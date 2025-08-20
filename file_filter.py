#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import argparse
import hashlib
import pandas as pd
import re
import difflib
import numpy as np
import requests
import json
from PIL import Image
import io
import base64
import time
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 可选：注册 HEIC/HEIF 解码支持（依赖 pillow-heif）
try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
except Exception:
    pass

# 尝试导入rawpy，如果失败则使用PIL处理RAW
try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False
    print("警告: rawpy未安装，RAW格式处理可能受限")

# 阿里云通义千问API配置（多模态 generation 接口）
QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
QWEN_API_KEY = "sk-2a293b2cc0cc4b679c6aea6ce82ae7fe"

# AI请求健壮性配置（可由命令行参数覆盖）
AI_REQUEST_TIMEOUT_S = 40
AI_REQUEST_MAX_RETRIES = 2
AI_REQUEST_QPS = 1.0  # 每秒请求数上限
_AI_LAST_CALL_TS = 0.0
_AI_RATE_LOCK = threading.Lock()

# 支持的图片格式（包含常见别名）
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.heic', '.heif'}
RAW_EXTENSIONS = {'.raw', '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.srw', '.raf', '.x3f'}

def is_raw_format(file_path):
    """检查是否为RAW格式文件"""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in RAW_EXTENSIONS

def convert_raw_to_jpg(raw_path, quality=85, max_size=(1920, 1080)):
    """将RAW格式图片转换为JPG"""
    try:
        if not RAWPY_AVAILABLE:
            print(f"警告: 无法处理RAW文件 {raw_path}，rawpy未安装")
            return None
        
        with rawpy.imread(raw_path) as raw:
            # 使用默认参数进行RAW解码
            rgb = raw.postprocess(use_camera_wb=True, half_size=False, 
                                no_auto_bright=True, output_bps=8)
            
            # 转换为PIL Image
            img = Image.fromarray(rgb)
            
            # 调整图片大小以控制文件大小
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 保存为临时JPG文件
            jpg_path = os.path.splitext(raw_path)[0] + '_temp.jpg'
            img.save(jpg_path, 'JPEG', quality=quality, optimize=True)
            return jpg_path
            
    except Exception as e:
        print(f"转换RAW文件失败 {raw_path}: {e}")
        return None

def compress_image_for_api(image_path, max_size=(1024, 768), quality=80):
    """压缩图片以适配API上传"""
    try:
        with Image.open(image_path) as img:
            # 如果是RGBA模式，转换为RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 调整图片大小
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 创建压缩后的临时文件
            compressed_path = os.path.splitext(image_path)[0] + '_compressed.jpg'
            img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
            return compressed_path
            
    except Exception as e:
        print(f"压缩图片失败 {image_path}: {e}")
        return None

def convert_to_jpg(image_path, quality=85, max_size=(1024, 768)):
    """将图片转换为JPG格式，支持RAW格式"""
    try:
        # 检查是否为RAW格式
        if is_raw_format(image_path):
            return convert_raw_to_jpg(image_path, quality, max_size)
        
        # 普通图片格式处理
        with Image.open(image_path) as img:
            # 如果是RGBA模式，转换为RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 调整图片大小
            # 统一限制最大边，避免过大图片导致API体积超限
            try:
                max_w, max_h = max_size
            except Exception:
                max_w, max_h = 1024, 768
            if img.size[0] > max_w or img.size[1] > max_h:
                img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            
            # 创建临时JPG文件
            jpg_path = os.path.splitext(image_path)[0] + '_temp.jpg'
            img.save(jpg_path, 'JPEG', quality=quality, optimize=True)
            return jpg_path
    except Exception as e:
        print(f"转换图片失败 {image_path}: {e}")
        return None

def analyze_image_with_qwen(image_path):
    """使用通义千问视觉模型分析图片内容（多模态 generation 接口）。"""
    try:
        # 转换图片为JPG格式（包含压缩）
        jpg_path = convert_to_jpg(image_path, quality=80, max_size=(1024, 768))
        if not jpg_path:
            return None

        # 读取图片并编码为base64（以 data URL 形式传入 image 字段）
        with open(jpg_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

        # 清理临时文件
        if os.path.exists(jpg_path):
            os.remove(jpg_path)

        # 准备API请求
        headers = {
            "Authorization": f"Bearer {QWEN_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen-vl-max-latest",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_data_url},
                            {"text": "请简要用中文描述图片内容，输出适合作为文件名的短语。"}
                        ]
                    }
                ]
            },
            "parameters": {
                "max_tokens": 150,
                "temperature": 0.2
            }
        }

        # 发送API请求（带速率限制与重试）
        backoff = 1.5
        attempt = 0
        while True:
            # 速率限制：全局串行节流，避免超QPS
            if AI_REQUEST_QPS > 0:
                interval = 1.0 / AI_REQUEST_QPS
                with _AI_RATE_LOCK:
                    now = time.time()
                    wait = max(0.0, interval - (now - _AI_LAST_CALL_TS))
                    if wait > 0:
                        time.sleep(wait)
                    # 更新最后调用时间
                    globals()['_AI_LAST_CALL_TS'] = time.time()

            try:
                response = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=AI_REQUEST_TIMEOUT_S)
                status = response.status_code
                if status >= 200 and status < 300:
                    break
                # 4xx: 对400直接放弃，429重试；5xx重试
                if status == 400:
                    # 记录并放弃
                    try:
                        print(f"AI请求400: {response.text}")
                    except Exception:
                        pass
                    return None
                if status in (408, 429) or 500 <= status < 600:
                    if attempt < AI_REQUEST_MAX_RETRIES:
                        sleep_s = backoff ** attempt
                        time.sleep(sleep_s)
                        attempt += 1
                        continue
                    else:
                        response.raise_for_status()
                # 其他状态码，直接抛出
                response.raise_for_status()
            except Exception as req_err:
                if attempt < AI_REQUEST_MAX_RETRIES:
                    sleep_s = backoff ** attempt
                    time.sleep(sleep_s)
                    attempt += 1
                    continue
                print(f"AI请求失败且重试耗尽: {req_err}")
                return None

        result = response.json()
        # 解析多模态 generation 输出，兼容 output.text 和 output.choices[0].message.content[*].text
        description = None
        if isinstance(result, dict):
            output_obj = result.get("output")
            if isinstance(output_obj, dict):
                text_value = output_obj.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    description = text_value.strip()
                if not description:
                    choices = output_obj.get("choices")
                    if isinstance(choices, list) and choices:
                        content_items = choices[0].get("message", {}).get("content", [])
                        if isinstance(content_items, list):
                            texts = [it.get("text") for it in content_items if isinstance(it, dict) and isinstance(it.get("text"), str)]
                            if texts:
                                description = " ".join(t.strip() for t in texts if t and t.strip())

        if not description:
            print(f"API响应格式异常: {result}")
            return None
        # 清理描述文本，移除特殊字符与尾部扩展名，适合作为文件名
        description = re.sub(r'[<>:"/\\|?*]', '', description)
        # 去除尾部常见扩展名，避免出现 .jpg.jpg
        description = re.sub(r'\.(jpg|jpeg|png|gif|bmp|tif|tiff|webp|heic|heif)\s*$', '', description, flags=re.IGNORECASE)
        # 统一空白为下划线
        description = re.sub(r'\s+', '_', description)
        description = re.sub(r'_+', '_', description).strip('_')
        return description

    except Exception as e:
        print(f"AI分析图片失败 {image_path}: {e}")
        return None

def _iter_source_files(source_folder):
    """遍历源目录，产生需要处理的文件名（过滤隐藏文件）。"""
    for root, _, files in os.walk(source_folder):
        for filename in files:
            if filename.startswith('.'):
                continue
            yield root, filename

def _compute_sha256(file_path, chunk_size=1024 * 1024):
    """计算文件的 SHA-256 校验值。"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def _copy_with_verify(source_file, target_file, max_retries=2):
    """复制文件到目标位置，并进行内容校验；失败将按次数重试。

    返回 True 表示复制并校验成功；否则 False。
    """
    try:
        source_hash = _compute_sha256(source_file)
    except Exception as e:  # noqa: BLE001
        print(f"计算源文件哈希失败: {source_file} -> {e}")
        return False

    attempt = 0
    while attempt <= max_retries:
        try:
            shutil.copy2(source_file, target_file)
            # 快速尺寸检查
            if os.path.getsize(source_file) != os.path.getsize(target_file):
                raise IOError("文件大小不一致")
            # 严格哈希校验
            target_hash = _compute_sha256(target_file)
            if target_hash == source_hash:
                return True
            raise IOError("哈希不一致")
        except Exception as e:  # noqa: BLE001
            if attempt < max_retries:
                print(f"复制校验失败 (第{attempt + 1}次): {e}，准备重试…")
                try:
                    if os.path.exists(target_file):
                        os.remove(target_file)
                except Exception:
                    pass
                attempt += 1
                continue
            else:
                print(f"复制校验最终失败: {e}")
                try:
                    if os.path.exists(target_file):
                        os.remove(target_file)
                except Exception:
                    pass
                return False

def process_files(source_folder, target_folder, reference_file, progress_callback=None, is_cancelled=None, use_ai_naming=False):
    """
    根据参考表格筛选文件，复制到目标文件夹并重命名
    
    参数:
        source_folder: 源文件夹路径，包含需要筛选的照片文件
        target_folder: 目标文件夹路径，用于存放筛选后的文件
        reference_file: 参考表格文件路径，包含标识符和对应的备注
        use_ai_naming: 是否使用AI视觉理解进行重命名
    """
    # 确保目标文件夹存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        print(f"已创建目标文件夹: {target_folder}")
    
    # 读取参考表格
    try:
        # 尝试读取Excel文件
        if reference_file.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(reference_file, header=0)
        # 尝试读取CSV文件
        elif reference_file.endswith('.csv'):
            df = pd.read_csv(reference_file, header=0)
        else:
            raise ValueError("参考文件必须是Excel(.xlsx/.xls)或CSV(.csv)格式")
        
        # 只读取第一列作为标识符
        if len(df.columns) < 1:
            raise ValueError("参考表格必须至少包含一列：标识符")
        
        # 获取标识符列表
        identifiers = []
        for _, row in df.iterrows():
            identifier = str(row[df.columns[0]]).strip()
            if identifier:
                identifiers.append(identifier.lower())

        print(f"成功加载参考表格，共有{len(identifiers)}个有效标识符")
    except Exception as e:
        print(f"读取参考表格时出错: {e}")
        return
    
    # 处理源文件夹中的文件
    matched_count = 0
    processed_count = 0
    all_files = list(_iter_source_files(source_folder))
    total_files = len(all_files)
    if progress_callback:
        try:
            progress_callback(processed_count, total_files, matched_count, None)
        except Exception:
            pass
    
    for root, filename in all_files:
        if is_cancelled and callable(is_cancelled) and is_cancelled():
            print("处理已被用户取消")
            break

        basename, ext = os.path.splitext(filename)
        source_file = os.path.join(root, filename)
        ai_temp_jpg_path = None
        
        # 检查是否为图片文件（包括RAW格式）
        is_image = ext.lower() in IMAGE_EXTENSIONS or is_raw_format(source_file)
        
        if use_ai_naming and is_image:
            # 使用AI视觉理解重命名
            print(f"正在使用AI分析图片: {filename}")
            # 对异常格式进行快速过滤：空文件、超大文件（> 50MB）直接跳过
            try:
                if os.path.getsize(source_file) <= 0 or os.path.getsize(source_file) > 50 * 1024 * 1024:
                    print(f"AI前置检查跳过(空或过大): {filename}")
                    ai_description = None
                else:
                    ai_description = analyze_image_with_qwen(source_file)
            except Exception:
                ai_description = analyze_image_with_qwen(source_file)
            if ai_description:
                new_filename = f"{ai_description}{ext}"
                print(f"AI分析结果: {filename} -> {new_filename}")
            else:
                print(f"AI分析失败，跳过: {filename}")
                processed_count += 1
                if progress_callback:
                    try:
                        progress_callback(processed_count, total_files, matched_count, filename)
                    except Exception:
                        pass
                continue
        else:
            # 使用原有的文件名匹配逻辑
            tokens = re.findall(r"\d+|[A-Za-z]+|[\u4e00-\u9fff]+", basename)
            tokens.append(basename)
            
            matched_identifier = None
            for token in tokens:
                key = token.lower()
                if key in identifiers:
                    matched_identifier = key
                    break
            
            if not matched_identifier:
                # 模糊匹配
                for token in tokens:
                    key = token.lower()
                    closest = difflib.get_close_matches(key, identifiers, n=1, cutoff=0.6)
                    if closest:
                        matched_identifier = closest[0]
                        print(f"模糊匹配: {filename} 的标识 {token} -> {matched_identifier}")
                        break
            
            if not matched_identifier:
                # 跳过不匹配的文件
                processed_count += 1
                if progress_callback:
                    try:
                        progress_callback(processed_count, total_files, matched_count, filename)
                    except Exception:
                        pass
                continue
            
            new_filename = f"{matched_identifier}{ext}"
        
        # 处理文件名冲突
        target_file = os.path.join(target_folder, new_filename)
        if os.path.exists(target_file):
            counter = 1
            while True:
                name_without_ext = os.path.splitext(new_filename)[0]
                candidate = f"{name_without_ext}_{counter}{os.path.splitext(new_filename)[1]}"
                candidate_path = os.path.join(target_folder, candidate)
                if not os.path.exists(candidate_path):
                    new_filename = candidate
                    target_file = candidate_path
                    break
                counter += 1

        # 复制文件并重命名（带校验与重试）
        success = _copy_with_verify(source_file, target_file)
        if success:
            print(f"已复制并重命名(校验通过): {filename} -> {new_filename}")
            matched_count += 1
        else:
            print(f"复制或校验失败，已跳过: {filename}")
        
        # 进度更新
        processed_count += 1
        if progress_callback:
            try:
                progress_callback(processed_count, total_files, matched_count, filename)
            except Exception:
                pass
    
    print(f"\n处理完成! 共找到并处理了{matched_count}个匹配的文件")
    if matched_count == 0:
        print("没有找到匹配的文件，请检查源文件夹中的文件名与参考表格中的标识符是否一致")

def main():
    parser = argparse.ArgumentParser(description='根据参考表格筛选文件，复制到目标文件夹并重命名')
    parser.add_argument('--source', '-s', required=True, help='源文件夹路径，包含需要筛选的照片文件')
    parser.add_argument('--target', '-t', required=True, help='目标文件夹路径，用于存放筛选后的文件')
    parser.add_argument('--reference', '-r', required=True, help='参考表格文件路径，包含标识符和对应的备注')
    parser.add_argument('--ai-naming', action='store_true', help='使用AI视觉理解进行重命名')
    
    args = parser.parse_args()
    
    # 验证路径
    if not os.path.exists(args.source):
        print(f"错误: 源文件夹不存在: {args.source}")
        return

    target_parent = os.path.dirname(args.target)
    if target_parent and not os.path.exists(target_parent):
        print(f"错误: 目标文件夹的父目录不存在: {target_parent}")
        return

    if not os.path.exists(args.reference):
        print(f"错误: 参考表格文件不存在: {args.reference}")
        return
    
    # 处理文件
    process_files(args.source, args.target, args.reference, use_ai_naming=args.ai_naming)

if __name__ == "__main__":
    main()

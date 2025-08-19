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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

def process_files(source_folder, target_folder, reference_file, progress_callback=None, is_cancelled=None):
    """
    根据参考表格筛选文件，复制到目标文件夹并重命名
    
    参数:
        source_folder: 源文件夹路径，包含需要筛选的照片文件
        target_folder: 目标文件夹路径，用于存放筛选后的文件
        reference_file: 参考表格文件路径，包含标识符和对应的备注
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
        
        # 确保表格有两列数据
        if len(df.columns) < 2:
            raise ValueError("参考表格必须至少包含两列：标识符和备注")

        # 获取标识符和备注的映射关系
        id_to_remark = {}
        for _, row in df.iterrows():
            identifier = str(row[df.columns[0]]).strip()
            if identifier:
                remark = str(row[df.columns[1]]).strip()
                id_to_remark[identifier.lower()] = remark

        reference_keys = list(id_to_remark.keys())
        vectorizer = TfidfVectorizer(analyzer='char').fit(reference_keys)
        reference_matrix = vectorizer.transform(reference_keys)

        print(f"成功加载参考表格，共有{len(id_to_remark)}个有效映射关系")
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

            tokens = re.findall(r"\d+|[A-Za-z]+|[\u4e00-\u9fff]+", basename)
            tokens.append(basename)

            remark = None

            for token in tokens:
                key = token.lower()
                if key in id_to_remark:
                    remark = id_to_remark[key]
                    break

            if not remark:
                for token in tokens:
                    key = token.lower()
                    closest = difflib.get_close_matches(key, id_to_remark.keys(), n=1, cutoff=0.6)
                    if closest:
                        matched_key = closest[0]
                        remark = id_to_remark[matched_key]
                        print(f"模糊匹配: {filename} 的标识 {token} -> {matched_key}")
                        break

            if not remark:
                tokens_lower = [t.lower() for t in tokens]
                token_matrix = vectorizer.transform(tokens_lower)
                similarities = cosine_similarity(token_matrix, reference_matrix)
                token_idx, ref_idx = np.unravel_index(similarities.argmax(), similarities.shape)
                best_score = similarities[token_idx, ref_idx]
                if best_score >= 0.5:
                    matched_key = reference_keys[ref_idx]
                    remark = id_to_remark[matched_key]
                    print(
                        f"AI匹配: {filename} 的标识 {tokens[token_idx]} -> {matched_key} (相似度 {best_score:.2f})"
                    )

            if remark:
                # 创建新的文件名，如有重名则自动追加编号
                new_filename = f"{remark}{ext}"
                target_file = os.path.join(target_folder, new_filename)
                if os.path.exists(target_file):
                    counter = 1
                    while True:
                        candidate = f"{remark}_{counter}{ext}"
                        candidate_path = os.path.join(target_folder, candidate)
                        if not os.path.exists(candidate_path):
                            new_filename = candidate
                            target_file = candidate_path
                            break
                        counter += 1

                # 源文件和目标文件的完整路径
                source_file = os.path.join(root, filename)

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
    process_files(args.source, args.target, args.reference)

if __name__ == "__main__":
    main()

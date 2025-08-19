#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import argparse
import pandas as pd
import re
import difflib

def process_files(source_folder, target_folder, reference_file):
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

        print(f"成功加载参考表格，共有{len(id_to_remark)}个有效映射关系")
    except Exception as e:
        print(f"读取参考表格时出错: {e}")
        return
    
    # 处理源文件夹中的文件
    matched_count = 0
    for root, _, files in os.walk(source_folder):
        for filename in files:
            # 跳过隐藏文件
            if filename.startswith('.'):
                continue

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

            if remark:
                # 创建新的文件名
                new_filename = f"{remark}{ext}"

                # 源文件和目标文件的完整路径
                source_file = os.path.join(root, filename)
                target_file = os.path.join(target_folder, new_filename)

                # 复制文件并重命名
                try:
                    shutil.copy2(source_file, target_file)
                    print(f"已复制并重命名: {filename} -> {new_filename}")
                    matched_count += 1
                except Exception as e:
                    print(f"复制文件时出错 {filename}: {e}")
    
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

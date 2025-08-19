#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import argparse
import pandas as pd
import re

def process_files(source_folder, target_folder, reference_file):
    """
    根据参考表格筛选文件，复制到目标文件夹并重命名
    
    参数:
        source_folder: 源文件夹路径，包含需要筛选的照片文件
        target_folder: 目标文件夹路径，用于存放筛选后的文件
        reference_file: 参考表格文件路径，包含四位数字和对应的备注
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
            raise ValueError("参考表格必须至少包含两列：四位数字和备注")
        
        # 获取四位数字和备注的映射关系
        number_to_remark = {}
        for _, row in df.iterrows():
            # 获取第一列的四位数字
            number = str(row[df.columns[0]]).strip()
            # 确保是四位数字
            if re.match(r'^\d{4}$', number):
                # 获取第二列的备注
                remark = str(row[df.columns[1]]).strip()
                number_to_remark[number] = remark
            else:
                print(f"警告: 跳过非四位数字的条目: {number}")
        
        print(f"成功加载参考表格，共有{len(number_to_remark)}个有效映射关系")
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
                
            # 获取文件的后四位数字
            match = re.search(r'(\d{4})\.[^.]+$', filename)
            if match:
                last_four_digits = match.group(1)
                
                # 检查是否在参考表格中
                if last_four_digits in number_to_remark:
                    # 获取对应的备注
                    remark = number_to_remark[last_four_digits]
                    
                    # 获取文件扩展名
                    _, ext = os.path.splitext(filename)
                    
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
        print("没有找到匹配的文件，请检查源文件夹中的文件名是否包含四位数字后缀，或者参考表格中的四位数字是否正确")

def main():
    parser = argparse.ArgumentParser(description='根据参考表格筛选文件，复制到目标文件夹并重命名')
    parser.add_argument('--source', '-s', required=True, help='源文件夹路径，包含需要筛选的照片文件')
    parser.add_argument('--target', '-t', required=True, help='目标文件夹路径，用于存放筛选后的文件')
    parser.add_argument('--reference', '-r', required=True, help='参考表格文件路径，包含四位数字和对应的备注')
    
    args = parser.parse_args()
    
    # 验证路径
    if not os.path.exists(args.source):
        print(f"错误: 源文件夹不存在: {args.source}")
        return
    
    if not os.path.exists(os.path.dirname(args.target)):
        print(f"错误: 目标文件夹的父目录不存在: {os.path.dirname(args.target)}")
        return
    
    if not os.path.exists(args.reference):
        print(f"错误: 参考表格文件不存在: {args.reference}")
        return
    
    # 处理文件
    process_files(args.source, args.target, args.reference)

if __name__ == "__main__":
    main()
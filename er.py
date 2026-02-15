#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
import re
from typing import List, Dict, Optional, Tuple
from utils_tools.libs import translate_lib


def is_invalid(s: str) -> bool:
    if s.isascii():
        return True

    # 检查Unicode私有区域字符和半角日语字符
    for char in s:
        code_point = ord(char)
        # 私有使用区: U+E000 - U+F8FF
        if 0xE000 <= code_point <= 0xF8FF:
            return True
        # 补充私有使用区-A: U+F0000 - U+FFFFF
        if 0xF0000 <= code_point <= 0xFFFFF:
            return True
        # 补充私有使用区-B: U+100000 - U+10FFFF
        if 0x100000 <= code_point <= 0x10FFFF:
            return True
        # 半角日语字符(标点+片假名): U+FF61 - U+FF9F
        if 0xFF61 <= code_point <= 0xFF9F:
            return True
        # 控制字符: C0 (0-31, 127) 和 C1 (128-159)
        if code_point < 32 or code_point == 127 or (128 <= code_point <= 159):
            return True
    return False


def map_name(i: int) -> str | None:
    if i == 0:
        return None
    if i == 1:
        return "真一"
    if i == 2:
        return "瑞穂"
    if i == 3:
        return "ユカリ"
    if i == 4:
        return "希"
    if i == 5:
        return "安芸"
    if i == 6:
        return "トキ子"
    if i == 7:
        return "朝霧"
    if i == 8:
        return "水鳥"
    if i == 9:
        return "櫻"
    if i == 10:
        return "嘉悦"  # 嘉悦行雄
    if i == 11:
        return "日向"  # 日向徹（ひなた とおる）
    if i == 12:
        return "女将"
    if i == 13:
        return "仲居さんA"
    if i == 14:
        return "仲居さんB"
    if i == 15:
        return "警官"
    if i == 16:
        return "黒服の男"
    if i == 17:
        return "担当車掌"
    if i == 18:
        return "アナウンス"
    if i == 19:
        return "司会者"
    if i == 20:
        return "希の友達"
    if i == 21:
        return "乗客"
    if i == 24:
        return "ナレーション"

    return f"未知角色{i}"


def extract_strings_from_file(file_path: str) -> List[Dict]:
    """
    扫描单文件，根据第一个匹配到的 marker 决定类型并提取字符串。
    返回的 results: 每项至少包含 'message' 和 'path'；若该对话有角色名则包含 'name'。
    """
    results: List[Dict] = []
    with open(file_path, 'r', encoding='utf-8') as f:
        opcodes = json.load(f)

    current_name_index = 0
    last_message = None

    for op in opcodes:
        if op["op"] == "10 FF 00 05":
            current_name_index, _ = translate_lib.de(op["value"][0])

        if op["op"] == "00":
            if is_invalid(op["value"][0]):
                raise ValueError(f"{op['value'][0]} 存在非法字符!")

            if last_message == None:
                last_message = op["value"][0]
            else:
                last_message += op["value"][0]

        if op["op"] == "15" and last_message != None:
            item = {"message": last_message}
            last_message = None

            name = map_name(current_name_index)
            if name:
                item["name"] = name
            results.append(item)

        if op["op"] == "08 0B 02 0F 08 0B FF 43 05 03 00 00 00 FF 05 00 00 00 00 FF 05 00 00 00 00 FF 05 00 00 00 00 FF 05 01 00 00 00 FF":
            assert last_message == None
            for v in op['value'][4:]:
                if is_invalid(v):
                    raise ValueError(f"{v} 存在非法字符!")
                results.append({"message": v, "is_select": True})

    assert last_message == None

    return results


def extract_strings(path: str, output_file: str):
    files = translate_lib.collect_files(path)
    results = []
    for file in files:
        results.extend(extract_strings_from_file(file))
    print(f"提取了 {len(results)} 项")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

# ========== 替换 ==========


def replace_in_file(
    file_path: str,
    text: List[Dict[str, str]],
    output_dir: str,
    trans_index: int,
    base_root: str
) -> int:
    with open(file_path, 'r', encoding='utf-8') as f:
        opcodes = json.load(f)

    in_sentence = False  # 是否已经处理过本句的第一个 00
    new_opcodes = []

    for op in opcodes:
        # ---------- 普通文本 ----------
        if op["op"] == "00":
            if not in_sentence:
                # 本句第一个 00，写入完整译文
                trans_item = text[trans_index]
                trans_index += 1
                op["value"][0] = trans_item["message"]
                in_sentence = True
            else:
                # 同一句后续 00，清空
                op["value"][0] = ""

        # ---------- 句子结束 ----------
        if op["op"] == "15":
            in_sentence = False

        # ---------- 选项 ----------
        if op["op"] == (
            "08 0B 02 0F 08 0B FF 43 05 03 00 00 00 FF "
            "05 00 00 00 00 FF 05 00 00 00 00 FF "
            "05 00 00 00 00 FF 05 01 00 00 00 FF"
        ):
            assert not in_sentence
            for i in range(len(op["value"][4:])):
                trans_item = text[trans_index]
                trans_index += 1
                op["value"][i + 4] = trans_item["message"]

        # ---------- 删除换行 ----------
        if op["op"] == "14":
            assert new_opcodes[-1]["op"] in ("08", "00")
            continue

        new_opcodes.append(op)

    # ---------- 保存 ----------
    rel = os.path.relpath(file_path, start=base_root)
    out_path = os.path.join(output_dir, rel)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(new_opcodes, f, ensure_ascii=False, indent=2)

    return trans_index


def replace_strings(path: str, text_file: str, output_dir: str):
    with open(text_file, 'r', encoding='utf-8') as f:
        text = json.load(f)
    files = translate_lib.collect_files(path)
    trans_index = 0
    for file in files:
        trans_index = replace_in_file(
            file, text, output_dir, trans_index, base_root=path)
        print(f"已处理: {file}")
    if trans_index != len(text):
        print(f"错误: 有 {len(text)} 项译文，但只消耗了 {trans_index}。")
        exit(1)

# ---------------- main ----------------


def main():
    parser = argparse.ArgumentParser(description='文件提取和替换工具')
    subparsers = parser.add_subparsers(
        dest='command', help='功能选择', required=True)

    ep = subparsers.add_parser('extract', help='解包文件提取文本')
    ep.add_argument('--path', required=True, help='文件夹路径')
    ep.add_argument('--output', default='raw.json', help='输出JSON文件路径')

    rp = subparsers.add_parser('replace', help='替换解包文件中的文本')
    rp.add_argument('--path', required=True, help='文件夹路径')
    rp.add_argument('--text', default='translated.json', help='译文JSON文件路径')
    rp.add_argument('--output-dir', default='translated',
                    help='输出目录(默认: translated)')

    args = parser.parse_args()
    if args.command == 'extract':
        extract_strings(args.path, args.output)
        print(f"提取完成! 结果保存到 {args.output}")
    elif args.command == 'replace':
        replace_strings(args.path, args.text, args.output_dir)
        print(f"替换完成! 结果保存到 {args.output_dir} 目录")


if __name__ == '__main__':
    main()

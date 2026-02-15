import os
import json
from typing import Dict, List, Tuple
from utils_tools.libs.ops_lib import assemble_one_op, byte_slice, flat, h, parse_data, string, u32, u16, u8, Handler
from utils_tools.libs.translate_lib import collect_files, de, read_bytes_s, se


OPCODES_MAP = flat({
    h("00"): [string],

    h("01"): [],
    h("02"): [u8],
    h("04"): [],
    h("07"): [],
    h("10"): [],
    h("11"): [],
    h("13"): [],
    h("14"): [],
    h("15"): [],
    h("17"): [],
    h("19"): [],
    h("1D"): [],
    h("1F"): [],
    h("20"): [],
    h("21"): [],
    h("29"): [],
    h("2B"): [],
    h("31"): [],
    h("34"): [],
    h("40"): [],
    h("45"): [],
    h("5C"): [],
    h("80"): [],
    h("98 06"): [],
    h("08"): [u8],
    h("FF"): [],

    h("18"): [u32],  # 非偏移
    h("05"): [u32],  # 非偏移
    h("00 05"): [u32],  # 非偏移
    h("93"): [u32],  # 非偏移
    h("10 FF 00 05"): [u32],  # 非偏移
    h("11 FF 00 05"): [u32],  # 非偏移
    h("12 FF 00 05"): [u32],  # 非偏移
    h("19 01"): [u32],  # 非偏移
    h("0B"): [u32],  # 非偏移

    h("10 FF 08"): [],
    h("10 FF"): [u32],  # 非偏移
    h("04 00"): [],
    h("20 00 31"): [],
    h("11 FF 02 05 0A 00"): [],

    h("06"): [u32],  # **是偏移，需要修
    h("00 FF 03 00"): [u32.repeat(3)],  # **三个u32都是偏移，需要修
    h("11 FF"): [u32],  # **是偏移，需要修
    h("12 FF"): [u32],  # **是偏移，需要修
    h("15 FF"): [u32.repeat(2)],  # **需要修第一个偏移
    # 选项，两个u32都是偏移，需要修
    h("08 0B 02 0F 08 0B FF 43 05 03 00 00 00 FF 05 00 00 00 00 FF 05 00 00 00 00 FF 05 00 00 00 00 FF 05 01 00 00 00 FF"): [u32, byte_slice.args(1), u8, u32, string.repeat_var(-2)],

    h("09 00"): [],
    h("12 00"): [],
    h("00 00"): [],
    h("0E 00"): [],
    h("0F"): [u8],

    h("05 28 06 28 08 00"): [],

    h("12 FF 00 13 FF 01"): [],

    h("00 FF"): [],



    h("1A"): [u8, u16],
    h("00 02"): [],



    h("00 02 06 00 FF 00"): [],
    h("00 02 05 00 FF 00"): [],
    h("00 02 07 00 FF 00"): [],
    h("5C 00 11 FF 00"): [],
    h("1D 00 4C 07 22 00"): [],
    h("04 01 00"): [],
    h("12 00 01 00"): [],
    h("01 01 00 96 00"): [],
    h("01 01 00"): [u16, u8],
})


def disasm_mode(input_path: str, output_path: str):
    """反汇编模式：将二进制文件转换为JSON"""
    files: List[str] = collect_files(input_path)

    for file in files:
        if file.endswith("json"):
            continue

        with open(file, "rb") as f:
            data = f.read()

        # 使用通用解析引擎和opcodes map
        opcodes, _ = parse_data({
            "file_name": file,
            "offset": 0,
        }, data, OPCODES_MAP)

        # 保存为JSON
        rel_path = os.path.relpath(file, start=input_path)
        out_file = os.path.join(output_path, rel_path + ".json")
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(opcodes, f, ensure_ascii=False, indent=2)


def asm_mode(input_path: str, output_path: str):
    """汇编模式：将JSON转换回二进制文件"""
    files = collect_files(input_path, "json")

    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            ops = json.load(f)

        # ========= 第一步：assemble opcode，计算新 offset =========
        old2new = {}          # old_offset -> new_offset
        opcode_bins = []      # 每条 opcode 的二进制
        cursor = 0

        for op in ops:
            old_offset = op["offset"]
            b = assemble_one_op(op)

            old2new[old_offset] = cursor
            opcode_bins.append(b)
            cursor += len(b)

        # ========= 第二步：修复 opcodes 的跳转 =========
        for i, op in enumerate(ops):
            if op['op'] in ("06", "00 FF 03 00", "11 FF", "12 FF"):
                for i in range(len(op['value'])):
                    old_offset, type_hint = de(op['value'][i])

                    if old_offset not in old2new:
                        raise ValueError(
                            f"{file}, {op} 指向不存在的 offset: {old_offset}")

                    op['value'][i] = se(old2new[old_offset], type_hint)
                continue

            if op['op'] == "08 0B 02 0F 08 0B FF 43 05 03 00 00 00 FF 05 00 00 00 00 FF 05 00 00 00 00 FF 05 00 00 00 00 FF 05 01 00 00 00 FF":
                for i in [0, 3]:
                    old_offset, type_hint = de(op['value'][i])

                    if old_offset not in old2new:
                        raise ValueError(
                            f"{file}, {op} 指向不存在的 offset: {old_offset}")

                    op['value'][i] = se(old2new[old_offset], type_hint)

                continue
            if op['op'] == "15 FF":
                for i in [0]:
                    old_offset, type_hint = de(op['value'][i])

                    if old_offset not in old2new:
                        raise ValueError(
                            f"{file}, {op} 指向不存在的 offset: {old_offset}")

                    op['value'][i] = se(old2new[old_offset], type_hint)

                continue

        new_blob = b"".join([assemble_one_op(op) for op in ops])

        # 保存二进制文件
        rel_path = os.path.relpath(file, start=input_path)
        rel_path = rel_path[:-5]  # 移除.json扩展名
        out_file = os.path.join(output_path, rel_path)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

        with open(out_file, 'wb') as f:
            f.write(new_blob)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='游戏脚本反汇编/汇编工具')
    parser.add_argument(
        'mode', choices=['disasm', 'asm'], help='模式: disasm(反汇编) 或 asm(汇编)')
    parser.add_argument('input', help='输入文件夹路径')
    parser.add_argument('output', help='输出文件夹路径')

    args = parser.parse_args()

    if args.mode == 'disasm':
        disasm_mode(args.input, args.output)
        print(f"反汇编完成: {args.input} -> {args.output}")
    elif args.mode == 'asm':
        asm_mode(args.input, args.output)
        print(f"汇编完成: {args.input} -> {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import struct
from pathlib import Path


# ----------------------------
# LZ Decompress / Compress
# ----------------------------

def lz_decompress(data: bytes) -> bytes | None:
    """
    完整等价于 C# 的 LzDecompress
    """
    pos = 0
    unpacked_size, = struct.unpack_from("<I", data, pos)
    pos += 4

    if unpacked_size == 0:
        return None

    out = bytearray(unpacked_size)
    dst = 0

    while dst < unpacked_size:
        if pos >= len(data):
            return None

        ctl = data[pos]
        pos += 1

        if ctl & 0x80:
            lo = data[pos]
            pos += 1

            offset = ((ctl << 3 | lo >> 5) & 0x3FF) + 1
            count = (lo & 0x1F) + 1

            for i in range(count):
                out[dst] = out[dst - offset]
                dst += 1
        else:
            count = ctl + 1
            out[dst:dst + count] = data[pos:pos + count]
            pos += count
            dst += count

    return bytes(out)


def lz_compress(data: bytes) -> bytes:
    """
    与上面的解压互逆，只保证能被正确解压，不追求压缩率
    策略：全 literal
    """
    out = bytearray()
    out += struct.pack("<I", len(data))

    pos = 0
    while pos < len(data):
        chunk = min(0x7F + 1, len(data) - pos)
        out.append(chunk - 1)   # ctl
        out += data[pos:pos + chunk]
        pos += chunk

    return bytes(out)


# ----------------------------
# Core Logic
# ----------------------------

def unpack(input_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    data = input_path.read_bytes()

    count_raw, = struct.unpack_from("<I", data, 0)
    count = count_raw + 1

    index_offset = 4

    offsets = []
    for i in range(count):
        off, = struct.unpack_from("<I", data, index_offset)
        offsets.append(off)
        index_offset += 4

    offsets.append(len(data))

    assert offsets[0] == count * 4 + 4

    meta = []

    for i in range(count):
        print(f"正在提取 {i} 个 (总共{count})")
        start = offsets[i]
        end = offsets[i + 1]
        chunk = data[start:end]

        name = f"{i:05d}"
        out_file = out_dir / name

        decompressed = False
        try:
            decoded = lz_decompress(chunk)
            if decoded:
                out_file.write_bytes(decoded)
                decompressed = True
            else:
                out_file.write_bytes(chunk)
        except Exception:
            out_file.write_bytes(chunk)

        meta.append({
            "name": name,
            "lz": decompressed,
            "size": end - start
        })

    with open(out_dir / "__META__.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def pack(input_dir: Path, out_path: Path):
    meta_path = input_dir / "__META__.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    blobs = []
    offsets = []
    cur = 4 + len(meta) * 4

    for item in meta:
        data = (input_dir / item["name"]).read_bytes()
        if item["lz"]:
            data = lz_compress(data)
        blobs.append(data)

    for b in blobs[:-1]:
        offsets.append(cur)
        cur += len(b)
    offsets.append(cur)

    with open(out_path, "wb") as f:
        f.write(struct.pack("<I", len(meta) - 1))
        for off in offsets:
            f.write(struct.pack("<I", off))
        for b in blobs:
            f.write(b)


# ----------------------------
# CLI
# ----------------------------

def main():
    ap = argparse.ArgumentParser(description="SERAPH SCN packer")
    sub = ap.add_subparsers(dest='cmd', required=True)

    ap_unpack = sub.add_parser('unpack', help='解包')
    ap_unpack.add_argument('-i', '--input', required=True)
    ap_unpack.add_argument('-o', '--out', required=True)

    ap_pack = sub.add_parser('pack', help='打包')
    ap_pack.add_argument('-i', '--input', required=True)
    ap_pack.add_argument('-o', '--out', required=True)

    args = ap.parse_args()

    if args.cmd == 'unpack':
        unpack(Path(args.input), Path(args.out))
    else:
        pack(Path(args.input), Path(args.out))


if __name__ == '__main__':
    main()

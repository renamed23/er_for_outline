#!/usr/bin/env python3

import os
from pathlib import Path

from utils_tools.libs import translate_lib

config = {
    "FONT_FACE": "SimHei",  # (ＭＳ ゴシック, SimHei, SimSun)
    "CHAR_SET": 134,  # CP932=128, GBK=134
    "FONT_FILTER": [
        "ＭＳ ゴシック",
        "俵俽 僑僔僢僋",
        "MS Gothic",
        "",
        "俵俽僑僔僢僋",
        "ＭＳゴシック",
    ],
    # "FONT_FILTER": ["Microsoft YaHei", "Microsoft YaHei UI"],
    # "CHAR_FILTER": [
    #     0x40
    # ],
    "ENUM_FONT_PROC_CHAR_SET": 128,
    # "ENUM_FONT_PROC_PITCH": 1,
    # "ENUM_FONT_PROC_OUT_PRECISION": 3,
    "WINDOW_TITLE": "Outline",
    "ARG_NAME": {
        "value": "OUTLINE",
        "type": "&str",
    },
    # "HIJACKED_DLL_PATH": "some_path/your_dll.dll",
    # "REDIRECTION_SRC_PATH": "B.FL4",
    # "REDIRECTION_TARGET_PATH": "FLOWERS_CHS.FL4",
    # "RESOURCE_PACK_NAME": "MOZU_chs",
}

hook_lists = {
    "enable": [],
    "disable": [
        "PropertySheetA",
    ],
}


# patch,custom_font,debug_output,debug_text_mapping
# default_impl,enum_font_families
# export_default_dll_main,read_file_patch_impl
# debug_file_impl,emulate_locale,override_window_title
# dll_hijacking,export_patch_process_fn,text_patch,text_extracting
# x64dbg_1337_patch,apply_1337_patch_on_attach,create_file_redirect
# text_out_arg_c_is_bytes,iat_hook,resource_pack,resource_pack_embedding
features = [
    "seraph",
    "text_hook",
    "text_out_arg_c_is_bytes",
    "override_window_title",
    "enum_font_families",
    "text_patch",
    "iat_hook"
]


PACKER = "python packer.py"
ASMER = "python ops.py"

ER = [
    (
        "python er.py extract --path raw --output raw.json",
        "python er.py replace --path raw --text generated/translated.json",
    )
]


def extract():
    print("执行提取...")
    # 需要将索引脚本和其他不支持的脚本放到asmed_pass
    # translate_lib.system(
    #     f"{PACKER} unpack -i ScnPac.Dat -o asmed")
    translate_lib.system(
        f"{ASMER} disasm asmed raw")
    translate_lib.extract_and_concat(ER)
    translate_lib.json_process('e', 'raw.json')


def replace():
    print("执行替换...")
    Path("generated/dist").mkdir(parents=True, exist_ok=True)

    # 你的 replace 逻辑
    translate_lib.generate_json(config, "config.json")
    translate_lib.generate_json(hook_lists, "hook_lists.json")
    translate_lib.copy_path(
        "translated.json", "generated/translated.json", overwrite=True
    )
    translate_lib.copy_path("raw.json", "generated/raw.json", overwrite=True)
    translate_lib.json_check()
    translate_lib.json_process("r", "generated/translated.json")
    translate_lib.ascii_to_fullwidth()
    translate_lib.replace("cp932", False)  # cp932,shift_jis,gbk

    translate_lib.split_and_replace(ER)

    translate_lib.copy_path(
        "translated", "generated/translated", overwrite=True)

    translate_lib.system(f"{ASMER} asm generated/translated generated/asmed")

    translate_lib.merge_directories(
        "asmed_pass", "generated/asmed", overwrite=True)

    translate_lib.system(
        f"{PACKER} pack -i generated/asmed -o generated/dist/Scn_chs.Dat")

    translate_lib.copy_path(
        "assets/raw_text", "generated/raw_text", overwrite=True)
    translate_lib.copy_path(
        "assets/translated_text", "generated/translated_text", overwrite=True)

    translate_lib.merge_directories(
        "assets/dist_pass", "generated/dist", overwrite=True
    )

    translate_lib.TextHookBuilder(os.environ["TEXT_HOOK_PROJECT_PATH"]).build(
        features, panic="immediate-abort"
    )


def main():
    translate_lib.create_cli(extract, replace)()


if __name__ == "__main__":
    main()

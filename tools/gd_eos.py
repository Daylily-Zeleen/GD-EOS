#!user/bin/python
# -*- coding: utf-8 -*-
import os
import sys

from SCons.Script import BoolVariable, Environment

try:
    import binding_generator.main as binding_generator
except ImportError:
    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    for key in list(sys.modules.keys()):
        if key == "binding_generator" or key.startswith("binding_generator."):
            del sys.modules[key]
    sys.path.insert(0, _tools_dir)
    import binding_generator.main as binding_generator

_generated_doc_data_file: str = "gd_eos/gen/doc_data/doc_data.cpp"


def generate(env: Environment):
    env.AddMethod(_generate_bindings, "GD_EOS_GENERATE_BINDINGS")
    env.AddMethod(_preprocess, "GD_EOS_PREPROCESS")
    env.AddMethod(_postprocess, "GD_EOS_POSTPROCESS")
    env.AddMethod(_add_clean_files, "GD_EOS_ADD_CLEAN_FILES")
    env.AddMethod(_generate_doc_data, "GD_EOS_GENERATE_DOC_DATA")
    env.AddMethod(_get_sdk_version, "GD_EOS_GET_SDK_VERSION")


def exists(_env):
    return True


def options(opts, _env):
    opts.Add(
        "min_field_count_to_expand_input_structs",
        "The min field count to expand input EOS Options structs (except 'ApiVersion' field).",
        "3",
    )
    opts.Add(
        "min_field_count_to_expand_callback_structs",
        "The min field count to expand EOS CallbackInfo structs.",
        "1",
    )
    opts.Add(
        BoolVariable(
            key="assume_only_one_local_user",
            help='If true, the code generator will hide all "LocalUserId" of EOS API\'s filed/argument and automatically fill them internally.',
            default=False,
        )
    )


def get_sdk_version() -> tuple[int, int, int, int]:
    # 从 eos_version.h 获取 SDK 版本（major, minor, patch, hotfix）
    import re

    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    eos_version_file = os.path.join(_tools_dir, "..", "thirdparty", "eos-sdk", "SDK", "Include", "eos_version.h")

    version_pattern = re.compile(r"#define\s+EOS_(MAJOR|MINOR|PATCH|HOTFIX)_VERSION\s+(\d+)")

    version: dict[str, int] = {}
    with open(eos_version_file, "r", encoding="utf-8") as f:
        for line in f:
            match = version_pattern.match(line.strip())
            if match:
                version[match.group(1)] = int(match.group(2))

    return (
        version.get("MAJOR", 0),
        version.get("MINOR", 0),
        version.get("PATCH", 0),
        version.get("HOTFIX", 0),
    )


def _get_sdk_version(env: Environment) -> tuple[int, int, int, int]:
    return get_sdk_version()


def _get_generated_files() -> tuple[list[str], list[str]]:
    files = []

    def is_generate_file(fp):
        return fp.endswith(".cpp") or fp.endswith(".c") or fp.endswith(".h") or fp.endswith(".hpp") or fp.endswith(".inl")

    from binding_generator.config import gen_include_dir, gen_src_dir

    for dir in [gen_include_dir, gen_src_dir]:
        for f in os.listdir(dir):
            fp = os.path.join(dir, f)
            if os.path.isfile(fp):
                if is_generate_file(fp):
                    files.append(fp)
            else:
                files += filter(is_generate_file, map(lambda x: os.path.join(fp, x), os.listdir(fp)))

    sources = list(filter(lambda fp: fp.endswith(".cpp") or fp.endswith(".c"), files))
    includes = list(filter(lambda fp: not (fp.endswith(".cpp") or fp.endswith(".c")), files))

    return includes, sources


def _generate_bindings(env: Environment) -> tuple[list[str], list[str]]:
    if not env.GetOption("clean"):
        from binding_generator.config import generate_config

        generate_config.min_field_count_to_expand_input_structs = int(env["min_field_count_to_expand_input_structs"])
        generate_config.min_field_count_to_expand_callback_structs = int(env["min_field_count_to_expand_callback_structs"])
        generate_config.assume_only_one_local_user = env["assume_only_one_local_user"]
        binding_generator.generate_bindings()
    return _get_generated_files()


def _preprocess(env: Environment) -> None:
    # 清理时不预处理
    if not env.GetOption("clean"):
        binding_generator.preprocess()


def _postprocess(env: Environment) -> None:
    # 清理时后处理(尝试还原文件,如已预处理但编译被打断未正确进行后处理)
    binding_generator.postprocess()


def _add_clean_files(env: Environment, target: str) -> None:
    includes, sources = _get_generated_files()
    files = includes + sources

    doc_data_file = _generated_doc_data_file
    if os.path.exists(doc_data_file):
        files.append(doc_data_file)

    env.Clean(target, files)


def _generate_doc_data(env: Environment) -> list[str]:
    # doc (godot-cpp 4.3 以上)
    if env["target"] in ["editor", "template_debug"]:
        try:
            if not env.GetOption("clean"):
                doc_data = env.GodotCPPDocData(_generated_doc_data_file, source=env.Glob("doc_classes/*.xml"))
                return doc_data
            else:
                return [_generated_doc_data_file]
        except AttributeError:
            print("Not including class reference as we're targeting a pre-4.3 baseline.")
    return []

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

_editor_gen_dir: str = os.path.join("gd_eos_editor", "gen")
_editor_gen_include_dir: str = os.path.join(_editor_gen_dir, "include")
_editor_gen_src_dir: str = os.path.join(_editor_gen_dir, "src")
_editor_doc_data_file: str = os.path.join(_editor_gen_dir, "doc_data", "doc_data.cpp")


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
    opts.Add(
        BoolVariable(
            key="generate_eos_bindings",
            help="If true, generate EOS bindings.",
            default=True,
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


def _get_generated_files(gen_include_dir: str, gen_src_dir: str) -> tuple[list[str], list[str]]:
    files = []

    def is_generated_file(fp: str) -> bool:
        return fp.endswith((".cpp", ".c", ".h", ".hpp", ".inl"))

    for generated_dir in [gen_include_dir, gen_src_dir]:
        # A target may be evaluated before its own generated files exist.
        if not os.path.isdir(generated_dir):
            continue

        for root, _, filenames in os.walk(generated_dir):
            files.extend(os.path.join(root, filename) for filename in filenames if is_generated_file(os.path.join(root, filename)))

    sources = [fp for fp in files if fp.endswith((".cpp", ".c"))]
    includes = [fp for fp in files if not fp.endswith((".cpp", ".c"))]

    return includes, sources


def _get_runtime_generated_files() -> tuple[list[str], list[str]]:
    from binding_generator.config import gen_include_dir, gen_src_dir

    return _get_generated_files(gen_include_dir, gen_src_dir)


def _get_editor_generated_files() -> list[str]:
    includes, sources = _get_generated_files(_editor_gen_include_dir, _editor_gen_src_dir)
    files = includes + sources

    if os.path.isfile(_editor_doc_data_file):
        files.append(_editor_doc_data_file)

    return files


def _generate_bindings(env: Environment) -> tuple[list[str], list[str]]:
    if not env.GetOption("clean"):
        from binding_generator.config import generate_config

        generate_config.min_field_count_to_expand_input_structs = int(env["min_field_count_to_expand_input_structs"])
        generate_config.min_field_count_to_expand_callback_structs = int(env["min_field_count_to_expand_callback_structs"])
        generate_config.assume_only_one_local_user = env["assume_only_one_local_user"]
        if env["generate_eos_bindings"]:
            binding_generator.generate_bindings()
    return _get_runtime_generated_files()


def _preprocess(env: Environment) -> None:
    # 清理时不预处理
    if not env.GetOption("clean"):
        binding_generator.preprocess()


def _postprocess(env: Environment) -> None:
    # 清理时后处理(尝试还原文件,如已预处理但编译被打断未正确进行后处理)
    binding_generator.postprocess()


def _add_clean_files(env: Environment, target: str, file_group: str) -> None:
    if file_group == "runtime":
        includes, sources = _get_runtime_generated_files()
        files = includes + sources
    elif file_group == "editor":
        files = _get_editor_generated_files()
    else:
        raise ValueError(f"Unknown generated file group: {file_group}")

    env.Clean(target, files)


def _generate_doc_data(env: Environment) -> list[str]:
    # Editor documentation is generated for every supported godot-cpp target.
    try:
        if not env.GetOption("clean"):
            doc_data = env.GodotCPPDocData(_editor_doc_data_file, source=env.Glob("doc_classes/*.xml"))
            return doc_data
        else:
            return [_editor_doc_data_file]
    except AttributeError:
        print("Not including class reference as we're targeting a pre-4.3 baseline.")
        return []

#!user/bin/python
# -*- coding: utf-8 -*-
import os
import tools.binding_generator
from SCons.Script import BoolVariable
from SCons.Script import Environment

_generated_doc_data_file :str = "gd_eos/gen/doc_data/doc_data.cpp"

def generate(env: Environment):
    env.AddMethod(_generate_bindings, "GD_EOS_GENERATE_BINDINGS")
    env.AddMethod(_preprocess, "GD_EOS_PREPROCESS")
    env.AddMethod(_postprocess, "GD_EOS_POSTPROCESS")
    env.AddMethod(_add_clean_files, "GD_EOS_ADD_CLEAN_FILES")
    env.AddMethod(_generate_doc_data, "GD_EOS_GENERATE_DOC_DATA")


def exists(env):
    return True


def options(opts, env):
    opts.Add("min_field_count_to_expand_input_structs", "The min field count to expand input EOS Options structs (except 'ApiVersion' field).", "3")
    opts.Add("min_field_count_to_expand_callback_structs", "The min field count to expand EOS CallbackInfo structs.", "1")
    opts.Add(
        BoolVariable(
            key="assume_only_one_local_user",
            help='If true, the code generator will hide all "LocalUserId" of EOS API\'s filed/argument and automatically fill them internally.',
            default=False,
        )
    )


def _get_generated_files() -> tuple[list[str], list[str]]:
    files = []

    is_generate_file = lambda fp: fp.endswith(".cpp") or fp.endswith(".c") or fp.endswith(".h") or fp.endswith(".hpp") or fp.endswith(".inl")

    gen_dir = os.path.join("gd_eos/", "gen")
    for folder in ["include", "src"]:
        dir = os.path.join(gen_dir, folder)
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
    # 不在清理时执行生成
    if not env.GetOption('clean'):
        tools.binding_generator.generate_bindings(int(env["min_field_count_to_expand_input_structs"]), int(env["min_field_count_to_expand_callback_structs"]), env["assume_only_one_local_user"])
    return _get_generated_files()


def _preprocess(env: Environment) -> None:
    # 清理时不预处理
    if not env.GetOption('clean'):
        tools.binding_generator.preprocess()


def _postprocess(env: Environment) -> None:
    # 清理时后处理(尝试还原文件,如已预处理但编译被打断未正确进行后处理)
    tools.binding_generator.postprocess()


def _add_clean_files(env: Environment, target):
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
            if not env.GetOption('clean'):
                doc_data = env.GodotCPPDocData(_generated_doc_data_file, source=env.Glob("doc_classes/*.xml"))
                return doc_data
            else:
                return [_generated_doc_data_file]
        except AttributeError:
            print("Not including class reference as we're targeting a pre-4.3 baseline.")
    return []
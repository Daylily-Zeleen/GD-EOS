#!user/bin/python
# -*- coding: utf-8 -*-
import os, sys
import traceback

from SCons.Variables import BoolVariable

# TODO: 解析废弃成员避免硬编码
# TODO: 为有Callable参数的方法生成强类型的回调版本供cpp使用

# TODO: 对文档提及的成员进行 GDS接口化
# TODO: @param @return @details 描述对象的处理 （低优先级，能用就行！

sdk_include_dir = "thirdparty/eos-sdk/SDK/Include"

gen_dir = "gd_eos/gen/"
gen_include_dir = os.path.join(gen_dir, "include")
gen_src_dir = os.path.join(gen_dir, "src")

# 解析结果
struct2additional_method_requirements: dict[str, dict[str, bool]] = {}  # dict[str, dict[str, bool]]
expanded_as_args_structs: list[str] = []  # 需要被展开为参数形式的结构体

interfaces: dict[str, dict] = {
    "Platform": {
        "EOS_Platform_Create": {
            "return": "EOS_HPlatform",
            "args": [{"type": "const EOS_Platform_Options*", "name": "Options"}],
        }
    }
}
structs: dict[str, dict] = {}
handles: dict[str, dict] = {
    "EOS": {
        "doc": "",
        "methods": {},
        "callbacks": {"EOS_LogMessageFunc": {"return": "", "args": [{"type": "const EOS_LogMessage*", "name": "Message"}], "doc": []}},
        "enums": {},
        "constants": {},
    },
    "EOS_HAntiCheatCommon": {
        "doc": "",
        "methods": {},
        "callbacks": {},
        "enums": {},
        "constants": {},
    },
}


api_latest_macros: list[str] = []
release_methods: dict[str, dict] = {}

unhandled_methods: dict[str, dict] = {}
unhandled_callbacks: dict[str, dict] = {}
unhandled_enums: dict[str, list[str]] = {}
unhandled_constants: dict[str, list[str]] = {}
unhandled_infos: dict[str, dict] = {}

generate_infos: dict = {}

# generate options
# 是否将Options结构展开为输入参数的，除了 ApiVersion 以外的最大字段数量,减少需要注册的类，以减少编译后大小
min_field_count_to_expand_input_structs: int = 3
min_field_count_to_expand_callback_structs: int = 1
# 是否假定只有一个本地用户，将隐藏所有的 LocalUserId 字段/参数，并在需要时在内部进行填充。
# 如果为非登录状态，则相关调用抛出错误并调用失败。
assume_only_one_local_user: bool = False

eos_data_class_h_file = "core/eos_data_class.h"

# 以下成员按替换顺序排序
# src -> {class: str, name: str}
doc_keyword_map_method: dict[str, dict[str, str]] = {}
doc_keyword_map_enum_member: dict[str, dict[str, str]] = {}
doc_keyword_map_enum: dict[str, dict[str, str]] = {}
doc_keyword_map_constant: dict[str, dict] = {}  # src -> {class: str, name: str, as_method: str}
doc_keyword_map_callback: dict[str, dict[str, str]] = {}
doc_keyword_map_struct: dict[str, str] = {}  # src -> name


def main(argv):
    # 处理生成选项
    for arg in argv:
        if arg in ["-h", "--help"]:
            print_help()
            print("You can override these options like this: min_field_count_to_expand_input_structs=5")
            exit()
        splits: list[str] = arg.split("=", 1)
        if (
            len(splits) != 2
            or not splits[1].isdecimal()
            or int(splits[1]) < 0
            or not splits[0] in ["min_field_count_to_expand_input_structs", "min_field_count_to_expand_callback_structs", "assume_only_one_local_user"]
        ):
            print("Unsupported option:", arg)
            print('Use "-h" or "--help" to get help.')
            exit()
        if splits[0] == "min_field_count_to_expand_input_structs":
            field_count_to_expand_input_structs = int(splits[1])
        elif splits[0] == "min_field_count_to_expand_callback_structs":
            field_count_to_expand_callback_structs = int(splits[1])
        elif splits[0] == "assume_only_one_local_user":
            only_one_local_user = to_snake_case(splits[1]) in ["t", "true"]

    generate_bindings(field_count_to_expand_input_structs, field_count_to_expand_callback_structs, only_one_local_user)


def print_help():
    print('min_field_count_to_expand_input_structs: The min field count to expand input Options structs (except "ApiVersion" field).')
    print("\tdefault:3")
    print("")
    print("min_field_count_to_expand_callback_structs: The min field count to expand CallbackInfo structs.")
    print("\tdefault:1")
    print("")
    print('assume_only_one_local_user: If true, the code generator will hide all "LocalUserId" filed/argument and automatically fill them internally.')
    print("\tdefault:false")
    print("")


def generate_bindings(
    p_min_field_count_to_expand_input_structs: int = 3, p_min_field_count_to_expand_callback_structs: int = 1, p_assume_only_one_local_user: bool = False
) -> None:
    global min_field_count_to_expand_input_structs
    global min_field_count_to_expand_callback_structs
    global assume_only_one_local_user

    min_field_count_to_expand_input_structs = p_min_field_count_to_expand_input_structs
    min_field_count_to_expand_callback_structs = p_min_field_count_to_expand_callback_structs
    assume_only_one_local_user = p_assume_only_one_local_user

    # make dir
    for base_dir in [gen_include_dir, gen_src_dir]:
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        if not os.path.exists(os.path.join(base_dir, "enums")):
            os.makedirs(os.path.join(base_dir, "enums"))
        if not os.path.exists(os.path.join(base_dir, "structs")):
            os.makedirs(os.path.join(base_dir, "structs"))
        if not os.path.exists(os.path.join(base_dir, "packed_results")):
            os.makedirs(os.path.join(base_dir, "packed_results"))
        if not os.path.exists(os.path.join(base_dir, "handles")):
            os.makedirs(os.path.join(base_dir, "handles"))
        if not os.path.exists(os.path.join(base_dir, "interfaces")):
            os.makedirs(os.path.join(base_dir, "interfaces"))
    # 解析文件
    print("Parsing...")
    parse_all_file()
    print("Parse finished")
    # 预处理文档
    _preprocess_docs()
    print("preprocess documents finished.")
    # 生成接口
    for fbn in generate_infos:
        gen_files(fbn, generate_infos[fbn])
        print("Generated:", fbn)
    # 生成 eos_interfaces.h
    gen_all_in_one()
    print("Generate Completed!")


# 在编译前调用
def preprocess():
    eos_base_file = os.path.join(sdk_include_dir, "eos_base.h")
    f = open(eos_base_file, "r")

    # 备份 eos_base.h
    bck = open("./.eos_base.h.bak", "w")
    bck.write(f.read())
    bck.close()

    # 除去 eos_base.h 中的 #define EOS_HAS_ENUM_CLASS, 影响枚举的绑定
    f.seek(0)
    lines: list[str] = f.readlines()
    f.close()

    for i in range(len(lines)):
        line = lines[i]
        if "#define EOS_HAS_ENUM_CLASS" in line and not line.startswith("//"):
            lines[i] = "//" + line

    f = open(eos_base_file, "w")
    f.write("".join(lines))
    f.close()


# 在编译后调用
def postprocess():
    eos_base_file = os.path.join(sdk_include_dir, "eos_base.h")
    backup_file = "./.eos_base.h.bak"
    if os.path.exists(backup_file):
        os.remove(eos_base_file)
        os.rename(backup_file, eos_base_file)


def _preprocess_docs():
    # 处理文档关键词映射
    for h in handles:
        h_info = handles[h]
        h_class = _convert_handle_class_name(h)
        for m in h_info["methods"]:
            doc_keyword_map_method[m] = {
                "class": h_class,
                "name": __convert_method_name(m, h),
            }

        for e in h_info["enums"]:
            doc_keyword_map_enum[e] = {
                "class": h_class,
                "name": _convert_enum_type(e),
            }

            for e_member in h_info["enums"][e]["members"]:
                doc_keyword_map_enum_member[e_member["name"]] = {
                    "class": h_class,
                    "name": _convert_enum_value(e_member["name"]),
                }

        for c in h_info["constants"]:
            as_method = _is_string_constant(c)
            doc_keyword_map_constant[c] = {
                "class": h_class,
                "name": _convert_constant_as_method_name(c) if as_method else _convert_constant_name(c),
                "as_method": as_method,
            }

        for cb in h_info["callbacks"]:
            doc_keyword_map_callback[cb] = {"class": h_class, "name": __convert_to_signal_name(cb)}

    for s in structs:
        doc_keyword_map_struct[s] = __convert_to_struct_class(s)

    # 优化文档
    for struct in structs:
        struct_info: dict = structs[struct]
        struct_info["doc"] = _optimize_doc(struct_info["doc"])

        for field in struct_info["fields"]:
            field_info = struct_info["fields"][field]
            field_info["doc"] = _optimize_doc(field_info["doc"])

    for h in handles:
        handle_info: dict = handles[h]
        handle_info["doc"] = _optimize_doc(handle_info["doc"])

        for m in handle_info["methods"]:
            m_info = handle_info["methods"][m]
            m_info["doc"] = _optimize_doc(m_info["doc"])

        for cb in handle_info["callbacks"]:
            cb_info = handle_info["callbacks"][cb]
            cb_info["doc"] = _optimize_doc(cb_info["doc"])

        for et in handle_info["enums"]:
            et_info = handle_info["enums"][et]
            et_info["doc"] = _optimize_doc(et_info["doc"])
            for e_info in handle_info["enums"][et]["members"]:
                e_info["doc"] = _optimize_doc(e_info["doc"])

        for c in handle_info["constants"]:
            c_info = handle_info["constants"][c]
            c_info["doc"] = _optimize_doc(c_info["doc"])


def __remove_backslash_of_last_line(lines: list[str]) -> None:
    if not len(lines):
        print("Error")
        _print_stack_and_exit()
    lines[len(lines) - 1] = lines[len(lines) - 1].removesuffix("\\")


def gen_all_in_one():
    lines: list[str] = []
    lines.append(f"#pragma once")
    lines.append("")

    register_classes_lines: list[str] = [""]

    register_classes_lines.append("namespace godot::eos {")

    register_classes_lines.append("#define REGISTER_EOS_CLASSES()\\")
    register_singleton_lines: list[str] = ["#define REGISTER_EOS_SINGLETONS()\\"]
    unregister_singleton_lines: list[str] = ["#define UNREGISTER_EOS_SINGLETONS()\\"]

    handle_types: list[str] = []
    for fbn in generate_infos:
        if len(generate_infos[fbn]["handles"]) <= 0:
            continue

        handle_class: str = ""
        for h in generate_infos[fbn]["handles"]:
            # Hack
            if h in ["EOS", "EOS_HAntiCheatCommon"]:
                break  # 跳过特殊类
            if h.removeprefix("EOS_H") in interfaces:
                handle_class = h
                break
        if len(handle_class):
            handle_types.append(handle_class)

        # 头文件
        if fbn in ["eos_common", "eos_anticheatcommon"]:
            continue
        if fbn == "eos_sdk":
            fbn = "eos_platform"
        lines.append(f"#include <interfaces/{fbn}_interface.h>")

    # 插入特殊类，调整注册顺序
    handle_types.insert(0, "EOS_HAntiCheatCommon")
    handle_types.insert(0, "EOS")

    for handle_type in handle_types:
        handle_class: str = _convert_handle_class_name(handle_type)
        register_classes_lines.append(f"\tEOS_REGISTER_{handle_class}\\")

        if handle_type in ["EOS", "EOS_HAntiCheatCommon"]:
            continue  # 特殊基类没有单例
        register_singleton_lines.append(
            f"\tgodot::Engine::get_singleton()->register_singleton(godot::eos::{handle_class}::get_class_static(), godot::eos::{handle_class}::get_singleton());\\"
        )
        if handle_type == "EOS_HPlatform":
            continue  # Platform 接口必须在最后析构
        unregister_singleton_lines.append(f"\tgodot::Engine::get_singleton()->unregister_singleton(godot::eos::{handle_class}::get_class_static());\\")
        unregister_singleton_lines.append(f"\tmemdelete(godot::eos::{handle_class}::get_singleton());\\")

    unregister_singleton_lines.append(f"\tgodot::Engine::get_singleton()->unregister_singleton(godot::eos::{ _convert_handle_class_name('EOS_HPlatform')}::get_class_static());\\")
    unregister_singleton_lines.append(f"\tmemdelete(godot::eos::{ _convert_handle_class_name('EOS_HPlatform')}::get_singleton());\\")
    __remove_backslash_of_last_line(register_classes_lines)
    __remove_backslash_of_last_line(register_singleton_lines)
    __remove_backslash_of_last_line(unregister_singleton_lines)

    register_singleton_lines.append("")
    unregister_singleton_lines.append("")

    register_classes_lines.append("")
    register_classes_lines.append("} // namesapce godot")
    register_classes_lines.append("")

    f = open(os.path.join(gen_include_dir, "eos_interfaces.h"), "w")
    f.write("\n".join(lines + register_classes_lines + register_singleton_lines + unregister_singleton_lines))
    f.close()


def _gen_disabled_macro(handle_type: str) -> str:
    if handle_type in ["EOS", "EOS_HPlatform"]:
        return ""
    return "EOS_" + handle_type.removeprefix("EOS_H").upper() + "_DISABLED"


def gen_files(file_base_name: str, infos: dict):
    eos_header = file_base_name + ".h"
    eos_types_header = file_base_name + ".h"
    if os.path.exists(os.path.join(sdk_include_dir, file_base_name + "_types.h")):
        eos_types_header = file_base_name + "_types.h"
    if not os.path.exists(os.path.join(sdk_include_dir, eos_header)):
        eos_header = eos_types_header

    if file_base_name == "eos_sdk":
        file_base_name = "eos_platform"

    handle_class: str = _convert_interface_class_name(file_base_name)

    enums_inline_file: str = os.path.join(gen_include_dir, "enums", file_base_name + ".enums.inl")

    structs_h_file: str = os.path.join(gen_include_dir, "structs", file_base_name + ".structs.h")
    structs_cpp_file: str = os.path.join(gen_src_dir, "structs", file_base_name + ".structs.cpp")

    packed_result_h_file: str = os.path.join(gen_include_dir, "packed_results", file_base_name + ".packed_results.h")
    packed_result_cpp_file: str = os.path.join(gen_src_dir, "packed_results", file_base_name + ".packed_results.cpp")

    handles_h_file: str = os.path.join(gen_include_dir, "handles", file_base_name + ".handles.h")
    handles_cpp_file: str = os.path.join(gen_src_dir, "handles", file_base_name + ".handles.cpp")

    interface_handle_h_file: str = os.path.join(gen_include_dir, "interfaces", file_base_name + "_interface.h")
    interface_handle_cpp_file: str = os.path.join(gen_src_dir, "interfaces", file_base_name + "_interface.cpp")
    #

    methods: dict = {}
    for m in infos["methods"]:
        methods[m] = infos["methods"][m]
    for h in infos["handles"]:
        for m in infos["handles"][h]["methods"]:
            methods[m] = infos["handles"][h]["methods"][m]

    # Handles
    interface_handle: str = ""
    sub_handles: dict = {}
    for h in infos["handles"]:
        # Hack
        if h in ["EOS", "EOS_HAntiCheatCommon"]:
            interface_handle = h
            continue
        if h.removeprefix("EOS_H") in interfaces:
            interface_handle = h
            continue
        sub_handles[h] = infos["handles"][h]

    macro_suffix = _convert_handle_class_name(interface_handle)

    # PackedResults h file
    packed_result_h_lines: list[str] = []
    packed_result_cpp_lines: list[str] = [f'#include <packed_results/{file_base_name + ".packed_results.h"}>']
    if len(sub_handles):
        packed_result_cpp_lines.append(f'#include <handles/{file_base_name + ".handles.h"}>')

    # 供绑定使用
    if len(interface_handle):
        packed_result_cpp_lines.append(f'#include <interfaces/{file_base_name + "_interface.h"}>')
    else:
        packed_result_cpp_lines.append(f'#include <{"eos_common_interface.h"}"')

    packed_result_cpp_lines.append("")
    packed_result_cpp_lines.append(f"using namespace godot::eos::internal;")
    packed_result_cpp_lines.append("namespace godot::eos {")
    has_packed_result: bool = gen_packed_results(file_base_name, eos_types_header, macro_suffix, methods, packed_result_h_lines, packed_result_cpp_lines)
    packed_result_cpp_lines.append("} // namespace godot::eos")
    packed_result_cpp_lines.append("")
    if has_packed_result:
        f = open(packed_result_h_file, "w")
        f.write("\n".join(packed_result_h_lines))
        f.close()
        f = open(packed_result_cpp_file, "w")
        f.write("\n".join(packed_result_cpp_lines))
        f.close()

    # Handles Gen
    if len(sub_handles):
        handles_cpp_lines: list[str] = [f'#include <handles/{file_base_name + ".handles.h"}>']
        handles_cpp_lines.append(f"#include <{file_base_name}.h>")

        # 供绑定使用
        if len(interface_handle):
            handles_cpp_lines.append(f'#include <interfaces/{file_base_name + "_interface.h"}>')
        else:
            handles_cpp_lines.append(f'#include <interfaces/{"eos_common_interface.h"}>')

        handles_cpp_lines.append(f"")
        additional_include_lines: list[str] = []
        if has_packed_result:
            additional_include_lines.append(f'#include <packed_results/{file_base_name + ".packed_results.h"}>')
        else:
            additional_include_lines.append(f"#include <{file_base_name}_types.h>")  # 句柄类型
            additional_include_lines.append(f"#include <core/utils.h>")  # is_equal() 使用其中的 _EOS_HANDLE_IS_EQUAL 宏

        if assume_only_one_local_user and file_base_name == "eos_common":
            # 假定只有一个用户时定义 EOS_ASSUME_ONLY_ONE_USER 宏
            additional_include_lines.append("")
            additional_include_lines.append("#define EOS_ASSUME_ONLY_ONE_USER")

        handles_hpp_lines: list[str] = gen_handles(interface_handle, additional_include_lines, sub_handles, handles_cpp_lines)

        if len(handles_hpp_lines):
            f = open(handles_h_file, "w")
            f.write("\n".join(handles_hpp_lines))
            f.close()

            f = open(handles_cpp_file, "w")
            f.write("\n".join(handles_cpp_lines))
            f.close()

    structs_to_gen: dict = {}
    for st in infos["structs"]:
        if _is_expanded_struct(st):
            continue
        if _is_need_skip_struct(st):
            continue
        structs_to_gen[st] = infos["structs"][st]

    if len(structs_to_gen):
        structs_cpp_lines: list[str] = [f'#include <structs/{file_base_name + ".structs.h"}>']
        if len(sub_handles) and len(handles_hpp_lines):
            structs_cpp_lines.append(f'#include <handles/{file_base_name + ".handles.h"}>')
        if file_base_name.startswith("eos_titlestorage") or file_base_name.startswith("eos_playerdatastorage"):
            structs_cpp_lines.append(f"#include <core/file_transfer.inl>")
        if file_base_name == "eos_platform":
            structs_cpp_lines.append(f"#include <handles/eos_integratedplatform.handles.h>")

        # 供绑定使用
        if len(interface_handle):
            structs_cpp_lines.append(f'#include <interfaces/{file_base_name + "_interface.h"}>')
        else:
            structs_cpp_lines.append(f'#include <interfaces/{"eos_common_interface.h"}>')

        additional_include_lines: list[str] = []
        if file_base_name.startswith("eos_anticheat"):
            additional_include_lines.append("#include <core/eos_anticheatcommon_client.h>")
        structs_h_lines: list[str] = gen_structs(
            file_base_name,
            eos_types_header,
            interface_handle,
            structs_to_gen,
            additional_include_lines,
            structs_cpp_lines,
        )

        # Structs h file
        f = open(structs_h_file, "w")
        f.write("\n".join(structs_h_lines))
        f.close()

        # Structs cpp file
        f = open(structs_cpp_file, "w")
        f.write("\n".join(structs_cpp_lines))
        f.close()

    # 检查
    if len(infos["enums"]):
        print(file_base_name, infos["enums"].keys())
    if len(infos["methods"]):
        print(file_base_name, infos["methods"].keys())
    if len(infos["callbacks"]):
        print(file_base_name, infos["callbacks"].keys())

    if len(interface_handle) <= 0:
        if not file_base_name in ["eos_logging"]:  # , "eos_init","eos_types"]:  # 这些文件均已处理
            print("ERR has not interface handle:", file_base_name)
        return

    # Enums inline file
    enums: dict = {}
    for e in infos["enums"]:
        enums[e] = infos["enums"][e]
    for h in infos["handles"]:
        handle_enums = infos["handles"][h]["enums"]
        for e in handle_enums:
            enums[e] = handle_enums[e]
    if len(enums):
        enums_inl: str = gen_enums(macro_suffix, interface_handle, enums)
        f = open(enums_inline_file, "w")
        f.write(enums_inl)
        f.close()

    # 生成接口
    disabled_macro: str = _gen_disabled_macro(interface_handle)
    interface_handle_h_lines: list[str] = []
    interface_handle_cpp_lines: list[str] = []
    interface_handle_h_lines.append(f"#pragma once")

    if len(disabled_macro):
        interface_handle_h_lines.append(f"#ifndef {disabled_macro}")
        interface_handle_cpp_lines.append(f"#ifndef {disabled_macro}")

    interface_handle_cpp_lines.append(f"#include <{eos_header}>")
    interface_handle_cpp_lines.append(f'#include <interfaces/{file_base_name+"_interface.h"}>')
    interface_handle_cpp_lines.append("")
    if file_base_name.startswith("eos_playerdatastorage") or file_base_name.startswith("eos_titlestorage"):
        interface_handle_cpp_lines.append(f"#include <core/file_transfer.inl>")
        interface_handle_cpp_lines.append("")

    for m in infos["handles"][interface_handle]["methods"]:
        if m.endswith("Interface"):
            splits: list[str] = m.split("_")
            _assert(len(splits) == 3)
            owner_handle_type = splits[1]
            interface = splits[2].removesuffix("Interface").removeprefix("Get")
            interface_low = interface.lower()

            interface_handle_type = ""
            if owner_handle_type == "Platform":
                # 从 Platform 获取的接口
                interface_handle_type = "EOS_H" + interface
            else:
                # 从其他接口获取的子接口
                interface_handle_type = "EOS_H" + owner_handle_type + interface
                owner_sub_handles = handles["EOS_H" + owner_handle_type].get("sub_handles", {})
                owner_sub_handles[interface_handle_type] = m
                handles["EOS_H" + owner_handle_type]["sub_handles"] = owner_sub_handles

            _disabled_macro = _gen_disabled_macro(interface_handle_type)

            _assert(len(_disabled_macro) > 0)
            if interface_low != "rtc" and (interface_low.startswith("rtc") or owner_handle_type == "RTC"):
                # rtc 开头的命名特殊处理
                interface_low = "rtc_" + interface_low.removeprefix("rtc")

            interface_handle_cpp_lines.append(f"#ifndef {_disabled_macro}")
            interface_handle_cpp_lines.append(f"#include <interfaces/eos_{interface_low}_interface.h>")
            interface_handle_cpp_lines.append(f"#endif // {_disabled_macro}")
    interface_handle_cpp_lines.append("")

    if file_base_name == "eos_common":
        interface_handle_h_lines.append(f"#include <eos_types.h>")
        interface_handle_h_lines.append(f"#include <eos_logging.h>")
        interface_handle_h_lines.append(f"#include <eos_version.h>")
        interface_handle_h_lines.append(f"#include <godot_cpp/classes/object.hpp>")
        interface_handle_h_lines.append(f"#include <godot_cpp/core/binder_common.hpp>")
        interface_handle_h_lines.append(f"#include <core/utils.h>")
        # interface_handle_h_lines.append(f"#include <structs/eos_init.structs.h>")
    elif file_base_name == "eos_anticheatcommon":
        interface_handle_h_lines.append(f'#include "eos_common_interface.h"')
    elif file_base_name.startswith("eos_anticheat"):
        interface_handle_h_lines.append(f'#include "eos_anticheatcommon_interface.h"')
    else:
        interface_handle_h_lines.append(f'#include "eos_common_interface.h"')

    if file_base_name.startswith("eos_platform"):
        interface_handle_h_lines.append(f"#include <godot_cpp/classes/engine.hpp>")
        interface_handle_h_lines.append(f"#include <godot_cpp/classes/main_loop.hpp>")
    interface_handle_h_lines.append(f"")

    if len(enums):
        interface_handle_h_lines.append(f'#include <enums/{file_base_name+".enums.inl"}>')
    if len(structs_to_gen):
        interface_handle_h_lines.append(f'#include <structs/{file_base_name+".structs.h"}>')
    if has_packed_result:
        interface_handle_h_lines.append(f'#include <packed_results/{file_base_name+".packed_results.h"}>')
    if len(sub_handles):
        interface_handle_h_lines.append(f'#include <handles/{file_base_name+".handles.h"}>')

    interface_handle_h_lines.append(f"")
    interface_handle_cpp_lines.append(f"using namespace godot::eos::internal;")
    interface_handle_cpp_lines.append(f"namespace godot::eos {{")

    interface_handle_h_lines += _gen_handle(
        interface_handle,
        infos["handles"][interface_handle],
        _convert_handle_class_name("EOS") if file_base_name == "eos_common" else macro_suffix,
        interface_handle_cpp_lines,
        [],
        True,
    )
    __remove_backslash_of_last_line(interface_handle_h_lines)
    interface_handle_cpp_lines.append(f"}} // namespace godot::eos")
    interface_handle_cpp_lines.append(f"")

    interface_handle_h_lines.append(f"#define EOS_REGISTER_{macro_suffix}\\")
    interface_handle_h_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS(godot::eos::{_convert_handle_class_name(interface_handle)})\\")
    if len(structs_to_gen):
        interface_handle_h_lines.append(f"\tREGISTER_DATA_CLASSES_OF_{macro_suffix}()\\")
    if has_packed_result:
        interface_handle_h_lines.append(f"\tREGISTER_PACKED_RESULTS_{macro_suffix}()\\")
    if len(sub_handles):
        interface_handle_h_lines.append(f"\tREGISTER_HANDLES_OF_{macro_suffix}()\\")

    __remove_backslash_of_last_line(interface_handle_h_lines)

    interface_handle_h_lines.append(f"")
    if len(disabled_macro):
        interface_handle_h_lines.append(f"#else // {disabled_macro}")
        # 生成空注册宏
        interface_handle_h_lines.append(f"#define EOS_REGISTER_{macro_suffix}")
        interface_handle_h_lines.append(f"#endif // {disabled_macro}")
        interface_handle_h_lines.append(f"")

        interface_handle_cpp_lines.append(f"#endif // {disabled_macro}")
        interface_handle_cpp_lines.append(f"")

    f = open(interface_handle_h_file, "w")
    f.write("\n".join(interface_handle_h_lines))
    f.close()

    f = open(interface_handle_cpp_file, "w")
    f.write("\n".join(interface_handle_cpp_lines))
    f.close()


def gen_enums(macro_suffix: str, handle_class: str, enums: dict) -> str:
    lines = ["#pragma once"]
    lines.append("")
    converted_handle_class = _convert_handle_class_name(handle_class)

    # Bind enum value macro
    for enum_type in enums:
        if _is_need_skip_enum_type(enum_type):
            continue
        lines.append(f"#define _BIND_ENUM_{enum_type}()\\")
        if _is_enum_flags_type(enum_type):
            for e_info in enums[enum_type]["members"]:
                e = e_info["name"]
                if _is_need_skip_enum_value(enum_type, e):
                    continue
                lines.append(f'\t_BIND_ENUM_BITFIELD_FLAG({enum_type}, {e}, "{_convert_enum_value(e)}")\\')
                # 文档
                _insert_doc_constant(converted_handle_class, _convert_enum_value(e), e_info["doc"])
        else:
            for e_info in enums[enum_type]["members"]:
                e = e_info["name"]
                if _is_need_skip_enum_value(enum_type, e):
                    continue
                lines.append(f'\t_BIND_ENUM_CONSTANT({enum_type}, {e}, "{_convert_enum_value(e)}")\\')
                # 文档
                _insert_doc_constant(converted_handle_class, _convert_enum_value(e), e_info["doc"])
        __remove_backslash_of_last_line(lines)
        lines.append("")

    # Bind macro
    lines.append(f"#define _BIND_ENUMS_{macro_suffix}()\\")
    for enum_type in enums:
        if _is_need_skip_enum_type(enum_type):
            continue
        lines.append(f"\t_BIND_ENUM_{enum_type}()\\")
    __remove_backslash_of_last_line(lines)
    lines.append("")

    # Using macro
    lines.append(f"#define _USING_ENUMS_{macro_suffix}()\\")
    for enum_type in enums:
        if _is_need_skip_enum_type(enum_type):
            continue
        lines.append(f"\tusing {_convert_enum_type(enum_type)} = {enum_type};\\")
    __remove_backslash_of_last_line(lines)
    lines.append("")

    # Variant cast macro
    lines.append(f"#define _CAST_ENUMS_{macro_suffix}()\\")
    for enum_type in enums:
        if _is_need_skip_enum_type(enum_type):
            continue
        if _is_enum_flags_type(enum_type):
            lines.append(f"\tVARIANT_BITFIELD_CAST(godot::eos::{converted_handle_class}::{_convert_enum_type(enum_type)})\\")
        else:
            lines.append(f"\tVARIANT_ENUM_CAST(godot::eos::{converted_handle_class}::{_convert_enum_type(enum_type)})\\")
    __remove_backslash_of_last_line(lines)
    lines.append("")

    return "\n".join(lines)


def gen_structs(
    file_base_name: str,
    types_include_file: str,
    handle_class: str,
    struct_infos: dict,
    additional_include_lines: str,
    r_cpp_lines: list[str],
) -> list[str]:
    r_cpp_lines.append("")
    r_cpp_lines.append(f"using namespace godot::eos::internal;")
    r_cpp_lines.append("namespace godot::eos {")

    lines: list[str] = []
    lines.append("#pragma once")
    lines.append("")

    # lines.append(f"#include <eos_sdk.h>")
    lines.append(f"#include <{types_include_file}>")
    lines.append(f"#include <godot_cpp/classes/ref_counted.hpp>")
    lines.append("")
    lines.append(f"#include <{eos_data_class_h_file}>")
    lines.append("")
    if len(additional_include_lines):
        lines += additional_include_lines
        lines.append("")

    lines.append("namespace godot::eos {")
    for struct_type in struct_infos:
        if _is_expanded_struct(struct_type):
            continue
        if _is_need_skip_struct(struct_type):
            continue
        lines += _gen_struct_v2(struct_type, struct_infos[struct_type], r_cpp_lines)

    lines.append(f"")
    r_cpp_lines.append("} // namespace godot::eos")
    r_cpp_lines.append("")

    lines.append("} // namespace godot::eos")
    lines.append("")

    ######### 生成绑定宏 #########
    lines.append("// ====================")
    lines.append(f"#define REGISTER_DATA_CLASSES_OF_{_convert_handle_class_name(handle_class)}()\\")
    for st in struct_infos:
        if _is_expanded_struct(st):
            continue
        if _is_need_skip_struct(st):
            continue
        lines.append(f"\tGDREGISTER_CLASS(godot::eos::{__convert_to_struct_class(st)})\\")
    __remove_backslash_of_last_line(lines)
    lines.append("")
    return lines


def gen_packed_results(file_base_name: str, types_include_file: str, register_macro_suffix: str, methods: dict, r_h_lines: list[str], r_cpp_lines: list[str]) -> bool:
    ret: bool = False
    r_h_lines.append("#pragma once")
    r_h_lines.append("")
    r_h_lines.append(f"#include <core/eos_packed_result.h>")
    r_h_lines.append(f"#include <{types_include_file}>")
    r_h_lines.append(f'#include <structs/{file_base_name+".structs.h"}>')
    r_h_lines.append("")
    r_h_lines.append("namespace godot::eos {")

    register_lines: list[str] = [f"#define REGISTER_PACKED_RESULTS_{register_macro_suffix}()\\"]
    for method in methods:
        if method.endswith("Release"):
            continue
        if _is_need_skip_method(method):
            continue
        if len(_gen_packed_result_type(method, methods[method], r_h_lines, r_cpp_lines, register_lines, [])):
            ret = True

    r_h_lines.append("")
    r_h_lines += register_lines
    __remove_backslash_of_last_line(r_h_lines)

    r_h_lines.append("")
    r_h_lines.append("} // namespace godot::eos")
    r_h_lines.append("")

    return ret


def gen_handles(interface_handle_class: str, additional_include_lines: list[str], p_handles: dict, r_cpp_lines: list[str]) -> list[str]:
    register_lines: list[str] = [f"#define REGISTER_HANDLES_OF_{_convert_handle_class_name(interface_handle_class)}()\\"]

    h_lines: list[str] = [f"#pragma once"]

    h_lines.append(f"#include <godot_cpp/classes/ref_counted.hpp>")
    h_lines.append(f"")
    if len(additional_include_lines):
        h_lines += additional_include_lines
        h_lines.append(f"")

    r_cpp_lines.append(f"using namespace godot::eos::internal;")
    r_cpp_lines.append(f"namespace godot::eos {{")
    for h in p_handles:
        if not _is_handle_type(h):
            continue  # Hack
        h_lines += _gen_handle(h, p_handles[h], _convert_handle_class_name(h), r_cpp_lines, register_lines)
    __remove_backslash_of_last_line(register_lines)

    r_cpp_lines.append(f"}} // namespace godot::eos")
    r_cpp_lines.append(f"")

    register_lines.append("")

    return h_lines + register_lines


def _make_notify_code(
    handle_class: str, add_notify_method: str, method_info: dict, options_type: str, r_member_lines: list[str], r_setup_lines: list[str], r_remove_lines: list[str]
):
    callback_type: str = ""
    for a in method_info["args"]:
        if __is_callback_type(_decay_eos_type(a["type"])):
            callback_type = a["type"]
    signal_name = __convert_to_signal_name(_decay_eos_type(callback_type), add_notify_method)
    id_identifier: str = f"notify_id_{signal_name}"

    remove_method = add_notify_method.replace("AddNotify", "RemoveNotify").removesuffix("V2")
    # Hack
    cb = _gen_callback(_decay_eos_type(callback_type), [])
    if "_EOS_METHOD_CALLBACK" in cb:
        if assume_only_one_local_user and _decay_eos_type(callback_type) in ["EOS_Connect_OnLoginStatusChangedCallback", "EOS_Auth_OnLoginStatusChangedCallback"]:
            gd_id_type = _get_gd_type_of_local_user_id(
                "LocalUserId", "EOS_ProductUserId" if _decay_eos_type(callback_type) == "EOS_Connect_OnLoginStatusChangedCallback" else "EOS_EpicAccountId"
            )
            cb = cb.replace("_EOS_METHOD_CALLBACK(", f"_CODE_SNIPPET_LOGIN_STATUS_CHANGED_CALLBACK({gd_id_type}, ")
        else:
            cb = cb.replace("_EOS_METHOD_CALLBACK", "_EOS_SIMPLE_NOTIFY_CALLBACK")
    elif "_EOS_METHOD_CALLBACK_EXPANDED" in cb:
        cb = cb.replace("_EOS_METHOD_CALLBACK_EXPANDED", "_EOS_SIMPLE_NOTIFY_CALLBACK_EXPANDED")
    else:
        print("ERROR")
        _print_stack_and_exit()

    r_member_lines.append(f"\tEOS_NotificationId {id_identifier}{{EOS_INVALID_NOTIFICATIONID}};")
    r_setup_lines.append("\tif (m_handle){")
    r_setup_lines.append(f"\t\t{options_type} options;")
    r_setup_lines.append(f"\t\toptions.ApiVersion = {__get_api_latest_macro(options_type)};")
    r_setup_lines.append(f"\t\t{id_identifier} = {add_notify_method}(m_handle, &options, this, {cb});")
    r_setup_lines.append("\t}")
    r_setup_lines.append(
        f'\tif ({id_identifier} == EOS_INVALID_NOTIFICATIONID) {{ WARN_PRINT("EOS: Setup signal \\"{handle_class}.{signal_name}\\" failed, this signal is not working."); }}'
    )
    r_remove_lines.append(f"\tif ({id_identifier} != EOS_INVALID_NOTIFICATIONID) {remove_method}(m_handle, {id_identifier});")


def _convert_constant_name(name: str) -> str:
    return name.removeprefix("EOS_")


def _convert_constant_as_method_name(name: str) -> str:
    return f'get_{name.removeprefix("EOS_").replace("OPT_", "ONLINE_PLATFORM_TYPE_").replace("IPT", "INTEGRATED_PLATFORM_TYPE_")}'


def _get_callback_type_of_method(method_info: dict) -> str:
    if len(method_info["args"]) >0:
        arg = method_info["args"][-1]
        if arg["type"].endswith("Callback") or arg["type"].endswith("CallbackV2"):
            return _decay_eos_type(arg["type"])
    return ""


def _gen_handle(
    handle_name: str,
    infos: dict,
    macro_suffix: str,
    r_cpp_lines: list[str],
    r_register_lines: list[str],
    need_singleton: bool = False,
) -> list[str]:
    is_base_handle_type = _is_base_handle_type(handle_name)
    base_class = _get_base_class(handle_name)
    if is_base_handle_type:
        need_singleton = False

    method_infos = infos["methods"]
    callback_infos = infos["callbacks"]

    klass = _convert_handle_class_name(handle_name)
    release_method: str = ""

    if assume_only_one_local_user and handle_name in ["EOS_ProductUserId", "EOS_EpicAccountId"]:
        r_cpp_lines.append(f"_CODE_SNIPPET_LOCAL_ID_DEFINE({klass})")

    if need_singleton:
        r_cpp_lines.append(f"{klass} *{klass}::singleton{{ nullptr }};")

    method_bind_lines: list[str] = []

    notifies_member_lines: list[str] = []
    setup_notifies_lines: list[str] = []
    remove_notifies_lines: list[str] = []

    for method in method_infos:
        if method.endswith("Release"):
            release_method = method
            break

    skip_remove_notify_methods: list[str] = []
    # Methods
    method_define_lines: list[str] = []
    methods_name_list: list[str] = []
    for m in method_infos:
        methods_name_list.append(m)
    methods_name_list.sort()

    need_notification_header :bool = False
    need_signal_callback_list :list[str] =[]
    for method in methods_name_list:
        if method.endswith("Release"):
            continue
        if _is_need_skip_method(method):
            continue
        if method.endswith("Interface"):
            continue  # 跳过接口获取方法

        method_info: dict = method_infos[method]
        if "AddNotify" in method:
            options_arg: dict = method_info["args"][1]
            options_type: str = options_arg["type"]
            decayed_options_type: str = _decay_eos_type(options_type)
            if __is_struct_type(decayed_options_type) and options_arg["name"].endswith("Options"):
                options_fields: dict = __get_struct_fields(decayed_options_type)

                valid_field_count = 0
                for field in options_fields:
                    if is_deprecated_field(field):  # 不计入弃用字段
                        continue
                    valid_field_count += 1

                if valid_field_count == 1 and "ApiVersion" in options_fields:
                    cb_type:str = _get_callback_type_of_method(method_info)
                    _assert(len(cb_type) > 0, f'{method} - {cb_type}')
                    need_signal_callback_list.append(cb_type)
                    _make_notify_code(klass, method, method_info, decayed_options_type, notifies_member_lines, setup_notifies_lines, remove_notifies_lines)

                    for m in method_infos:
                        if m == method:
                            continue
                        if method.replace("AddNotify", "RemoveNotify") in m:
                            skip_remove_notify_methods.append(m)
                    continue

        if "RemoveNotify" in method:
            continue  # 已处理

        _gen_method(
            handle_name,
            method,
            method_info,
            method_define_lines,
            r_cpp_lines,
            method_bind_lines,
        )
        r_cpp_lines.append("")

        if "AddNotify" in method:
            # 使用 EOSNotification, 不需要为其添加信号
            need_notification_header = True
        else:
            cb_type:str = _get_callback_type_of_method(method_info)
            if len(cb_type) > 0:
                need_signal_callback_list.append(cb_type)

    # to_string
    method_define_lines.append("")
    method_define_lines.append(f"\tString _to_string() const;")
    method_define_lines.append("")

    if klass == "EOS":
        method_define_lines.append("\t_EOS_GET_VERSION()")
        method_define_lines.append("\t_CODE_SNIPPET_DECLARE_LAST_RESULT_CODE()")
        method_define_lines.append("")

    # String Constants
    # Hack: Godot 不能绑定字符串常量，作为方法进行绑定
    has_string_constants = False
    for constant in infos["constants"]:
        const_value = infos["constants"][constant]["value"]
        if _is_string_constant(const_value):
            method_define_lines.append(f"\tstatic String {_convert_constant_as_method_name(constant)}() {{ return {constant}; }}")
            has_string_constants = True
            _insert_doc_method(klass, _convert_constant_as_method_name(constant), infos["constants"][constant]["doc"], {})
    if has_string_constants:
        method_define_lines.append("")

    if need_singleton:
        r_cpp_lines.append(f"{klass}::{klass}() {{")
        r_cpp_lines.append(f"\tERR_FAIL_COND(singleton!= nullptr);")
        r_cpp_lines.append(f"\tsingleton = this;")
        r_cpp_lines.append(f"}}")
        r_cpp_lines.append(f"")

    if len(release_method) or len(remove_notifies_lines):
        r_cpp_lines.append(f"{klass}::~{klass}() {{")
        if len(remove_notifies_lines):
            r_cpp_lines.append(f"\tif (m_handle) {{")
            for line in remove_notifies_lines:
                r_cpp_lines.append("\t" + line)
            r_cpp_lines.append(f"\t}}")
        if len(release_method):
            r_cpp_lines.append(f"\tif (m_handle) {{")
            r_cpp_lines.append(f"\t\t{release_method}(m_handle);")
            r_cpp_lines.append(f"\t}}")
        if need_singleton:
            r_cpp_lines.append(f"\tERR_FAIL_COND(singleton != this);")
            r_cpp_lines.append(f"\tsingleton = nullptr;")
            if handle_name == "EOS_HPlatform":
                r_cpp_lines.append(f"\tEOS_Shutdown();")
        r_cpp_lines.append(f"}}")

    if not is_base_handle_type:
        r_cpp_lines.append(f"void {klass}::set_handle({handle_name} p_handle) {{")
        r_cpp_lines.append(f"\tERR_FAIL_COND(m_handle); m_handle = p_handle;")

        if "sub_handles" in handles[handle_name]:
            for sub_handle in handles[handle_name]["sub_handles"]:
                get_method = handles[handle_name]["sub_handles"][sub_handle]
                sub_handle_snake_name = to_snake_case(sub_handle.removeprefix("EOS_H")) + "_handle"
                r_cpp_lines.append(f"#ifndef {_gen_disabled_macro(sub_handle)}")
                r_cpp_lines.append(f"\tif (m_handle) {{")
                r_cpp_lines.append(f"\t\tauto {sub_handle_snake_name} = {get_method}(m_handle);")
                r_cpp_lines.append(f"\t\t{_convert_handle_class_name(sub_handle)}::get_singleton()->set_handle({sub_handle_snake_name});")
                r_cpp_lines.append(f"\t}}")
                r_cpp_lines.append(f"#endif // {_gen_disabled_macro(sub_handle)}")

        if len(setup_notifies_lines):
            for line in setup_notifies_lines:
                r_cpp_lines.append(line)
        r_cpp_lines.append(f"}}")
        r_cpp_lines.append(f"")

    ret: list[str] = []
    if need_notification_header:
        ret.append("#include <core/eos_notification.h>")

    # 单例继承关系特殊处理
    inherits = f"public {base_class}"
    if base_class in [_convert_handle_class_name("EOS_HAntiCheatCommon")]:
        base_class = "Object"

    ret.append("namespace godot::eos {")
    ret.append(f"class {klass} : {inherits} {{")
    ret.append(f"\tGDCLASS({klass}, {base_class})")
    ret.append(f"")
    if not is_base_handle_type:
        ret.append(f"\t{handle_name} m_handle{{ nullptr }};")
        ret.append(f"")
    if len(notifies_member_lines):
        ret += notifies_member_lines
        ret.append("")
    if need_singleton:
        ret.append(f"\tstatic {klass} *singleton;")
        # ret.append(f"\tfriend class EOSPlatform;")
        ret.append(f"")
    if klass == "EOS":
        ret.append("public:")
        ret.append("\tstatic Callable &get_log_message_callback() {{ static Callable ret; return ret; }}")

    ret.append(f"protected:")
    ret.append(f"\tstatic void _bind_methods();")
    ret.append(f"")
    ret.append(f"public:")
    # USING 枚举
    if len(infos["enums"]):
        ret.append(f"\t_USING_ENUMS_{macro_suffix}()")
        ret.append(f"")
    if need_singleton:
        ret.append(f"\tstatic {klass} *get_singleton() {{ if (singleton == nullptr) {{singleton = memnew({klass});}} return singleton; }}")
        ret.append(f"")
    if need_singleton:
        ret.append(f"\t{klass}();")
    # Destructor
    if len(release_method) or len(remove_notifies_lines):  # and not is_base_handle_type:
        ret.append(f"\tvirtual ~{klass}() override;")
    # Handle setget
    if not is_base_handle_type:
        ret.append(f"\tvoid set_handle({handle_name} p_handle);")
        ret.append(f"\t{handle_name} get_handle() const {{ return m_handle; }}")
        if not need_singleton:
            # 非单例句柄类添加比较方法
            ret.append(f"\tbool is_equal(const Ref<{klass}> &p_other) const {{ _EOS_HANDLE_IS_EQUAL(m_handle, p_other); }}")
        ret.append(f"")

    ret += method_define_lines

    ret.append(f"")
    if handle_name == "EOS_HPlatform":
        # Platform自动Tick代码
        ret.append("\t_EOS_PLATFORM_SETUP_TICK()")

    if assume_only_one_local_user and handle_name in ["EOS_ProductUserId", "EOS_EpicAccountId"]:
        ret.append(f"\t_CODE_SNIPPET_LOCAL_ID_DECLARE({klass})")

    ret.append(f"}};")
    ret.append("} // namespace godot::eos")

    # CAST 枚举
    if len(infos["enums"]):
        ret.append(f"_CAST_ENUMS_{macro_suffix}()")
    ret.append(f"")

    # _to_string
    if handle_name in ["EOS_ProductUserId", "EOS_EpicAccountId"]:
        r_cpp_lines.append(f"String {klass}::_to_string() const {{")
        r_cpp_lines.append(f'\tString str{{"Invalid"}};')
        r_cpp_lines.append(f"\tif (m_handle) {{")
        r_cpp_lines.append(f"\t\tchar OutBuffer [{handle_name.upper()}_MAX_LENGTH + 1] {{}};")
        r_cpp_lines.append(f"\t\tint32_t InOutBufferLength{{ {handle_name.upper()}_MAX_LENGTH + 1 }};")
        r_cpp_lines.append(f"\t\tEOS_EResult result_code = {handle_name}_ToString(m_handle, &OutBuffer[0], &InOutBufferLength);")
        r_cpp_lines.append(f"\t\tEOS::_set_last_result_code(result_code);")
        r_cpp_lines.append(f"\t\tif (result_code != EOS_EResult::EOS_Success) {{")
        r_cpp_lines.append(f"\t\t\tstr = EOS_EResult_ToString(result_code);")
        r_cpp_lines.append(f"\t\t}} else {{")
        r_cpp_lines.append(f"\t\t\tstr = &OutBuffer[0];")
        r_cpp_lines.append(f"\t\t}}")
        r_cpp_lines.append(f"\t}}")
        r_cpp_lines.append(f'\treturn vformat("[{klass}:%s]", str);')
        r_cpp_lines.append(f"}}")
    else:
        r_cpp_lines.append(f'String {klass}::_to_string() const {{ return vformat("<{klass}#%d>", get_instance_id()); }}')
    r_cpp_lines.append("")

    # bind
    r_cpp_lines.append(f"void {klass}::_bind_methods() {{")
    r_cpp_lines += method_bind_lines
    if not need_singleton and not is_base_handle_type:
        # 非单例句柄类添加比较方法
        r_cpp_lines.append(f'\tClassDB::bind_method(D_METHOD("is_equal", "other"), &{klass}::is_equal);')
    for callback in callback_infos:
        if _is_need_skip_callback(callback):
            continue
        if callback == "EOS_LogMessageFunc":
            # log 回调为静态成员，不能添加信号
            continue

        if callback in need_signal_callback_list:
            _gen_callback(callback, r_cpp_lines, True)
    # BIND 枚举
    if len(infos["enums"]):
        r_cpp_lines.append(f"\t_BIND_ENUMS_{macro_suffix}()")
    # 常量
    for constant in infos["constants"]:
        if _is_string_constant(infos["constants"][constant]["value"]):
            r_cpp_lines.append(
                f'\tClassDB::bind_static_method(get_class_static(), D_METHOD("{_convert_constant_as_method_name(constant)}"), &{klass}::{_convert_constant_as_method_name(constant)});'
            )
        else:
            r_cpp_lines.append(f'\t_BIND_CONSTANT({constant}, "{_convert_constant_name(constant)}")')
    if klass == "EOS":
        r_cpp_lines.append("\t_EOS_BING_VERSION_CONSTANTS()")

    if assume_only_one_local_user and handle_name in ["EOS_ProductUserId", "EOS_EpicAccountId"]:
        r_cpp_lines.append(f"\t_CODE_SNIPPET_BINE_GET_LOCAL_ID({klass});")

    r_cpp_lines.append(f"}}")

    if klass == "EOS":
        r_cpp_lines.append("_CODE_SNIPPET_DEFINE_LAST_RESULT_CODE()")

    # 注册宏
    r_register_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS(godot::eos::{klass})\\")

    _insert_doc_class_brief(klass, infos["doc"])
    _insert_doc_class_description(klass)
    return ret


def _is_base_handle_type(handle_type: str) -> str:
    return handle_type in ["EOS", "EOS_HAntiCheatCommon"]


def _get_base_class(handle_type: str) -> str:
    if handle_type.startswith("EOS_HAntiCheat") and handle_type != "EOS_HAntiCheatCommon":
        return _convert_handle_class_name("EOS_HAntiCheatCommon")
    elif "EOS" == handle_type or "EOS_HAntiCheatCommon" == handle_type or handle_type.removeprefix("EOS_H") in interfaces:
        return "Object"
    else:
        return "RefCounted"


def _convert_to_interface_lower(file_name: str) -> str:
    splits = file_name.rsplit("\\", 1)
    f: str = splits[len(splits) - 1]
    if f == "eos_types.h":
        # Hack
        return "platform"
    if f in ["eos_init.h", "eos_logging.h"]:
        # logging 不单独作为一个接口
        return "common"
    return f.removesuffix("_types.h").removesuffix(".h").replace("_sdk", "_platform").removeprefix("eos_")


def _cheat_as_handle_method(method_name: str) -> str:
    map = {
        "EOS_IntegratedPlatform_CreateIntegratedPlatformOptionsContainer": "EOS_HIntegratedPlatform",
        "EOS_EpicAccountId_FromString": "EOS_EpicAccountId",
        "EOS_ProductUserId_FromString": "EOS_ProductUserId",
        # 公用（common）
        "EOS_EResult_ToString": "EOS",
        "EOS_EResult_IsOperationComplete": "EOS",
        "EOS_ByteArray_ToString": "EOS",
        "EOS_EApplicationStatus_ToString": "EOS",
        "EOS_ENetworkStatus_ToString": "EOS",
        "EOS_Logging_SetCallback": "EOS",
        "EOS_Logging_SetLogLevel": "EOS",
        #
        "EOS_Initialize": "EOS",
        "EOS_Shutdown": "EOS",
        "EOS_Platform_Create": "EOS_HPlatform",
    }
    return map.get(method_name, "")


def _cheat_as_handle_enum(enum_type: str) -> str:
    if enum_type.startswith("EOS_EAntiCheatCommon"):
        return "EOS_HAntiCheatCommon"
    map = {
        # Log (不单独开一个类)
        "EOS_ELogLevel": "EOS",
        "EOS_ELogCategory": "EOS",
        # 公用（common）
        "EOS_ELoginStatus": "EOS",
        "EOS_EAttributeType": "EOS",
        "EOS_EComparisonOp": "EOS",
        "EOS_EExternalAccountType": "EOS",
        "EOS_EExternalCredentialType": "EOS",
        "EOS_EResult": "EOS",
        #
        "EOS_ERTCBackgroundMode": "EOS",
        "EOS_EApplicationStatus": "EOS",
        "EOS_ENetworkStatus": "EOS",
        "EOS_EDesktopCrossplayStatus": "EOS",
        #
    }
    return map.get(enum_type, "")


def _cheat_as_handle_callback(callback_type: str) -> str:
    map = {
        "EOS_TitleStorage_OnReadFileDataCallback": "EOS_HTitleStorageFileTransferRequest",
        "EOS_TitleStorage_OnFileTransferProgressCallback": "EOS_HTitleStorageFileTransferRequest",
        "EOS_PlayerDataStorage_OnReadFileDataCallback": "EOS_HPlayerDataStorageFileTransferRequest",
        "EOS_PlayerDataStorage_OnWriteFileDataCallback": "EOS_HPlayerDataStorageFileTransferRequest",
        "EOS_PlayerDataStorage_OnFileTransferProgressCallback": "EOS_HPlayerDataStorageFileTransferRequest",
        #
        # "EOS_TitleStorage_OnReadFileCompleteCallback": "EOS_HTitleStorageFileTransferRequest",
        # "EOS_PlayerDataStorage_OnReadFileCompleteCallback": "EOS_HPlayerDataStorageFileTransferRequest",
        # "EOS_PlayerDataStorage_OnWriteFileCompleteCallback": "EOS_HPlayerDataStorageFileTransferRequest",
        "EOS_LogMessageFunc": "EOS",
    }
    return map.get(callback_type, "")


def _cheat_as_handle_constant(constant_name: str) -> str:
    if constant_name.startswith("EOS_ANTICHEATCOMMON_"):
        return "EOS_HAntiCheatCommon"
    if constant_name.startswith("EOS_IPT_"):
        return "EOS_HIntegratedPlatform"
    if constant_name in [
        "EOS_EPICACCOUNTID_MAX_LENGTH",
        "EOS_PRODUCTUSERID_MAX_LENGTH",
        "EOS_INVALID_NOTIFICATIONID",
        "EOS_PAGEQUERY_MAXCOUNT_DEFAULT",
        "EOS_PAGEQUERY_MAXCOUNT_MAXIMUM",
        "EOS_INITIALIZEOPTIONS_PRODUCTNAME_MAX_LENGTH",
        "EOS_INITIALIZEOPTIONS_PRODUCTVERSION_MAX_LENGTH",
    ] or constant_name.startswith("EOS_OPT_"):
        return "EOS"
    return ""


def parse_all_file():
    file_lower2infos: dict[str] = {}
    file_lower2infos[_convert_to_interface_lower("eos_common.h")] = {
        "file": "eos_common",
        "enums": {},
        "methods": {},
        "callbacks": {},
        "structs": {},
        "handles": {},
        "constants": {},
        "interface_doc": [],
    }
    file_lower2infos["platform"] = {"file": "eos_sdk", "enums": {}, "methods": {}, "callbacks": {}, "structs": {}, "handles": {}, "constants": {}, "interface_doc": []}

    for f in os.listdir(sdk_include_dir):
        fp = os.path.join(sdk_include_dir, f)
        if os.path.isdir(fp):
            continue

        if "deprecated" in f:
            continue

        if f in [
            "eos_base.h",
            "eos_platform_prereqs.h",
            "eos_version.h",
            # "eos_init.h",  # 在EOSCommon::init中使用，不再单独处理
            #
            "eos_result.h",
            "eos_ui_keys.h",
            "eos_ui_buttons.h",
        ]:  # 特殊处理
            continue
        interface_lower = _convert_to_interface_lower(f)
        if not interface_lower in file_lower2infos.keys():
            file_lower2infos[interface_lower] = {
                "file": f.removesuffix("_types.h").removesuffix(".h"),
                "methods": {},  # 最终为空
                "callbacks": {},  # 最终为空
                "enums": {},  # 最终为空
                "structs": {},  # 最终为空
                "handles": {},  # 最终为空
                "constants": {},  # 最终为空
                "interface_doc": [],  # 最终为空
            }
        _parse_file(interface_lower, fp, file_lower2infos)

    _get_EOS_EResult(file_lower2infos)
    _get_EOS_UI_EKeyCombination(file_lower2infos)
    _get_EOS_UI_EInputStateButtonFlags(file_lower2infos)

    extra_handles_methods: dict[str, dict] = {}
    # 将方法、回调，移动到对应的handle中,并检出接口类
    for il in file_lower2infos:
        _handles = file_lower2infos[il]["handles"]

        for infos in file_lower2infos.values():
            methods: dict[str, dict] = infos["methods"]
            to_remove_methods: list[str] = []
            for method_name in methods.keys():
                handle_type: str = ""
                callback_type: str = ""

                # 获取接口方法
                if "_Get" in method_name and method_name.endswith("Interface"):
                    splits: list[str] = method_name.split("_")
                    for i in range(len(splits)):
                        if splits[i] in ["EOS", "Platform"]:
                            splits[i] = ""
                        if splits[i].startswith("Get"):
                            splits[i] = splits[i].removeprefix("Get")
                        if splits[i].removesuffix("Interface"):
                            splits[i] = splits[i].removesuffix("Interface")
                    interfaces["".join(splits)] = methods[method_name]
                    to_remove_methods.append(method_name)

                    handle_type = _decay_eos_type(methods[method_name]["args"][0]["type"])
                    if not handle_type in extra_handles_methods:
                        extra_handles_methods[handle_type] = {}
                    extra_handles_methods[handle_type][method_name] = methods[method_name]
                    continue

                # 句柄方法
                for i in range(len(methods[method_name]["args"])):
                    arg: dict[str, str] = methods[method_name]["args"][i]
                    arg_type = _decay_eos_type(arg["type"])
                    if arg_type in _handles.keys() and i == 0:
                        # 移动到对应的handle中
                        if not method_name in to_remove_methods:
                            handle_type = arg_type
                            _handles[handle_type]["methods"][method_name] = methods[method_name]
                            to_remove_methods.append(method_name)
                    elif i == 0 and _is_handle_type(arg_type) and method_name.endswith("_Release"):
                        handle_type = _decay_eos_type(methods[method_name]["args"][0]["type"])
                        if not handle_type in extra_handles_methods:
                            extra_handles_methods[handle_type] = {}
                        extra_handles_methods[handle_type][method_name] = methods[method_name]
                        to_remove_methods.append(method_name)

                    if arg_type.endswith("Callback") or arg_type.endswith("CallbackV2"):
                        # 需要被移动的回调
                        callback_type = arg_type

                # Release 方法
                if method_name.endswith("_Release"):
                    if not len(handle_type):
                        release_methods[method_name] = methods[method_name]
                        to_remove_methods.append(method_name)
                        continue

                # 移动回调类型
                if len(handle_type) and len(callback_type):
                    _handles[handle_type]["callbacks"][callback_type] = infos["callbacks"][callback_type]
                    infos["callbacks"].pop(callback_type)

            for m in to_remove_methods:
                infos["methods"].pop(m)

        # 处理接口句柄文档
        interface_doc: list[str] = file_lower2infos[il]["interface_doc"]
        if len(interface_doc):
            interface_handle_type: str = ""
            for i in range(len(interface_doc)):
                l: str = interface_doc[i]
                if l.startswith("@see EOS_Platform_Get") and l.strip().endswith("Interface"):
                    interface_handle_type = l.removeprefix("@see EOS_Platform_Get").strip().removesuffix("Interface")
                    if interface_handle_type != "EOS":
                        interface_handle_type = "EOS_H" + interface_handle_type

                    # 移除该行与上一空行
                    interface_doc.pop(i)
                    if len(interface_doc[i - 1].strip()) <= 0:
                        interface_doc.pop(i - 1)
                    break
            if interface_handle_type in _handles:
                _handles[interface_handle_type]["doc"] = interface_doc
            else:
                handles[interface_handle_type]["doc"] = interface_doc
            file_lower2infos[il]["interface_doc"] = []

        # 检查文档是否被正确使用
        if len(file_lower2infos[il]["interface_doc"]) > 0:
            print("ERROR: ", il)
            exit()

    # 初始化生成信息
    for il in file_lower2infos:
        infos: dict = file_lower2infos[il]
        generate_infos[infos["file"]] = {
            "handles": {},
            "structs": {},
            "enums": {},
            "constants": {},
            #
            "callbacks": {},
            "methods": {},
        }

    # 移动句柄
    for il in file_lower2infos:
        for h in file_lower2infos[il]["handles"]:
            handles[h] = file_lower2infos[il]["handles"][h]
            generate_infos[file_lower2infos[il]["file"]]["handles"][h] = file_lower2infos[il]["handles"][h]
        file_lower2infos[il].pop("handles")

    generate_infos["eos_common"]["handles"]["EOS"] = handles["EOS"]
    generate_infos["eos_anticheatcommon"]["handles"]["EOS_HAntiCheatCommon"] = handles["EOS_HAntiCheatCommon"]

    # 移动结构体
    for il in file_lower2infos:
        for s in file_lower2infos[il]["structs"]:
            structs[s] = file_lower2infos[il]["structs"][s]
            generate_infos[file_lower2infos[il]["file"]]["structs"][s] = file_lower2infos[il]["structs"][s]
        file_lower2infos[il].pop("structs")

    # 移动枚举
    for il in file_lower2infos:
        interface = _convert_interface_class_name(il).removeprefix("EOS")
        if interface in interfaces:
            handles["EOS_H" + interface]["enums"] = file_lower2infos[il]["enums"]
            for e in file_lower2infos[il]["enums"]:
                generate_infos[file_lower2infos[il]["file"]]["handles"]["EOS_H" + interface]["enums"][e] = file_lower2infos[il]["enums"][e]
            file_lower2infos[il].pop("enums")  # 容器为引用类型，不能直接clear()
            file_lower2infos[il]["enums"] = {}

    # 移动常量
    for il in file_lower2infos:
        interface = _convert_interface_class_name(il).removeprefix("EOS")
        if interface in interfaces:
            handles["EOS_H" + interface]["constants"] = file_lower2infos[il]["constants"]
            for e in file_lower2infos[il]["constants"]:
                generate_infos[file_lower2infos[il]["file"]]["handles"]["EOS_H" + interface]["constants"][e] = file_lower2infos[il]["constants"][e]
            file_lower2infos[il].pop("constants")  # 容器为引用类型，不能直接clear()
            file_lower2infos[il]["constants"] = {}

    # Cheat as handle's method
    for il in file_lower2infos:
        methods = file_lower2infos[il]["methods"]
        to_remove: list[str] = []
        for m in methods:
            cheat_handle_type = _cheat_as_handle_method(m)
            if not len(cheat_handle_type):
                print("WARN: has not owned handle method:", m)
                continue
            if not cheat_handle_type in handles:
                print(handles.keys())
                print("ERR UNKNOWN handle type:", cheat_handle_type)
                _print_stack_and_exit()
            handles[cheat_handle_type]["methods"][m] = methods[m]
            to_remove.append(m)
        for m in to_remove:
            methods.pop(m)

    # Cheat as handle's enum
    for il in file_lower2infos:
        enums = file_lower2infos[il]["enums"]
        to_remove: list[str] = []
        for e in enums:
            cheat_handle_type = _cheat_as_handle_enum(e)
            if not len(cheat_handle_type):
                print("WARN: has not owned handle enum type:", e)
                continue
            if not cheat_handle_type in handles:
                print("ERR UNKNOWN handle type:", cheat_handle_type)
                _print_stack_and_exit()
            handles[cheat_handle_type]["enums"][e] = enums[e]
            to_remove.append(e)
        for e in to_remove:
            enums.pop(e)

    # Hack
    to_remove_enum_types: list[str] = []
    for enum in handles["EOS_HPlatform"]["enums"]:
        cheat = _cheat_as_handle_enum(enum)
        if len(cheat) and cheat != "EOS_HPlatform":
            handles[cheat]["enums"][enum] = handles["EOS_HPlatform"]["enums"][enum]
            to_remove_enum_types.append(enum)
    for e in to_remove_enum_types:
        handles["EOS_HPlatform"]["enums"].pop(e)

    for h in extra_handles_methods:
        for m in extra_handles_methods[h]:
            handles[h]["methods"][m] = extra_handles_methods[h][m]

    # Cheat as handle's callback
    for il in file_lower2infos:
        callbacks = file_lower2infos[il]["callbacks"]
        to_remove: list[str] = []
        for cb in callbacks:
            cheat_handle_type = _cheat_as_handle_callback(cb)
            if not len(cheat_handle_type):
                print("WARN: has not owned handle callback type:", cb)
                continue
            if not cheat_handle_type in handles:
                print("ERR UNKNOWN handle type:", cheat_handle_type)
                _print_stack_and_exit()
            handles[cheat_handle_type]["callbacks"][cb] = callbacks[cb]
            to_remove.append(cb)
        for cb in to_remove:
            callbacks.pop(cb)

    # Cheat as handle's constants
    for il in file_lower2infos:
        constants = file_lower2infos[il]["constants"]
        to_remove: list[str] = []
        for c in constants:
            cheat_handle_type = _cheat_as_handle_constant(c)
            if not len(cheat_handle_type):
                print("WARN: has not owned constant:", c)
                continue
            if not cheat_handle_type in handles:
                print("ERR UNKNOWN handle type:", cheat_handle_type)
                _print_stack_and_exit()
            handles[cheat_handle_type]["constants"][c] = constants[c]
            to_remove.append(c)
        for c in to_remove:
            constants.pop(c)

    # 复制特殊的回调
    handles["EOS_HTitleStorageFileTransferRequest"]["callbacks"]["EOS_TitleStorage_OnReadFileCompleteCallback"] = handles["EOS_HTitleStorage"]["callbacks"][
        "EOS_TitleStorage_OnReadFileCompleteCallback"
    ]
    handles["EOS_HPlayerDataStorageFileTransferRequest"]["callbacks"]["EOS_PlayerDataStorage_OnReadFileCompleteCallback"] = handles["EOS_HPlayerDataStorage"]["callbacks"][
        "EOS_PlayerDataStorage_OnReadFileCompleteCallback"
    ]
    handles["EOS_HPlayerDataStorageFileTransferRequest"]["callbacks"]["EOS_PlayerDataStorage_OnWriteFileCompleteCallback"] = handles["EOS_HPlayerDataStorage"]["callbacks"][
        "EOS_PlayerDataStorage_OnWriteFileCompleteCallback"
    ]

    # Check
    # 未处理的方法、回调、枚举
    for il in file_lower2infos:
        for cb in file_lower2infos[il]["callbacks"]:
            unhandled_callbacks[cb] = file_lower2infos[il]["callbacks"][cb]
            generate_infos[file_lower2infos[il]["file"]]["callbacks"][cb] = file_lower2infos[il]["callbacks"][cb]

        for m in file_lower2infos[il]["methods"]:
            unhandled_methods[m] = file_lower2infos[il]["methods"][m]
            generate_infos[file_lower2infos[il]["file"]]["methods"][m] = file_lower2infos[il]["methods"][m]

        for e in file_lower2infos[il]["enums"]:
            unhandled_enums[e] = file_lower2infos[il]["enums"][e]
            generate_infos[file_lower2infos[il]["file"]]["enums"][e] = file_lower2infos[il]["enums"][e]

        for c in file_lower2infos[il]["constants"]:
            unhandled_constants[c] = file_lower2infos[il]["constants"][c]
            generate_infos[file_lower2infos[il]["file"]]["constants"][c] = file_lower2infos[il]["constants"][c]

        if len(file_lower2infos[il]["callbacks"]):
            if not il in unhandled_infos:
                unhandled_infos[il] = {}
            unhandled_infos[il]["callbacks"] = file_lower2infos[il]["callbacks"]
        if len(file_lower2infos[il]["methods"]):
            if not il in unhandled_infos:
                unhandled_infos[il] = {}
            unhandled_infos[il]["methods"] = file_lower2infos[il]["methods"]
        if len(file_lower2infos[il]["enums"]):
            if not il in unhandled_infos:
                unhandled_infos[il] = {}
            unhandled_infos[il]["enums"] = file_lower2infos[il]["enums"]
        if len(file_lower2infos[il]["constants"]):
            if not il in unhandled_infos:
                unhandled_infos[il] = {}
            print(file_lower2infos[il]["constants"].keys())
            unhandled_infos[il]["constants"] = file_lower2infos[il]["constants"]

        file_lower2infos[il].pop("callbacks")
        file_lower2infos[il].pop("methods")
        file_lower2infos[il].pop("enums")
        file_lower2infos[il].pop("constants")

    classes: list[str] = []
    for il in file_lower2infos.keys():
        classes.append(_convert_interface_class_name(il).removeprefix("EOS"))

    for up in interfaces:
        if not up in classes:
            print("?? :", up)
        else:
            classes.remove(up)

    _make_additional_method_requirements()

    for il in unhandled_infos:
        print(
            f'{il}\t\t\tcb:{len(unhandled_infos[il].get("callbacks", {}))}\tmethods:{len(unhandled_infos[il].get("methods",{}))}\tenums:{len(unhandled_infos[il].get("enums",{}))}\tconstantes:{len(unhandled_infos[il].get("constants", {}))}'
        )


def _convert_interface_class_name(interface_name_lower: str) -> str:
    if interface_name_lower in ["eos_common", "common", "e_o_s"]:
        interface_name_lower = "eos"
    if interface_name_lower == "eos":
        return "EOS"
    if interface_name_lower == "eos_userinfo":
        return "EOSUserInfoInterface"
    name_splits = interface_name_lower.removeprefix("eos_").split("_")
    for i in range(len(name_splits)):
        if name_splits[i] in ["rtc", "p2p", "ui"]:
            name_splits[i] = name_splits[i].upper()
        elif name_splits[i] == "playerdatastorage":
            name_splits[i] = "PlayerDataStorage"
        elif name_splits[i] == "p2p":
            name_splits[i] = "P2P"
        elif name_splits[i] == "sdk":
            name_splits[i] = "Platform"
        elif name_splits[i] == "userinfo":
            name_splits[i] = "UserInfo"
        elif name_splits[i] == "titlestorage":
            name_splits[i] = "TitleStorage"
        elif name_splits[i] == "anticheatserver":
            name_splits[i] = "AntiCheatServer"
        elif name_splits[i] == "anticheatclient":
            name_splits[i] = "AntiCheatClient"
        elif name_splits[i] == "anticheatcommon":
            name_splits[i] = "AntiCheatCommon"
        elif name_splits[i] == "progressionsnapshot":
            name_splits[i] = "ProgressionSnapshot"
        elif name_splits[i] == "kws":
            name_splits[i] = "KWS"
        elif name_splits[i] == "custominvites":
            name_splits[i] = "CustomInvites"
        elif name_splits[i] == "integratedplatform":
            name_splits[i] = "IntegratedPlatform"
        else:
            name_splits[i] = name_splits[i].capitalize()

    return "EOS" + "".join(name_splits)


def _convert_handle_class_name(handle_type: str) -> str:
    if handle_type == "EOS_HUserInfo":
        return "EOSUserInfoInterface"
    text = handle_type.removeprefix("EOS_H")
    if text == "EOS":
        return text
    if text.startswith("EOS_"):
        text = text.replace("EOS_", "EOS")
    if not text.startswith("EOS"):
        text = "EOS" + text
    return text


def _is_enum_type(type: str) -> bool:
    for h in handles:
        if type in handles[h]["enums"]:
            return True
    if type in unhandled_enums:
        print("WARN: ", type)
        return True
    return False


def _convert_result_type(method_name: str) -> str:
    return "EOS" + method_name.split("_", 1)[1] + "Result"


def _gen_packed_result_type(
    method_name: str,
    method_info: dict,
    r_h_lines: list[str],
    r_cpp_lines: list[str],
    r_register_lines: list[str],
    r_need_convert_to_return_value: list[bool],
    get_type_name_only: bool = False,
    # 返回 EOS_EResult 并且只有单个对象类型的返回参数 时重新映射的返回值类型。
    r_remapped_result_type: list[str] = [],
) -> str:
    out_args: list[dict[str, str]] = []
    for i in range(len(method_info["args"])):
        arg_name: str = method_info["args"][i]["name"]
        arg_type: str = method_info["args"][i]["type"]
        if (arg_name.startswith("Out") or arg_name.startswith("InOut") or arg_name.startswith("bOut")) and arg_type.endswith("*"):
            out_args.append(method_info["args"][i])
    if len(out_args) <= 0:
        return ""
    #
    if len(method_info["return"]) <= 0 or method_info["return"] == "void":
        if len(out_args) == 1:
            r_need_convert_to_return_value.append[True]
            return ""
        if len(out_args) == 2:
            if (out_args[0]["type"] == "char*" and out_args[1]["type"].endswith("int32_t*") and out_args[1]["name"].endswith("Length")) or (
                out_args[0]["type"] == "void*" and out_args[1]["type"].endswith("int32_t*")
            ):
                r_need_convert_to_return_value.append[True]
                return ""

    if method_info["return"] == "EOS_EResult" and len(out_args) == 1:
        arg_name: str = out_args[0]["name"]
        arg_type: str = out_args[0]["type"]
        decayed_type: str = _decay_eos_type(arg_type)
        if _is_handle_type(decayed_type) and not _is_handle_arr_type(arg_type, arg_name):
            r_remapped_result_type.append(f"Ref<{_convert_handle_class_name(decayed_type)}>")
            return ""
        if __is_struct_type(decayed_type):
            r_remapped_result_type.append(f"Ref<{__convert_to_struct_class(decayed_type)}>")
            return ""

    typename: str = _convert_result_type(method_name)
    if get_type_name_only:
        return typename

    members_lines: list[str] = []
    setget_lines: list[str] = []
    bind_lines: list[str] = []
    i = 0
    while i < len(out_args):
        arg: dict[str, str] = out_args[i]
        arg_type: str = arg["type"]
        arg_name: str = arg["name"]
        decayed_type: str = _decay_eos_type(arg_type)
        snake_name: str = to_snake_case(arg_name.removeprefix("IntOut").removeprefix("Out").removeprefix("bOut"))
        if _is_handle_arr_type(arg_type, arg_name):
            print("ERROR UNSUPPORTED handle arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_handle_type(decayed_type):
            # Handle 类型需要前向声明
            handle_class = _convert_handle_class_name(decayed_type)
            members_lines.append(f"\tRef<RefCounted> {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET_TYPED({snake_name}, Ref<class {handle_class}>)")
            r_cpp_lines.append(f"_DEFINE_SETGET_TYPED({typename}, {snake_name}, Ref<{handle_class}>)")
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_name}, {handle_class})")
        elif __is_struct_type(decayed_type):
            members_lines.append(f"\tRef<{__convert_to_struct_class(decayed_type)}> {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_name}, {__convert_to_struct_class(decayed_type)})")
        elif _is_pure_handle_type(decayed_type):
            members_lines.append(f"\t{remap_type(decayed_type)} {snake_name}{{ 0 }};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f'\t_BIND_PROP_OBJ({snake_name}, {remap_type(arg_type).removesuffix("*")})')
        elif _is_enum_type(decayed_type):
            enum_owner: str = _get_enum_owned_interface(decayed_type)
            members_lines.append(f"\t{decayed_type} {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_ENUM({snake_name}, {enum_owner}, {_convert_enum_type( decayed_type)})")
        elif _is_socket_id_type(decayed_type, arg_name):
            members_lines.append(f"\tString {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP({snake_name})")
        elif _is_str_type(arg_type, arg_name):
            print("ERROR: UNSUPPORTED")
            _print_stack_and_exit()
        elif _is_str_arr_type(arg_type, arg_name):
            print("ERROR: UNSUPPORTED")
            _print_stack_and_exit()
        elif arg_type == "char*" and (i + 1) < len(out_args) and out_args[i + 1]["type"].endswith("int32_t*") and out_args[i + 1]["name"].endswith("Length"):
            # 配合 _MAX_LENGTH 宏的字符串
            members_lines.append(f"\tString {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP({snake_name})")
            i += 1
        elif arg_type == "void*" and (i + 1) <= len(out_args) and out_args[i + 1]["type"].endswith("int32_t*"):
            if out_args[i + 1]["name"] != "OutBytesWritten":
                print("WARN:", method_name)
            members_lines.append(f"\tPackedByteArray {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP({snake_name})")
            i += 1
        elif decayed_type == "EOS_Bool":
            members_lines.append(f"\tbool {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET_BOOL({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET_BOOL({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_BOOL({snake_name})")
            i += 1
        elif _is_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORTED arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_internal_struct_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORTED struct arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_audio_frames_type(arg_type, arg_name):
            print("ERROR UNSUPPORTED struct arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_enum_flags_type(arg_type):
            members_lines.append(f"\tBitField<{decayed_type}> {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET_FLAGS({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET_FLAGS({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_BITFIELD({snake_name})")
        else:
            members_lines.append(f"\t{remap_type(decayed_type)} {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP({snake_name})")

        i += 1

    # r_h_lines.append("namespace godot::eos {")
    r_h_lines.append(f"class {typename} : public EOSPackedResult {{")
    r_h_lines.append(f"\tGDCLASS({typename}, EOSPackedResult)")
    r_h_lines.append(f"public:")
    if method_info["return"] == "EOS_EResult":
        r_h_lines.append(f"\tEOS_EResult result_code{{ EOS_EResult::EOS_InvalidParameters }};")
    else:
        print("ERROR unsupported to gen packed result:", method_name)
    r_h_lines += members_lines
    r_h_lines.append("")
    r_h_lines.append(f"public:")
    if method_info["return"] == "EOS_EResult":
        r_h_lines.append(f"\t_DECLARE_SETGET(result_code);")
        r_cpp_lines.append(f"_DEFINE_SETGET({typename}, result_code)")
    r_h_lines += setget_lines
    r_h_lines.append("")
    r_h_lines.append(f"protected:")
    r_h_lines.append(f"\tstatic void _bind_methods();")
    r_h_lines.append(f"}};")
    # r_h_lines.append("} // namespace godot::eos")
    r_h_lines.append(f"")

    #
    r_cpp_lines.append(f"void {typename}::_bind_methods() {{")
    r_cpp_lines.append(f"\t_BIND_BEGIN({typename});")
    if method_info["return"] == "EOS_EResult":
        r_cpp_lines.append(f'\t_BIND_PROP_ENUM(result_code, EOS_Common, {_convert_enum_type("EOS_EResult")})')
    r_cpp_lines += bind_lines
    r_cpp_lines.append(f"\t_BIND_END();")
    r_cpp_lines.append(f"}}")
    r_cpp_lines.append(f"")

    r_register_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS(godot::eos::{typename})\\")

    handle = __find_method_handle_type(method_name)
    _insert_doc_class_brief(typename, [f"The result type of [method {_convert_handle_class_name(handle)}.{__convert_method_name(method_name)}].\n"])
    _insert_doc_class_description(typename)
    return typename


def __is_struct_type(type: str) -> bool:
    # HACK
    if _is_socket_id_type(_decay_eos_type(type), ""):
        return False
    # HACK
    if type in ["EOS_AntiCheatCommon_Vec3f", "EOS_AntiCheatCommon_Quat"]:
        return False
    return type in structs


def __is_callback_type(type: str) -> bool:
    for h in handles:
        if type in handles[h]["callbacks"]:
            return True
    if type in unhandled_callbacks:
        print("WARN unhandled callback ty:", type)
        return True
    return False


def __is_client_data(type: str, name: str) -> bool:
    return type == "void*" and name == "ClientData"


def __is_api_version_field(type: str, name: str) -> bool:
    return type == "int32_t" and name == "ApiVersion"


def __get_struct_fields(type: str) -> dict[str, dict]:
    return structs[_decay_eos_type(type)]["fields"]


def __convert_to_signal_name(callback_type: str, method_name: str = "") -> str:
    if len(method_name) <= 0:
        for infos in handles.values():
            methods = infos["methods"]
            for m in methods:
                for a in methods[m]["args"]:
                    if _decay_eos_type(a["type"]) == callback_type:
                        if len(method_name):
                            print("ERROR: ", callback_type, method_name)
                            _print_stack_and_exit()
                        method_name = m

    ret = to_snake_case(callback_type.rsplit("_", 1)[1])
    if ret.endswith("_callback_v2"):
        ret = ret.removesuffix("_callback_v2") + "_v2"
    ret = ret.removesuffix("_callback")
    if "AddNotify" in method_name:
        ret = ret.removeprefix("on_")
    elif callback_type in [
        # 对传输完成信号名进行特殊处理
        "EOS_PlayerDataStorage_OnWriteFileCompleteCallback",
        "EOS_PlayerDataStorage_OnReadFileCompleteCallback",
        "EOS_TitleStorage_OnReadFileCompleteCallback",
    ]:
        ret = ret.removeprefix("on_") + "d"
    return ret


# 结构体，被展开的结构体
def _need_ignore_local_user_id_struct(struct_type: str) -> bool:
    struct_type = _decay_eos_type(struct_type)
    for prefix in [
        "EOS_Achievements_",  # 服务端可空 （TODO: 再看看， 如果不能查别人的就挪到下面去）
        "EOS_Connect_",  # 需要管理产品id的关联
        "EOS_Auth_",  # 需要管理账号的关联
    ]:
        if struct_type.startswith(prefix):
            return False
    return True


def _need_check_null_local_user_id_struct(struct_type: str) -> bool:
    struct_type = _decay_eos_type(struct_type)
    return (
        not struct_type
        in [
            "EOS_AntiCheatServer_BeginSessionOptions",  # 服务器为空
            "EOS_Connect_QueryProductUserIdMappingsOptions",  # 服务器为空
            "EOS_Stats_IngestStatOptions",  # 服务器可空
            "EOS_Stats_QueryStatsOptions",  # 服务器可空
        ]
        and not struct_type.startswith("EOS_TitleStorage_")
        and not struct_type.startswith("EOS_Achievements_")
    )


def __convert_to_struct_class(struct_type: str) -> str:
    return _decay_eos_type(struct_type).replace("EOS_", "EOS")


def _gen_callback(
    callback_type: str,
    r_bind_signal_lines: list[str],
    for_gen_signal_binding: bool = False,
    for_notification: bool = False,
) -> str:
    (infos, handle, method) = _get_callback_infos_v2(callback_type)
    method = __convert_method_name(method, handle) if len(method) else method
    handle = _convert_handle_class_name(handle)

    if not len(infos["args"]) == 1:
        # 特殊处理
        if not callback_type in ["EOS_PlayerDataStorage_OnWriteFileDataCallback"]:
            print("ERROR:", callback_type)
            exit()

    arg: dict[str, str] = infos["args"][0]
    arg_type: str = arg["type"]
    arg_name: str = arg["name"]
    return_type: str = infos["return"]

    if not __is_struct_type(_decay_eos_type(arg_type)):
        print("ERROR unsupported callback:", callback_type)
        _print_stack_and_exit()

    signal_name = __convert_to_signal_name(callback_type)
    if not _is_expanded_struct(_decay_eos_type(arg_type)):
        r_bind_signal_lines.append(
            f'\tADD_SIGNAL(MethodInfo("{signal_name}", _MAKE_PROP_INFO({__convert_to_struct_class(_decay_eos_type(arg_type))}, {to_snake_case(arg_name)})));'
        )
        gd_cb_info_type = remap_type(_decay_eos_type(arg_type), arg_name).removeprefix("Ref<").removesuffix(">")
        ret = ""
        if callback_type == "EOS_IntegratedPlatform_OnUserPreLogoutCallback":
            ret = f'_EOS_USER_PRE_LOGOUT_CALLBACK({arg_type}, data, "{signal_name}", {gd_cb_info_type})'
        elif len(return_type):
            if for_gen_signal_binding:
                return ""
            print("ERROR unsupported callback type:", callback_type)
            _print_stack_and_exit()
        else:
            if not for_notification:
                ret = f'_EOS_METHOD_CALLBACK({arg_type}, data, "{signal_name}", {gd_cb_info_type})'
            else:
                ret = f'_EOS_NOTIFY_CALLBACK({arg_type}, data, {gd_cb_info_type})'

        additional_doc: list[str] = []
        if len(method) and signal_name.startswith("on_"):
            additional_doc.append(f"Callback of [method {method}].\n")
        _insert_doc_signal(handle, signal_name, infos["doc"], {}, additional_doc)
        return ret
    else:
        fields: dict[str, str] = __get_struct_fields(_decay_eos_type(arg_type))

        ## 检出不需要成为参数的字段
        count_and_variant_type_fields: list[str] = __find_count_and_variant_type_fields_in_struct(_decay_eos_type(arg_type))

        ##
        ret: str = ""
        signal_bind_args: str = ""

        expanded_args_doc: dict[str, list[str]] = {}

        if len(return_type):
            if for_gen_signal_binding:
                return ""
            print("ERROR unsupported callback type:", callback_type)
            _print_stack_and_exit()
        else:
            if not for_notification:
                ret = f'\n\t\t_EOS_METHOD_CALLBACK_EXPANDED({arg_type}, data, "{signal_name}"'
            else:
                ret = f'\n\t\t_EOS_NOTIFY_CALLBACK_EXPANDED({arg_type}, data'

        for field in fields:
            field_type: str = fields[field]["type"]
            if __is_api_version_field(field_type, field):
                continue

            if is_deprecated_field(field) or field in count_and_variant_type_fields:
                continue

            if _is_client_data_field(field_type, field):
                # 接口与回调不再含有 ClientData
                continue

            snake_case_field = to_snake_case(field)
            if assume_only_one_local_user and _is_local_user_id(field) and _need_ignore_local_user_id_struct(struct_type=arg_type):
                continue  # 不需要绑定该参数

            if not ret.endswith(",\n\t\t\t"):
                ret += ",\n\t\t\t"
                signal_bind_args += ", "

            if _is_enum_type(field_type):
                if _is_enum_flags_type(field_type):
                    ret += f"_EXPAND_TO_GODOT_VAL_FLAGS({remap_type(field_type)}, data->{field})"
                else:
                    ret += f"_EXPAND_TO_GODOT_VAL({remap_type(field_type)}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO_ENUM({snake_case_field}, {_get_enum_owned_interface(field_type)}, {_convert_enum_type(field_type)})"
            elif _is_pure_handle_type(_decay_eos_type(field_type)):
                ret += f"_EXPAND_TO_GODOT_VAL_PURE_HANDLE(data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({remap_type(field_type)}, {snake_case_field})"
            elif _is_socket_id_type(_decay_eos_type(field_type), field):
                ret += f"String(data->{field}.SocketName)"
                signal_bind_args += f'PropertyInfo(Variant::STRING, "{snake_case_field}")'
            elif _is_requested_channel_ptr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_REQUESTED_CHANNEL({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::INT, "{snake_case_field}")'
            elif field_type.startswith("Union"):
                ret += f"_EXPAND_TO_GODOT_VAL_UNION({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::NIL, "{snake_case_field}")'
            elif _is_internal_struct_arr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_STRUCT_ARR({remap_type(_decay_eos_type(field_type))}, data->{field}, {_find_count_field(field, fields.keys())})"
                signal_bind_args += f'PropertyInfo(Variant::ARRAY, "{snake_case_field}", PROPERTY_HINT_ARRAY_TYPE, "{__convert_to_struct_class(_decay_eos_type(field_type))}")'
            elif _is_internal_struct_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_STRUCT({remap_type(_decay_eos_type(field_type))}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({__convert_to_struct_class(_decay_eos_type(field_type))}, {snake_case_field})"
            elif _is_handle_arr_type(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_HANDLER_ARR({_convert_handle_class_name(_decay_eos_type(field_type))}, data->{field}, {_find_count_field(field, fields.keys())})"
                signal_bind_args += f"_MAKE_PROP_INFO_TYPED_ARR({_convert_handle_class_name(_decay_eos_type(field_type))}, {snake_case_field})"
            elif _is_handle_type(_decay_eos_type(field_type), field):
                ret += f"_EXPAND_TO_GODOT_VAL_HANDLER({_convert_handle_class_name(_decay_eos_type(field_type))}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({_convert_handle_class_name(_decay_eos_type(field_type))}, {snake_case_field})"
            elif _is_arr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_ARR({remap_type(field_type)}, data->{field}, data->{_find_count_field(field, fields.keys())})"
                signal_bind_args += f'PropertyInfo(Variant({remap_type(field_type)}()).get_type(), "{snake_case_field}")'
            else:
                ret += f"_EXPAND_TO_GODOT_VAL({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant({remap_type(field_type)}()).get_type(), "{snake_case_field}")'

            expanded_args_doc[snake_case_field] = fields[field]["doc"]
        ret += ")"

        # if len(signal_bind_args):
        #     signal_bind_args = ", " + signal_bind_args
        r_bind_signal_lines.append(f'\tADD_SIGNAL(MethodInfo("{signal_name}"{signal_bind_args}));')

        additional_doc: list[str] = []
        if len(method) and signal_name.startswith("on_"):
            additional_doc.append(f"Callback of [method {method}].\n")
        _insert_doc_signal(handle, signal_name, infos["doc"], expanded_args_doc, additional_doc)
        return ret


def __get_api_latest_macro(struct_type: str) -> str:
    #
    if (struct_type.upper() + "_API_LATEST") in api_latest_macros:
        return struct_type.upper() + "_API_LATEST"
    #
    if (struct_type.removesuffix("Options").upper() + "_API_LATEST") in api_latest_macros:
        return struct_type.removesuffix("Options").upper() + "_API_LATEST"
    #
    if (struct_type.upper() + "OPTIONS_API_LATEST") in api_latest_macros:
        return struct_type.upper() + "OPTIONS_API_LATEST"
    #
    if (struct_type.upper() + "_OPTIONS_API_LATEST") in api_latest_macros:
        return struct_type.upper() + "_OPTIONS_API_LATEST"
    # 特殊
    if struct_type in ["EOS_UserInfo", "EOS_UserInfo_CopyUserInfoOptions"]:
        return "EOS_USERINFO_COPYUSERINFO_API_LATEST"
    if struct_type == "EOS_SessionSearch_SetMaxResultsOptions":
        return "EOS_SESSIONSEARCH_SETMAXSEARCHRESULTS_API_LATEST"

    print(f"ERROR GET API_LATEST MACRO: {struct_type}")
    exit()


def __get_str_result_max_length_macro(method_name: str) -> str:
    # TODO: 能否不硬编码
    # TODO: 不含 eos common, 需要特殊处理
    map = {
        "EOS_Connect_GetProductUserIdMapping": "EOS_CONNECT_EXTERNAL_ACCOUNT_ID_MAX_LENGTH",
        "EOS_Ecom_CopyLastRedeemedEntitlementByIndex": "EOS_ECOM_ENTITLEMENTID_MAX_LENGTH",
        "EOS_Ecom_Transaction_GetTransactionId": "EOS_ECOM_TRANSACTIONID_MAXIMUM_LENGTH",
        "EOS_Lobby_GetInviteIdByIndex": "EOS_LOBBY_INVITEID_MAX_LENGTH",
        "EOS_Lobby_GetRTCRoomName": "256",  # ?
        "EOS_Lobby_GetConnectString": "EOS_LOBBY_GETCONNECTSTRING_BUFFER_SIZE",
        "EOS_Lobby_ParseConnectString": "EOS_LOBBY_PARSECONNECTSTRING_BUFFER_SIZE",
        "EOS_PlayerDataStorageFileTransferRequest_GetFilename": "EOS_PLAYERDATASTORAGE_FILENAME_MAX_LENGTH_BYTES",
        "EOS_Presence_GetJoinInfo": "EOS_PRESENCEMODIFICATION_JOININFO_MAX_LENGTH",
        "EOS_Platform_GetActiveCountryCode": "EOS_COUNTRYCODE_MAX_LENGTH",
        "EOS_Platform_GetActiveLocaleCode": "EOS_LOCALECODE_MAX_LENGTH",
        "EOS_Platform_GetOverrideCountryCode": "EOS_COUNTRYCODE_MAX_LENGTH",
        "EOS_Platform_GetOverrideLocaleCode": "EOS_LOCALECODE_MAX_LENGTH",
        "EOS_Sessions_GetInviteIdByIndex": "EOS_LOBBY_INVITEID_MAX_LENGTH",
        "EOS_TitleStorageFileTransferRequest_GetFilename": "EOS_TITLESTORAGE_FILENAME_MAX_LENGTH_BYTES",
        # 以下可能需要特殊处理
        "EOS_EpicAccountId_ToString": "EOS_EPICACCOUNTID_MAX_LENGTH",
        "EOS_ProductUserId_ToString": "EOS_PRODUCTUSERID_MAX_LENGTH",
        "EOS_ContinuanceToken_ToString": "256",  # 需要调用一次从 InOut 参数获取需要的大小
    }
    if not method_name in map:
        print("ERR has not MAX_LENGTH macros: ", method_name)
        exit()
    return map[method_name]


def __get_str_arr_element_type(str_arr_type: str) -> str:
    if str_arr_type in ["const char**", "const char* const*"]:
        return "const char *"
    elif str_arr_type.endswith("EOS_EpicAccountId*"):
        return "EOS_EpicAccountId"
    elif str_arr_type.endswith("EOS_ProductUserId*"):
        return "EOS_ProductUserId"
    else:
        return str_arr_type.removesuffix("*").removeprefix("const ")


def __expand_input_struct(
    handle_klass: str,
    snake_method_name: str,
    arg_type: str,
    arg_name: str,
    invalid_arg_return_value: str,
    r_declare_args: list[str],
    r_call_args: list[str],
    r_bind_args: list[str],
    r_prepare_lines: list[str],
    r_after_call_lines: list[str],
    r_bind_def_vals: list[str],
    r_required_arg_doc: dict[str, list[str]],  # 字段 -> 文档
):
    decayed_type = _decay_eos_type(arg_type)

    r_prepare_lines.append(f"\t{decayed_type} {arg_name}{{}};")
    r_call_args.append(f"&{arg_name}")

    fields: dict[str, str] = __get_struct_fields(decayed_type)

    ## 检出不需要成为参数的字段
    count_fields: list[str] = []
    variant_union_type_fields: list[str] = []
    for field in fields.keys():
        if is_deprecated_field(field):
            continue

        field_type = fields[field]["type"]
        # 检出count字段
        if _is_arr_field(field_type, field) or _is_internal_struct_arr_field(field_type, field):
            count_fields.append(_find_count_field(field, fields.keys()))

        # 检出Variant式的联合体类型字段
        if _is_variant_union_type(field_type, field):
            for f in fields.keys():
                if f == field + "Type":
                    variant_union_type_fields.append(f)
    ##
    for field in fields:
        field_type: str = fields[field]["type"]
        decay_field_type: str = _decay_eos_type(field_type)
        snake_field: str = to_snake_case(field)

        if __is_api_version_field(field_type, field):
            # 不需要 ApiVersion 作为参数
            macro = __get_api_latest_macro(decayed_type)
            r_prepare_lines.append(f"\t{arg_name}.ApiVersion = {macro};")
            continue
        elif is_deprecated_field(field) or field in count_fields or field in variant_union_type_fields:
            # 需要跳过的字段
            continue

        options_field = f"{arg_name}.{field}"
        if assume_only_one_local_user and _is_local_user_id(field) and _need_ignore_local_user_id_struct(decayed_type):
            interface_class = _get_login_interface_of_local_user_id(field, field_type)
            if _need_check_null_local_user_id_struct(field_type):
                r_prepare_lines.append(
                    f'\tif({_get_gd_type_of_local_user_id(field, field_type)}::_get_local_native() == nullptr) {{ ERR_PRINT("Call \\"{handle_klass}.{snake_method_name}()\\" failed: has not local user, please login by using \\"{interface_class}.login()\\" first."); }}'
                )
            r_prepare_lines.append(f"\t{options_field} = {_get_gd_type_of_local_user_id(field, field_type)}::_get_local_native();")
            continue  # 不需要绑定该参数

        r_bind_args.append(f'"{snake_field}"')

        if _is_pure_handle_type(decay_field_type):
            r_declare_args.append(f"{remap_type(decay_field_type, field)} p_{snake_field}")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_PURE_HANDLE({options_field}, p_{snake_field});")
        elif _is_audio_frames_type(arg_type, arg_name):
            r_declare_args.append(f"const PackedInt32Array &p_{snake_field}")
            r_prepare_lines.append(f"\tLocalVector<int32_t> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_packed_int32_to_audio_frames(p_{snake_field}, _shadow_{snake_field});")
            r_prepare_lines.append(f"\t{arg_name}.{_find_count_field(field, fields.keys())} = _shadow_{snake_field}.size();")
            r_prepare_lines.append(f"\t{options_field} = _shadow_{snake_field}.ptr();")
        elif _is_socket_id_type(decay_field_type, field):
            r_declare_args.append(f"const String &p_{snake_field}")
            r_prepare_lines.append(f"\tCharString ascii_{snake_field} = p_{snake_field}.ascii();")
            r_prepare_lines.append(
                f"\tif (ascii_{snake_field}.size() > (EOS_P2P_SOCKETID_SOCKETNAME_SIZE - 1) && ascii_{snake_field}.get(EOS_P2P_SOCKETID_SOCKETNAME_SIZE - 1) != 0) {{"
            )
            r_prepare_lines.append(
                f'\t\tERR_PRINT(vformat("EOS: Socket name \\"%s\\"\'s length is greater than %d (in ASCII), will be truncated.", p_{snake_field}, EOS_P2P_SOCKETID_SOCKETNAME_SIZE - 1));'
            )
            r_prepare_lines.append(f"\t\tascii_{snake_field}.resize(EOS_P2P_SOCKETID_SOCKETNAME_SIZE);")
            r_prepare_lines.append(f"\t\tascii_{snake_field}.set(EOS_P2P_SOCKETID_SOCKETNAME_SIZE - 1, 0);")
            r_prepare_lines.append(f"\t}}")
            r_prepare_lines.append(f"\tEOS_P2P_SocketId {field};")
            r_prepare_lines.append(f"\t{field}.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;")
            r_prepare_lines.append(f"\tmemcpy(&{field}.SocketName[0], ascii_{snake_field}.get_data(), MIN(ascii_{snake_field}.size(), EOS_P2P_SOCKETID_SOCKETNAME_SIZE));")
            r_prepare_lines.append(f"\t{options_field} = &{field};")
        elif _is_str_type(field_type, field):
            r_declare_args.append(f"const String &p_{snake_field}")
            r_prepare_lines.append(f"\tCharString utf8_{snake_field} = p_{snake_field}.utf8();")
            r_prepare_lines.append(f"\t{options_field} = to_eos_type<const CharString &, decltype({options_field})>(utf8_{snake_field});")
        elif _is_str_arr_type(field_type, field):
            r_declare_args.append(f"const PackedStringArray &p_{snake_field}")
            option_count_field = f"{arg_name}.{_find_count_field(field, fields.keys())}"
            element_type: str = __get_str_arr_element_type(field_type)
            r_prepare_lines.append(f"\tLocalVector<{element_type}> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_TO_EOS_STR_ARR_FROM_PACKED_STRING_ARR({options_field}, p_{snake_field}, _shadow_{snake_field}, {option_count_field});")
        elif _is_nullable_float_pointer_field(field_type, field):
            r_declare_args.append(f"{decay_field_type} p_{snake_field} = -1.0")
            r_prepare_lines.append(f"\t{options_field} = p_{snake_field} < 0.0? nullptr: &p_{snake_field};")
        elif _is_requested_channel_ptr_field(field_type, field):
            r_declare_args.append(f"{remap_type(field_type, field)} p_{snake_field} = -1")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_REQUESTED_CHANNEL({options_field}, p_{snake_field});")
            r_bind_def_vals.append("DEFVAL(-1)")
        elif field_type.startswith("Union"):
            r_declare_args.append(f"const {remap_type(_decay_eos_type(field_type), field)} &p_{snake_field}")
            if _is_variant_union_type(field_type, field):
                r_prepare_lines.append(f"\t_TO_EOS_FIELD_VARIANT_UNION({options_field}, p_{snake_field});")
            else:
                r_prepare_lines.append(f"\t_TO_EOS_FIELD_METRICS_ACCOUNT_ID_UNION({options_field}, p_{snake_field});")
        elif _is_handle_arr_type(field_type, field):
            r_declare_args.append(f"const TypedArray<{_convert_handle_class_name(decay_field_type)}> &p_{snake_field}")
            option_count_field = f"{arg_name}.{_find_count_field(field, fields.keys())}"
            r_prepare_lines.append(f"\tLocalVector<{decay_field_type}> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_HANDLER_ARR({options_field}, p_{snake_field}, _shadow_{snake_field}, {option_count_field});")
        elif _is_handle_type(decay_field_type, field):
            r_declare_args.append(f"const class {remap_type(_decay_eos_type(field_type), field)} &p_{snake_field}")
            if len(invalid_arg_return_value):
                r_prepare_lines.append(f"\tERR_FAIL_NULL_V(p_{snake_field}, {invalid_arg_return_value});")
            else:
                r_prepare_lines.append(f"\tERR_FAIL_NULL(p_{snake_field});")
            gd_type = _convert_handle_class_name(decay_field_type)
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_HANDLER({options_field}, p_{snake_field}, {gd_type});")
        elif _is_client_data_field(field_type, field):
            # 输入结构体不含有 ClientData 字段
            print("ERR:", arg_type)
            _print_stack_and_exit()
        elif _is_internal_struct_arr_field(field_type, field):
            r_declare_args.append(f"const TypedArray<{__convert_to_struct_class(_decay_eos_type(field_type))}> &p_{snake_field}")
            option_count_field = f"{arg_name}.{_find_count_field(field, fields.keys())}"
            r_prepare_lines.append(f"\tLocalVector<{_decay_eos_type(field_type)}> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_STRUCT_ARR({options_field}, p_{snake_field}, _shadow_{snake_field}, {option_count_field});")
        elif _is_internal_struct_field(field_type, field):
            r_declare_args.append(f"const {remap_type(_decay_eos_type(field_type), field, True)} &p_{snake_field}")
            if len(invalid_arg_return_value):
                r_prepare_lines.append(f"\tERR_FAIL_NULL_V(p_{snake_field}, {invalid_arg_return_value});")
            else:
                r_prepare_lines.append(f"\tERR_FAIL_NULL(p_{snake_field});")

            r_prepare_lines.append(f"\t_TO_EOS_FIELD_STRUCT({options_field}, p_{snake_field});")

        elif _is_arr_field(field_type, field):
            r_declare_args.append(f"const {remap_type(field_type, field)} &p_{snake_field}")
            option_count_field = f"{arg_name}.{_find_count_field(field, fields.keys())}"
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_ARR({options_field}, p_{snake_field}, {option_count_field});")
        elif _is_struct_ptr(field_type):
            r_declare_args.append(f"gd_arg_t<{remap_type(field_type, field)}> p_{snake_field}")
            r_prepare_lines.append(f"\t{field_type} shadow_{snake_field} = to_eos_type<decltype(p_{snake_field}), {_decay_eos_type(field_type)}>(p_{snake_field});")
            r_prepare_lines.append(f"\t{options_field} = &shadow_{snake_field};")
        elif _is_enum_flags_type(field_type):
            r_declare_args.append(f"BitField<{remap_type(field_type, field)}> p_{snake_field}")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_FLAGS({options_field.split('[')[0]}, p_{snake_field});")
        else:
            r_declare_args.append(f"gd_arg_t<{remap_type(field_type, field)}> p_{snake_field}")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD({options_field.split('[')[0]}, p_{snake_field});")

        r_required_arg_doc[field] = fields[field]["doc"]


def __make_packed_result(
    packed_result_type: str,
    method_name: str,
    has_result_code: bool,
    options_identifier: str,
    options_type: str,
    begin_idx: int,
    args: list[dict[str, str]],
    r_call_args: list[str],
    r_prepare_lines: list[str],
    r_after_call_lines: list[str],
    r_return_type_if_convert_to_return: list[str],
):
    pack_result: bool = len(packed_result_type) > 0

    if pack_result:
        r_after_call_lines.append(f"\tRef<{packed_result_type}> ret; ret.instantiate();")
        if has_result_code:
            r_after_call_lines.append(f"\tret->result_code = result_code;")
            r_after_call_lines.append(f"\tif (result_code == EOS_EResult::EOS_Success) {{")
        else:
            print("Error UNSUPPORTED:", method_name)
            _print_stack_and_exit()
    acl_indents = "\t\t" if has_result_code else "\t"
    i = begin_idx
    while i < len(args):
        arg_name: str = args[i]["name"]
        arg_type: str = args[i]["type"]
        decayed_type: str = _decay_eos_type(arg_type)
        snake_name: str = to_snake_case(arg_name.removeprefix("InOut").removeprefix("Out").removeprefix("bOut"))

        if _is_handle_arr_type(arg_type, arg_name):
            print("ERROR UNSUPPORTED handle arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_handle_type(decayed_type):
            r_prepare_lines.append(f"\t{decayed_type} {arg_name}{{ nullptr }};")
            r_call_args.append(f"&{arg_name}")
            if pack_result:
                r_after_call_lines.append(f"{acl_indents}ret->{snake_name}.reference_ptr(memnew({_convert_handle_class_name(decayed_type)}));")
                r_after_call_lines.append(f"{acl_indents}ret->get_{snake_name}()->set_handle({arg_name});")
            else:
                r_return_type_if_convert_to_return.append(f"Ret<{_convert_handle_class_name(decayed_type)}>")
                r_after_call_lines.append(f"{acl_indents}Ret<{_convert_handle_class_name(decayed_type)}> ret; ret.instantiate(); ret->set_handle({arg_name});")
        elif __is_struct_type(decayed_type):
            if arg_type.endswith("**"):
                r_prepare_lines.append(f"\t{decayed_type} *{arg_name}{{ nullptr }};")
                r_call_args.append(f"&{arg_name}")
                if pack_result:
                    r_after_call_lines.append(f"{acl_indents}ret->{snake_name}.instantiate(); ret->{snake_name}->set_from_eos(*{arg_name});")
                    r_after_call_lines.append(f"{acl_indents}{decayed_type}_Release({arg_name});")
                else:
                    return_type = remap_type(decayed_type, arg_name)
                    r_return_type_if_convert_to_return.append(f"Ret<{return_type}>")
                    r_after_call_lines.append(f"{acl_indents}Ret<{return_type}> ret; ret.instantiate(); ret->set_from_eos(*{arg_name});")
                    r_after_call_lines.append(f"{acl_indents}{decayed_type}_Release({arg_name});")
            else:
                r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
                r_call_args.append(f"&{arg_name}")
                if pack_result:
                    r_after_call_lines.append(f"{acl_indents}ret->{snake_name}.instantiate(); ret->{snake_name}->set_from_eos({arg_name});")
                else:
                    r_return_type_if_convert_to_return.append(f"Ret<{__convert_to_struct_class(decayed_type)}>")
                    r_after_call_lines.append(f"{acl_indents}Ret<{__convert_to_struct_class(decayed_type)}> ret; ret.instantiate(); ret->set_from_eos({arg_name});")
        elif _is_socket_id_type(decayed_type, arg_name):
            r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
            r_call_args.append(f"&{arg_name}")
            if pack_result:
                r_after_call_lines.append(f"{acl_indents}ret->{snake_name} = String(&{arg_name}.SocketName[0]);")
            else:
                r_return_type_if_convert_to_return.append(f"String")
                r_after_call_lines.append(f"{acl_indents}String ret{{ &{arg_name}.SocketName[0] }};")
        elif _is_enum_type(decayed_type):
            r_prepare_lines.append(f"\t{_convert_enum_type(decayed_type)} {arg_name};")
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                r_after_call_lines.append(f"{acl_indents}ret->{snake_name} = {arg_name};")
            else:
                r_return_type_if_convert_to_return.append(f"{remap_type(decayed_type, arg_name)}")
                r_after_call_lines.append(f"{acl_indents}{remap_type(decayed_type, arg_name)} ret = {arg_name};")
        elif arg_type == "char*" and (i + 1) < len(args) and args[i + 1]["type"].endswith("int32_t*") and args[i + 1]["name"].endswith("Length"):
            r_prepare_lines.append(f"\tchar {arg_name} [{__get_str_result_max_length_macro(method_name)} + 1] {{}};")
            initialize_value = "0"
            if args[i + 1]["name"].startswith("InOut"):
                initialize_value = f"{__get_str_result_max_length_macro(method_name)} + 1"

            r_prepare_lines.append(f'\t{_decay_eos_type(args[i+1]["type"])} {args[i+1]["name"]}{{ {initialize_value} }};')

            r_call_args.append(f"&{arg_name}[0]")
            r_call_args.append(f'&{args[i+1]["name"]}')

            if pack_result:
                r_after_call_lines.append(f"{acl_indents}ret->{snake_name} = &{arg_name}[0];")
            else:
                r_return_type_if_convert_to_return.append(f"String")
                r_after_call_lines.append(f"{acl_indents}String ret = &{arg_name}[0];")
            i += 1
        elif arg_type == "void*" and (i + 1) <= len(args) and args[i + 1]["type"].endswith("int32_t*"):
            # 查找大小字段
            length_variable: str = ""
            options_fields: dict[str, str] = __get_struct_fields(options_type)
            for field in options_fields:
                if field == arg_name + "SizeBytes":
                    length_variable = f"{options_identifier}.{field}"
                    break
                elif field in ["MaxDataSizeBytes"]:  # 特殊处理
                    length_variable = f"{options_identifier}.{field}"
                    break
            if len(length_variable) <= 0:
                print(f"ERR can't find length_variable: {arg_name}")
                _print_stack_and_exit()
            #

            r_prepare_lines.append(f"\tPackedByteArray {arg_name};")
            r_prepare_lines.append(f"\t{arg_name}.resize({length_variable});")
            r_prepare_lines.append(f'\t{_decay_eos_type(args[i+1]["type"])} {args[i+1]["name"]} = {length_variable};')

            r_call_args.append(f"{arg_name}.ptrw()")
            r_call_args.append(f'&{args[i+1]["name"]}')

            r_after_call_lines.append(f'{acl_indents}{arg_name}.resize({args[i+1]["name"]});')

            if pack_result:
                r_after_call_lines.append(f"{acl_indents}ret->{snake_name} = {arg_name};")
            else:
                r_return_type_if_convert_to_return.append(f"PackedByteArray")
                r_after_call_lines.append(f"{acl_indents}PackedByteArray ret = {arg_name};")

            i += 1
        elif decayed_type == "EOS_Bool":
            r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                r_after_call_lines.append(f"{acl_indents}ret->{snake_name} = {arg_name};")
            else:
                r_return_type_if_convert_to_return.append(f"{remap_type(decayed_type, arg_name)}")
                r_after_call_lines.append(f"{acl_indents}{remap_type(decayed_type, arg_name)} ret = {arg_name};")

            i += 1
        elif _is_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORTED arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_internal_struct_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORTED struct arr:", method_name, arg_type)
            _print_stack_and_exit()
        elif _is_struct_ptr(arg_type):
            print("ERROR UNSUPPORTED struct ptr:", method_name, arg_type)
            _print_stack_and_exit()
        else:
            if not arg_type.endswith("*"):
                print("ERROR UNSUPPORTED out: ", arg_type, arg_name)
                _print_stack_and_exit()

            r_prepare_lines.append(f'\t{arg_type.removesuffix("*")} {arg_name};')
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                r_after_call_lines.append(f"{acl_indents}_FROM_EOS_FIELD(ret->{snake_name}, {arg_name.split('[')[0]});")
            else:
                r_return_type_if_convert_to_return.append(f"{remap_type(decayed_type, arg_name)}")
                r_after_call_lines.append(f"{acl_indents}{remap_type(decayed_type, arg_name)} ret; _FROM_EOS_FIELD(ret, {arg_name.split('[')[0]});")

        i += 1

    if has_result_code:
        r_after_call_lines.append(f"\t}}")


def __find_method_handle_type(method_name: str) -> str:
    for h in handles:
        for m in handles[h]["methods"]:
            if m == method_name:
                return h
    print(f"ERROR: {method_name} has not owned handle type.")
    exit()


def __convert_method_name(method_name: str, handle_type: str = "") -> str:
    if method_name == "EOS_Logging_SetCallback":
        return "set_logging_callback"
    elif method_name == "EOS_Platform_Create":
        return "platform_create"
    else:
        if len(handle_type) <= 0:
            for h in handles:
                for m in handles[h]["methods"]:
                    if m == method_name:
                        handle_type = h
                        break
                if len(handle_type):
                    break
        if len(handle_type) == 0:
            print("ERROR")
            exit()

        # 避免同类内方法重名
        candidate_method_name = method_name.rsplit("_", 1)[1]
        valid = False
        while not valid:
            valid = True
            for m in handles[handle_type]["methods"]:
                if method_name == m:
                    continue
                if m.endswith(candidate_method_name):
                    splits = method_name.rsplit("_", 2)
                    candidate_method_name = "".join([splits[1], splits[2]])
                    valid = False
                    break
        return to_snake_case(candidate_method_name).removeprefix("e_")  # Hack, 去除枚举前缀


def _gen_method(
    handle_type: str,
    method_name: str,
    info: dict[str],
    r_declare_lines: list[str],
    r_define_lines: list[str],
    r_bind_lines: list[str],
):
    handle_klass = _convert_handle_class_name(handle_type)

    return_type: str = ""
    callback_signal = ""

    out_to_ret: list[bool] = []
    _remapped_return_type_list: list[str] = []
    packed_result_type: str = _gen_packed_result_type(method_name, info, [], [], [], out_to_ret, True, _remapped_return_type_list)
    remapped_return_type: str = _remapped_return_type_list[0] if len(_remapped_return_type_list) > 0 else ""
    need_out_to_ret: bool = False if len(out_to_ret) <= 0 else out_to_ret[0]

    # 是否回调
    for a in info["args"]:
        if __is_callback_type(_decay_eos_type(a["type"])):
            if len(info["return"]) <= 0 or info["return"] == "void":
                return_type = "Signal"
                callback_signal = __convert_to_signal_name(_decay_eos_type(a["type"]), method_name)
            break

    if (return_type == "Signal") and (len(packed_result_type) or len(remapped_return_type)):
        print("ERROR 回调与打包返回冲突:", method_name)
        _print_stack_and_exit()

    if len(packed_result_type):
        return_type = f"Ref<{packed_result_type}>"

    if len(remapped_return_type):
        return_type = remapped_return_type
    elif _is_handle_type(_decay_eos_type(info["return"])):
        return_type = f'Ref<class {_convert_handle_class_name(_decay_eos_type(info["return"]))}>'
    elif return_type == "" and info["return"] != "void":
        return_type = remap_type(info["return"], "")
    elif return_type == "":
        return_type = "void"

    if "AddNotify" in method_name:
        # 添加通知,返回通知对象
        return_type = "Ref<EOSNotification>"

    invalid_arg_return_val: str = ""
    if return_type != "void":
        if return_type == "EOS_EResult":
            invalid_arg_return_val = "EOS_EResult::EOS_InvalidParameters"
        else:
            invalid_arg_return_val = "{}"

    if method_name == "EOS_Platform_Create":
        # 特殊处理
        return_type = "EOS_EResult"
        invalid_arg_return_val = "EOS_EResult::EOS_InvalidParameters"

    if _is_enum_flags_type(return_type):
        return_type = f"BitField<{return_type}>"
        invalid_arg_return_val = f"{return_type}({{}})"

    snake_method_name = __convert_method_name(method_name, handle_type)

    declare_args: list[str] = []
    call_args: list[str] = []
    bind_args: list[str] = []

    prepare_lines: list[str] = []
    after_call_lines: list[str] = []

    options_type: str = ""  # 用于获取里边的buffer size 字段
    options_input_identifier: str = ""
    options_prepare_identifier: str = ""

    for_file_transfer: bool = False

    static: bool = True
    i: int = 0

    bind_def_vals: list[str] = []

    expanded_args_doc: dict[str, list[str]] = {}  # 字段 -> doc
    additional_doc: list[str] = []
    while i < len(info["args"]):
        type: str = info["args"][i]["type"]
        name: str = info["args"][i]["name"]
        decayed_type: str = _decay_eos_type(type)
        snake_name: str = to_snake_case(name)

        if decayed_type == handle_type:
            # 句柄参数
            call_args.append("m_handle")
            if len(invalid_arg_return_val):
                prepare_lines.append(f"\tERR_FAIL_NULL_V(m_handle, {invalid_arg_return_val});")
            else:
                prepare_lines.append(f"\tERR_FAIL_NULL(m_handle);")
            static = False
        elif __is_callback_type(decayed_type):
            if method_name == "EOS_Logging_SetCallback":
                declare_args.append(f"const Callable &p_{snake_name}")
                bind_args.append(f'"{snake_name}"')
                prepare_lines.append(f"\tEOS::get_log_message_callback() = p_{snake_name};")
            else:
                # 回调参数
                declare_args.append(f"const Callable &p_{snake_name} = {{}}")
                bind_args.append(f'"{snake_name}"')

                if decayed_type in [
                    "EOS_PlayerDataStorage_OnWriteFileCompleteCallback",
                    "EOS_PlayerDataStorage_OnReadFileCompleteCallback",
                    "EOS_TitleStorage_OnReadFileCompleteCallback",
                ]:
                    cb = _decay_eos_type(_get_callback_infos(decayed_type)["args"][0]["type"])
                    gd_cb = remap_type(cb, name).removeprefix("Ref<").removesuffix(">")
                    signal_name = __convert_to_signal_name(decayed_type, "")
                    interface_signal_name = __convert_to_signal_name(decayed_type, "")
                    prepare_lines.append(f'\tstatic constexpr char {signal_name}[] = "{signal_name}";')
                    if signal_name != interface_signal_name:
                        prepare_lines.append(f'\tstatic constexpr char {interface_signal_name}[] = "{interface_signal_name}";')
                    prepare_lines.append(
                        f"\tconstexpr {decayed_type} callback = &godot::eos::internal::file_transfer_completion_callback<{cb}, {gd_cb}, {signal_name}, {interface_signal_name}>;"
                    )
                    call_args.append(f"callback")
                else:
                    call_args.append(f'{_gen_callback(decayed_type, [], False, return_type == "Ref<EOSNotification>")}')

                bind_def_vals.append("DEFVAL(Callable())")
            # 插入回调的文档
            expanded_args_doc[name] = __make_callback_doc(decayed_type)
        elif __is_client_data(type, name):
            # Client Data, 必定配合回调使用
            if return_type == "Ref<EOSNotification>":
                next_arg_name = _decay_eos_type(info["args"][i + 1]["name"])
                prepare_lines.append("\tRef<EOSNotification> ret; ret.instantiate();")
                call_args.append("ret.ptr()")
                after_call_lines.append(f'\tif (notification_id == EOS_INVALID_NOTIFICATIONID) return {{}};')
                after_call_lines.append(f'\tauto NotifyRemover = memnew(EOSNotifyRemover(m_handle, &{method_name.replace("AddNotify", "RemoveNotify")}));')
                after_call_lines.append(f'\tret->_setup(notification_id, NotifyRemover, p_{to_snake_case(next_arg_name)});')

                additional_doc.append(f"[b]NOTE[/b]: The return value can be null, it means that add notify failed.\n")
            else:
                next_decayed_type = _decay_eos_type(info["args"][i + 1]["type"])
                if (i + 1) < len(info["args"]) and __is_callback_type(next_decayed_type):
                    if next_decayed_type == "EOS_PlayerDataStorage_OnWriteFileCompleteCallback":
                        write_cb = f'{options_input_identifier}->get_{to_snake_case("WriteFileDataCallback")}()'
                        progress_cb = f'{options_input_identifier}->get_{to_snake_case("FileTransferProgressCallback")}()'
                        completion_cb = f'p_{to_snake_case(info["args"][i+1]["name"])}'

                        prepare_lines.append(f"\t{return_type} ret; ret.instantiate();")
                        prepare_lines.append(f"\tauto transfer_data = MAKE_FILE_TRANSFER_DATA(ret, {write_cb}, {progress_cb}, {completion_cb});")
                        call_args.append(f"transfer_data")
                        for_file_transfer = True
                    elif next_decayed_type in ["EOS_PlayerDataStorage_OnReadFileCompleteCallback", "EOS_TitleStorage_OnReadFileCompleteCallback"]:
                        read_cb = f'{options_input_identifier}->get_{to_snake_case("ReadFileDataCallback")}()'
                        progress_cb = f'{options_input_identifier}->get_{to_snake_case("FileTransferProgressCallback")}()'
                        completion_cb = f'p_{to_snake_case(info["args"][i+1]["name"])}'

                        prepare_lines.append(f"\t{return_type} ret; ret.instantiate();")
                        prepare_lines.append(f"\tauto transfer_data = MAKE_FILE_TRANSFER_DATA(ret, {read_cb}, {progress_cb}, {completion_cb});")
                        call_args.append(f"transfer_data")
                        for_file_transfer = True
                    elif next_decayed_type == "EOS_IntegratedPlatform_OnUserPreLogoutCallback":
                        prepare_lines.append("\tstatic auto ClientData = _CallbackClientData(this, {});")
                        prepare_lines.append("\tClientData.handle_wrapper = this;")
                        prepare_lines.append(f'\tClientData.callback = p_{to_snake_case(info["args"][i+1]["name"])};')
                        call_args.append("&ClientData")
                    else:
                        call_args.append(f'_CallbackClientData::create(this, p_{to_snake_case(info["args"][i+1]["name"])})')
                else:
                    call_args.append(f"_CallbackClientData::create(this)")
        elif assume_only_one_local_user and _is_local_user_id(name):
            interface_class = _get_login_interface_of_local_user_id(name, type)
            prepare_lines.append(
                f'\tif({_get_gd_type_of_local_user_id(name, type)}::_get_local_native() == nullptr) {{ ERR_PRINT("Call \\"{handle_klass}.{snake_method_name}()\\" failed: has not local user, please login by using \\"{interface_class}.login()\\" first."); }}'
            )
            prepare_lines.append(f"\t{type} {name} = {_get_gd_type_of_local_user_id(name, type)}::_get_local_native();")
            call_args.append(name)
        elif __is_method_input_only_struct(decayed_type) and not _is_expanded_struct(decayed_type):
            if name.endswith("Options"):
                options_type = decayed_type
                options_input_identifier = f"p_{snake_name}"
                options_prepare_identifier = f"{name}"
            # 未被展开的输入结构体（Options）
            if len(invalid_arg_return_val):
                prepare_lines.append(f"\tERR_FAIL_NULL_V(p_{snake_name}, {invalid_arg_return_val});")
            else:
                prepare_lines.append(f"\tERR_FAIL_NULL(p_{snake_name});")
            declare_args.append(f"const {remap_type(decayed_type, name)}& p_{snake_name}")

            prepare_lines.append(f"\tauto &{options_prepare_identifier} = p_{snake_name}->to_eos();")

            bind_args.append(f'"{snake_name}"')
            call_args.append(f"&{options_prepare_identifier}")
        elif __is_method_input_only_struct(decayed_type) and _is_expanded_struct(decayed_type):
            if name.endswith("Options"):
                options_type = decayed_type
                options_input_identifier = f"p_{snake_name} "
                options_prepare_identifier = f"{name}"
            # 被展开的输入结构体（Options）
            __expand_input_struct(
                handle_klass,
                snake_method_name,
                type,
                name,
                invalid_arg_return_val,
                declare_args,
                call_args,
                bind_args,
                prepare_lines,
                after_call_lines,
                bind_def_vals,
                expanded_args_doc,
            )
        elif name.startswith("Out") or name.startswith("InOut") or name.startswith("bOut"):
            if len(remapped_return_type) == 0:
                # Out 参数
                converted_return_type: list[str] = []
                __make_packed_result(
                    packed_result_type,
                    method_name,
                    info["return"] == "EOS_EResult",
                    options_prepare_identifier,
                    options_type,
                    i,
                    info["args"],
                    call_args,
                    prepare_lines,
                    after_call_lines,
                    converted_return_type,
                )
                if len(converted_return_type):
                    if len(converted_return_type) != 1:
                        print("Error len(converted_return_type) != 1:", method_name)
                        _print_stack_and_exit()
                    if return_type != "void":
                        print("ERROR : ?")
                        _print_stack_and_exit()
                    return_type = converted_return_type[1]
            else:
                # 返回 EOS_EResult 且返回参数为单个对象类型时
                _assert(info["return"] == "EOS_EResult")

                after_call_lines.append(f"\t{remapped_return_type} ret;")
                after_call_lines.append(f"\tif (result_code == EOS_EResult::EOS_Success) {{")
                after_call_lines.append(f"\t\tret.instantiate();")
                if _is_handle_type(decayed_type):
                    prepare_lines.append(f"\t{decayed_type} {name}{{ nullptr }};")
                    call_args.append(f"&{name}")
                    after_call_lines.append(f"\t\tret->set_handle({name});")
                elif __is_struct_type(decayed_type):
                    call_args.append(f"&{name}")
                    if type.endswith("**"):
                        prepare_lines.append(f"\t{decayed_type} *{name}{{}};")
                        after_call_lines.append(f"\t\tret->set_from_eos(*{name});")
                        after_call_lines.append(f"\t\t{decayed_type}_Release({name});")
                    else:
                        prepare_lines.append(f"\t{decayed_type} {name}{{}};")
                        after_call_lines.append(f"\t\tret->set_from_eos({name});")
                after_call_lines.append(f"\t}}")

            # Out 参数在最后，直接跳出
            break
        elif _is_str_type(type, name):
            # 字符串参数
            declare_args.append(f"const String &p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            prepare_lines.append(f"\tCharString utf8_{snake_name} = p_{snake_name}.utf8();")
            call_args.append(f"to_eos_type<const CharString &, {type}>(utf8_{snake_name})")
        elif _is_str_arr_type(type, name):
            # 字符串数组参数
            print("ERROR")
            _print_stack_and_exit()
        elif _is_enum_flags_type(type):
            # 普通参数
            declare_args.append(f"BitField<{type}> p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"to_eos_type<{type}>(p_{snake_name})")
        elif _is_handle_arr_type(type, name):
            print("ERROR: Unsupported handle arr argument:", method_name, type, name)
            _print_stack_and_exit()
        elif _is_handle_type(decayed_type):
            declare_args.append(f"const {remap_type(decayed_type, name)} &p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"p_{snake_name}.is_valid()? p_{snake_name}->get_handle() : nullptr")
        elif name.endswith("StringBufferSizeBytes"):
            # xxxGetFilename 的字符串 buffer 长度不是使用 InOut 来传入缓冲区大小并传出缓冲区被使用的大小，
            # 而是使用 Out 进行传出 + xxxStringBufferSizeBytes 来传入缓冲区大小
            prepare_lines.append(f"\t{type} {name} = {__get_str_result_max_length_macro(method_name)} + 1;")
            call_args.append(name)
        else:
            # 普通参数
            declare_args.append(f"gd_arg_t<{remap_type(type, name)}> p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"to_eos_type<gd_arg_t<{remap_type(type, name)}>, {type}>(p_{snake_name})")
        i += 1

    # ======= 声明 ===============
    r_declare_lines.append(f'\t{"static " if static else ""}{return_type} {snake_method_name}({", ".join(declare_args)});')
    # ======= 定义 ===============
    for i in range(len(declare_args)):
        # 移除默认值
        declare_args[i] = declare_args[i].rsplit(" =", 1)[0]
        # 移除前向声明
        declare_args[i] = declare_args[i].replace(" class ", " ")
    r_define_lines.append(f'{return_type.replace("class ", "")} {handle_klass}::{snake_method_name}({", ".join(declare_args)}) {{')
    r_define_lines += prepare_lines
    # 调用
    if method_name == "EOS_Platform_Create":
        # 特殊处理
        r_define_lines.append(f'\tauto platform_handle = {method_name}({", ".join(call_args)});')
        r_define_lines.append(f"\tERR_FAIL_COND_V(platform_handle == nullptr, EOS_EResult::EOS_UnexpectedError);")
        r_define_lines.append(f'\t{_convert_handle_class_name("EOS_HPlatform")}::get_singleton()->set_handle(platform_handle);')
        for m in handles["EOS_HPlatform"]["methods"]:
            if not m.endswith("Interface"):
                continue
            interface: str = "EOS_H" + m.rsplit("_", 1)[1].removeprefix("Get").removesuffix("Interface")
            disable_macro = _gen_disabled_macro(interface)
            handle_identifier = interface.removeprefix("EOS_H").lower() + "_handle"
            r_define_lines.append(f"#ifndef {disable_macro}")
            #
            if handle_identifier.startswith("rtc"):
                # 需要设置RTC选项才能使用RTC相关功能
                r_define_lines.append(f"\tif ({options_prepare_identifier}.RTCOptions != nullptr) {{")
                r_define_lines.append(f"\t\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\t\tERR_FAIL_COND_V({handle_identifier} == nullptr, EOS_EResult::EOS_UnexpectedError);")
                r_define_lines.append(f"\t\t{_convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier});")
                r_define_lines.append(f"\t}}")
            elif handle_identifier.startswith("anticheatclient"):
                # 反作弊客户端需要从 bootstrapper 启动，非必须功能，允许为空
                r_define_lines.append(f"\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\tif ({handle_identifier}) {{ {_convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier}); }};")
            elif handle_identifier.startswith("anticheatserver"):
                # 如果不是以客户端进行启动则不对反作弊服务器进行初始化。
                r_define_lines.append(f"\tif ({options_prepare_identifier}.bIsServer) {{")
                r_define_lines.append(f"\t\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\t\tERR_FAIL_COND_V({handle_identifier} == nullptr, EOS_EResult::EOS_UnexpectedError);")
                r_define_lines.append(f"\t\t{_convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier});")
                r_define_lines.append(f"\t}}")
            elif handle_identifier.startswith("playerdatastorage") or handle_identifier.startswith("titlestorage"):
                # PlayerDataStorage 与 TitleStorage 需要文件加密密钥
                r_define_lines.append(f"\tif ({options_prepare_identifier}.EncryptionKey) {{")
                r_define_lines.append(f"\t\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\t\tERR_FAIL_COND_V({handle_identifier} == nullptr, EOS_EResult::EOS_UnexpectedError);")
                r_define_lines.append(f"\t\t{_convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier});")
                r_define_lines.append(f"\t}} else {{")
                r_define_lines.append(f'\t\tWARN_PRINT("Create Platform without encryption_key, The singleton \\"{_convert_handle_class_name(interface)}\\" is invalid.");')
                r_define_lines.append(f"\t}}")
            else:
                r_define_lines.append(f"\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\tif ({handle_identifier}) {{ {_convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier}); }}")
                r_define_lines.append(
                    f'\telse {{ WARN_PRINT("Can\'t get \\"{_convert_handle_class_name(interface).removeprefix("EOS")}\\" interface, \\"{_convert_handle_class_name(interface)}\\" singleton is invalid, maybe due to platform\'s limitation."); }}'
                )
            r_define_lines.append(f"#endif // {disable_macro}")
    elif method_name == "EOS_Logging_SetCallback":
        r_define_lines.append(f"\tEOS_EResult result_code = {method_name}(_EOS_LOGGING_CALLBACK());")
        r_define_lines.append(f"\tEOS::_set_last_result_code(result_code);")
    elif _is_handle_type(_decay_eos_type(info["return"])):
        r_define_lines.append(f'\tauto return_handle = {method_name}({", ".join(call_args)});')
    elif info["return"] == "EOS_EResult":
        r_define_lines.append(f'\tEOS_EResult result_code = {method_name}({", ".join(call_args)});')
        r_define_lines.append(f"\tEOS::_set_last_result_code(result_code);")
    elif return_type == "void" or return_type == "Signal" or need_out_to_ret:
        r_define_lines.append(f'\t{method_name}({", ".join(call_args)});')
    elif return_type == "Ref<EOSNotification>":
        r_define_lines.append(f'\tauto notification_id = {method_name}({", ".join(call_args)});')
    else:
        r_define_lines.append(f'\tauto ret = {method_name}({", ".join(call_args)});')
    # 后处理
    r_define_lines += after_call_lines
    # 返回
    if method_name == "EOS_Platform_Create":
        r_define_lines.append(f"\treturn EOS_EResult::EOS_Success;")
    elif _is_handle_type(_decay_eos_type(info["return"])):
        if not for_file_transfer:
            r_define_lines.append(f"\t{return_type} ret;")
            r_define_lines.append(f"\tif(return_handle) {{ ret.instantiate(); ret->set_handle(return_handle);}}")
        else:
            r_define_lines.append(f"\tret->set_handle(return_handle);")
        r_define_lines.append(f"\treturn ret;")
    elif len(packed_result_type):
        if info["return"] == "EOS_EResult":
            r_define_lines.append(f"\tret->result_code = result_code;")
        r_define_lines.append(f"\treturn ret;")
    elif len(remapped_return_type):
        r_define_lines.append(f"\treturn ret;")
        additional_doc.append(f"If the return value is null, please use [method EOS.get_last_result_code] to check the error.\n")
    elif return_type == "EOS_EResult":
        r_define_lines.append(f"\treturn result_code;")
    elif return_type == "Signal":
        r_define_lines.append(f'\treturn Signal(this, SNAME("{callback_signal}"));')
        # 附加返回的文档
        additional_doc.append(f"Return signal [signal {callback_signal}].\n")
    elif return_type.startswith("BitField"):
        r_define_lines.append(f"\treturn _EXPAND_TO_GODOT_VAL_FLAGS({return_type}, ret);")
    elif return_type != "void":
        r_define_lines.append(f"\treturn _EXPAND_TO_GODOT_VAL({return_type}, ret);")

    r_define_lines.append("}")
    # ======= 绑定 ===============
    bind_args_text: str = ", ".join(bind_args)
    if len(bind_args_text):
        bind_args_text = ", " + bind_args_text
    default_val_arg = ""
    if len(bind_def_vals):
        default_val_arg = ", " + ", ".join(bind_def_vals)

    bind_prefix: str = "ClassDB::bind_static_method(get_class_static(), " if static else "ClassDB::bind_method("
    r_bind_lines.append(f'\t{bind_prefix}D_METHOD("{snake_method_name}"{bind_args_text}), &{handle_klass}::{snake_method_name}{default_val_arg});')

    _insert_doc_method(handle_klass, snake_method_name, info["doc"], expanded_args_doc, additional_doc)


def _get_EOS_EResult(r_file_lower2infos: list[str]):
    f = open(os.path.join(sdk_include_dir, "eos_result.h"), "r")
    lines: list[str] = f.readlines()

    r_file_lower2infos[_convert_to_interface_lower("eos_common.h")]["enums"]["EOS_EResult"] = {"doc": "", "members": []}

    for i in range(len(lines)):
        line: str = lines[i]
        if not line.startswith("EOS_RESULT_VALUE"):
            continue
        r_file_lower2infos[_convert_to_interface_lower("eos_common.h")]["enums"]["EOS_EResult"]["members"].append(
            {
                "doc": _extract_doc(lines, i - 1),
                "name": line.split("(", 1)[1].split(", ", 1)[0],
            }
        )

    f.close()


def _get_EOS_UI_EKeyCombination(r_file_lower2infos: list[str]):
    f = open(os.path.join(sdk_include_dir, "eos_ui_keys.h"), "r")
    lines: list[str] = f.readlines()

    r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"]["EOS_UI_EKeyCombination"] = {"doc": "", "members": []}

    for i in range(len(lines)):
        line: str = lines[i]
        if not line.startswith("EOS_UI_KEY_"):
            continue

        splits = line.split("(", 1)[1].rsplit(")")[0].split(", ")
        r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"]["EOS_UI_EKeyCombination"]["members"].append(
            {
                "doc": _extract_doc(lines, i - 1),
                "name": splits[0] + splits[1],
            }
        )

    f.close()


def _get_EOS_UI_EInputStateButtonFlags(r_file_lower2infos: list[str]):
    f = open(os.path.join(sdk_include_dir, "eos_ui_buttons.h"), "r")
    lines: list[str] = f.readlines()

    r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"]["EOS_UI_EInputStateButtonFlags"] = {"doc": "", "members": []}

    for i in range(len(lines)):
        line: str = lines[i]
        if not line.startswith("EOS_UI_KEY_"):
            continue

        splits = line.split("(", 1)[1].rsplit(")")[0].split(", ")
        r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"]["EOS_UI_EInputStateButtonFlags"]["members"].append(
            {
                "doc": _extract_doc(lines, i - 1),
                "name": splits[0] + splits[1],
            }
        )

    f.close()


def _is_handle_arr_type(type: str, name: str) -> bool:
    suffix = "*"
    if name.startswith("Out") or name.startswith("InOut"):
        suffix = "**"
    if not type.endswith(suffix):
        return False
    return _is_handle_type(_decay_eos_type(type))


def _convert_enum_type(ori: str) -> str:
    if ori.startswith("EOS_E"):
        return ori.replace("EOS_E", "")
    elif "_E" in ori:
        splits = ori.split("_")
        splits[2] = splits[2].removeprefix("E")
        splits.pop(0)
        return "_".join(splits)
    else:
        print("ERROR: Unsupported:", ori)
        return ori


def _convert_enum_value(ori: str) -> str:
    return ori.removeprefix("EOS_")


def _is_need_skip_struct(struct_type: str) -> bool:
    return (
        struct_type
        in [
            "EOS_AntiCheatCommon_Quat",
            "EOS_AntiCheatCommon_Vec3f",
            # 直接使用字符串代替
            "EOS_P2P_SocketId",
            # 未使用
            "EOS_UI_Rect",
        ]
        or "_Reserved" in struct_type
    )  # 保留的API, 不能被用户调用


def _is_need_skip_callback(callback_type: str) -> bool:
    return callback_type in ["EOS_IntegratedPlatform_OnUserPreLogoutCallback"]


def _is_need_skip_method(method_name: str) -> bool:
    # TODO: Create , Release, GetInterface 均不需要
    return (
        method_name
        in [
            "EOS_ByteArray_ToString",  # Godot 压根就不需要
            # 废弃 DEPRECATED!
            "EOS_Achievements_CopyAchievementDefinitionByIndex",
            "EOS_Achievements_CopyAchievementDefinitionByAchievementId",
            "EOS_Achievements_GetUnlockedAchievementCount",
            "EOS_Achievements_CopyUnlockedAchievementByIndex",
            "EOS_Achievements_CopyUnlockedAchievementByAchievementId",
            "EOS_Achievements_AddNotifyAchievementsUnlocked",
            "EOS_RTCAudio_RegisterPlatformAudioUser",
            "EOS_RTCAudio_UnregisterPlatformAudioUser",
            "EOS_RTCAudio_GetAudioInputDevicesCount",
            "EOS_RTCAudio_GetAudioInputDeviceByIndex",
            "EOS_RTCAudio_GetAudioOutputDevicesCount",
            "EOS_RTCAudio_GetAudioOutputDeviceByIndex",
            "EOS_RTCAudio_SetAudioInputSettings",
            "EOS_RTCAudio_SetAudioOutputSettings",
            # 废弃 NOT: This api is deprecated.
            "EOS_AntiCheatClient_PollStatus",
        ]
        or "_Reserved" in method_name
    )  # 保留的API, 不能被用户调用


def _is_need_skip_enum_type(ori_enum_type: str) -> bool:
    return ori_enum_type in []


def _is_need_skip_enum_value(ori_enum_type: str, enum_value: str) -> bool:
    map = {
        "EOS_EExternalCredentialType": [
            # DEPRECATED
            "EOS_ECT_STEAM_APP_TICKET"
        ],
    }
    return ori_enum_type in map and enum_value in map[ori_enum_type]


def _get_enum_owned_interface(ori_enum_type: str) -> str:
    for infos in generate_infos.values():
        if ori_enum_type in infos["enums"]:
            print("ERROR UNSUPPORTED ENUM:", ori_enum_type)
            _print_stack_and_exit()
        for h in infos["handles"]:
            if ori_enum_type in infos["handles"][h]["enums"]:
                return _convert_handle_class_name(h)
    print("ERROR UNSUPPORTED ENUM !:", ori_enum_type)
    _print_stack_and_exit()


def _is_reserved_field(field: str, type: str) -> bool:
    return field == "Reserved" and type == "void*"


def is_deprecated_field(field: str) -> bool:
    return (
        field.endswith("_DEPRECATED")
        or field
        in [
            # "Reserved",  # SDK要求保留
            "SystemSpecificOptions",  # 内部处理
        ]
        or field
        in [
            "SystemAuthCredentialsOptions",  # 暂不支持的字段，下载的sdk里没有 (System)/eos_(system).h
            "SystemMemoryMonitorReport",  # 暂不支持的字段，下载的sdk里没有 eos_<platform>_ui.h 文件
            "PlatformSpecificData",  # 暂不支持的字段，下载的sdk里没有 eos_<platform>_ui.h 文件
        ]
    )


def remap_type(type: str, field: str = "", forward_declare: bool = False) -> str:
    if _is_enum_type(type):
        # 枚举类型原样返回
        return type
    if __is_struct_type(type):
        if forward_declare:
            return f"Ref<class {__convert_to_struct_class(type)}>"
        else:
            return f"Ref<{__convert_to_struct_class(type)}>"
    if _is_handle_arr_type(type, field):
        return f"TypedArray<{_convert_handle_class_name(type)}>"
    if _is_handle_type(type, field):
        if forward_declare:
            return f"Ref<class {_convert_handle_class_name(type)}>"
        else:
            return f"Ref<{_convert_handle_class_name(type)}>"
    if _is_internal_struct_arr_field(type, field):
        return f"TypedArray<{__convert_to_struct_class(_decay_eos_type(type))}>"
    if __is_callback_type(_decay_eos_type(type)):
        return "Callable"

    if type.startswith("Union") and len(field):
        union_field_map = {
            "ParamValue": "Variant",
            "Value": "Variant",
            "AccountId": "String",
        }
        return union_field_map[field]

    todo_types = {
        #
        "EOS_PlayerDataStorage_OnReadFileDataCallback": ["ReadFileDataCallback"],
        "EOS_PlayerDataStorage_OnFileTransferProgressCallback": ["FileTransferProgressCallback"],
        "EOS_PlayerDataStorage_OnWriteFileDataCallback": ["WriteFileDataCallback"],
        "EOS_TitleStorage_OnReadFileDataCallback": ["ReadFileDataCallback"],
        "EOS_TitleStorage_OnFileTransferProgressCallback": ["FileTransferProgressCallback"],
        # Arr
        "const EOS_Stats_IngestData*": ["Stats"],
        "const EOS_PresenceModification_DataRecordId*": ["Records"],
        "const EOS_Presence_DataRecord*": ["Records"],
        "const EOS_Leaderboards_UserScoresQueryStatInfo*": ["StatInfo"],
        "const EOS_Ecom_CheckoutEntry*": ["Entries"],
        "const EOS_AntiCheatCommon_RegisterEventParamDef*": ["ParamDefs"],
        "const EOS_AntiCheatCommon_LogEventParamPair*": ["Params"],
    }

    simple_remap = {
        "void": "void",
        "uint8_t": "uint8_t",
        "int64_t": "int64_t",
        "int32_t": "int32_t",
        "uint16_t": "uint16_t",
        "uint32_t": "uint32_t",
        "uint64_t": "uint64_t",
        "EOS_UI_EventId": "uint64_t",
        "EOS_Bool": "bool",
        "float": "float",
        "EOS_LobbyId": "String",
        "const EOS_LobbyId": "String",
        "const char*": "String",
        "EOS_Ecom_SandboxId": "String",
        "const EOS_Ecom_CatalogItemId*": "PackedStringArray",
        ## Options 新增
        "EOS_AntiCheatCommon_Vec3f*": "Vector3",
        "EOS_AntiCheatCommon_Quat*": "Quaternion",
        "const char**": "PackedStringArray",
        "EOS_Ecom_CatalogOfferId": "String",
        "EOS_Ecom_EntitlementId": "String",
        "EOS_Ecom_CatalogItemId": "String",
        "EOS_Ecom_EntitlementName": "String",
        "EOS_Ecom_EntitlementId*": "PackedStringArray",
        "EOS_Ecom_CatalogItemId*": "PackedStringArray",
        "EOS_Ecom_SandboxId*": "PackedStringArray",
        "const char* const*": "PackedStringArray",
        "EOS_Ecom_EntitlementName*": "PackedStringArray",
        "EOS_OnlinePlatformType": "uint32_t",
        "EOS_IntegratedPlatformType": "String",
        "Union{EOS_AntiCheatCommon_ClientHandle : ClientHandle, const char* : String, uint32_t : UInt32, in, EOS_AntiCheatCommon_Vec3f : Vec3f, EOS_AntiCheatCommon_Quat : Quat}": "Variant",
        "Union{int64_t : AsInt64, double : AsDouble, EOS_Bool : AsBool, const char* : AsUtf8}": "Variant",
        "Union{EOS_EpicAccountId : Epic, const char* : External}": "String",
        # 纯句柄
        "EOS_AntiCheatCommon_ClientHandle": "handle_int_t<EOS_AntiCheatCommon_ClientHandle>",
        #
    }

    condition_remap = {
        "void*": {"ClientData": "Variant"},
        "const void*": {
            "DataChunk": "PackedByteArray",
            "MessageData": "PackedByteArray",
            "Data": "PackedByteArray",
            # Options 新增
            "SystemSpecificOptions": "Variant",  # 暂不支持
            "PlatformSpecificData": "Variant",  # 暂不支持
            "InitOptions": "Ref<class EOSIntegratedPlatform_Steam_Options>",  # 暂不支持
            "SystemMemoryMonitorReport": "Variant",  # 暂不支持
        },
        "char": {
            "SocketName[EOS_P2P_SOCKETID_SOCKETNAME_SIZE]": "String",
        },
        "const uint8_t*": {
            "RequestedChannel": "int16_t",  # 可选字段，-1 将转为空指针
        },
        "int16_t*": {"Frame": "PackedInt32Array"},
        "const uint32_t*": {"AllowedPlatformIds": "PackedInt32Array"},  # 平台ID，虽然是uint32_t但可行的值在int32_t的正值范围内
        # 弃用的
        "const EOS_Auth_AccountFeatureRestrictedInfo*": {
            "AccountFeatureRestrictedInfo_DEPRECATED": "Dictionary",
        },
    }

    if type in condition_remap.keys():
        return condition_remap[type].get(field, "Variant")

    return simple_remap.get(type, type)


def _is_expanded_struct(struct_type: str) -> bool:
    if struct_type in [
        # 特殊处理
        "EOS_PlayerDataStorage_ReadFileDataCallbackInfo",
        "EOS_PlayerDataStorage_WriteFileDataCallbackInfo",
        "EOS_PlayerDataStorage_FileTransferProgressCallbackInfo",
        "EOS_PlayerDataStorage_WriteFileCallbackInfo",
        "EOS_PlayerDataStorage_ReadFileCallbackInfo",
        # 以下结构体已经以不展开的方式硬编码
        "EOS_IntegratedPlatform_UserPreLogoutCallbackInfo",
        "EOS_PlayerDataStorage_WriteFileOptions",
        "EOS_PlayerDataStorage_ReadFileOptions",
        "EOS_TitleStorage_ReadFileOptions",
        "EOS_Connect_LoginCallbackInfo",  # PackedPeerMediator 中使用
        "EOS_Connect_LoginStatusChangedCallbackInfo",  # EOSPacketPeerMediator 中使用
        "EOS_Auth_LoginCallbackInfo",
    ]:
        return False
    if struct_type in ["EOS_LogMessage"]:
        # 已经以展开方式硬编码
        return True
    return _decay_eos_type(struct_type) in expanded_as_args_structs


def to_snake_case(text: str) -> str:
    # SPECIAL: char SocketName[EOS_P2P_SOCKETID_SOCKETNAME_SIZE];
    text = text.split("[", 1)[0].removeprefix("b")
    snake_str = "".join(["_" + char.lower() if char.isupper() else char for char in text])
    return (
        snake_str.lstrip("_")
        .replace("u_r_i", "uri")
        .replace("u_r_l", "url")
        .replace("b_is", "is")
        .replace("r_t_c", "rtc")
        .replace("u_i_", "ui_")
        .replace("k_w_s", "kws")
        .replace("p2_p_", "p2p_")
        .replace("n_a_t", "nat")
        # Hack: 句柄将被包装为对象，因此命名上去除 handle 关键字
        .removesuffix("_handle")
        .replace("_handle_", "_")
    )


def __is_arg_out_struct(struct_type: str) -> bool:
    for infos in handles.values():
        for method_info in infos["methods"].values():
            for arg in method_info["args"]:
                if _decay_eos_type(arg["type"]) == struct_type and arg["name"].startswith("Out"):
                    return True

    for method_info in unhandled_methods.values():
        for arg in method_info["args"]:
            if _decay_eos_type(arg["type"]) == struct_type and arg["name"].startswith("Out"):
                print(f"Warning: ", struct_type)
                return True
    return False


def __is_input_struct(struct_type: str) -> bool:
    # Hack
    if struct_type in ["EOS_IntegratedPlatform_Steam_Options"]:
        return True
    for infos in handles.values():
        methods = infos["methods"]
        for method_name in methods:
            if method_name.endswith("Release"):
                # 不检查释放方法
                continue

            method_info = methods[method_name]
            for arg in method_info["args"]:
                if _decay_eos_type(arg["type"]) == struct_type and not arg["name"].startswith("Out"):
                    return True

    for method_name in unhandled_methods:
        if method_name.endswith("Release"):
            # 不检查释放方法
            continue

        method_info = unhandled_methods[method_name]
        for arg in method_info["args"]:
            if _decay_eos_type(arg["type"]) == struct_type and not arg["name"].startswith("Out"):
                print(f"Warning: ", struct_type)
                return True
    return False


def __is_output_struct(struct_type: str) -> bool:
    for infos in handles.values():
        for method_info in infos["methods"].values():
            if _decay_eos_type(method_info["return"]) == struct_type:
                return True
        for callback_info in infos["callbacks"].values():
            for arg in callback_info["args"]:
                if _decay_eos_type(arg["type"]) == struct_type:
                    return True

    for method_info in unhandled_methods.values():
        if _decay_eos_type(method_info["return"]) == struct_type:
            print(f"Warning: ", struct_type)
            return True
    for callback_info in unhandled_callbacks.values():
        for arg in callback_info["args"]:
            if _decay_eos_type(arg["type"]) == struct_type:
                print(f"Warning: ", struct_type)
                return True
    return False


def __is_internal_struct(struct_type: str, r_owned_structs: list[str]) -> bool:
    if struct_type in ["EOS_IntegratedPlatform_Steam_Options"]:
        return False  # Hack
    r_owned_structs.clear()
    for struct_name in structs:
        fields = __get_struct_fields(struct_name)
        for field in fields:
            field_type = fields[field]["type"]
            if not struct_name in r_owned_structs and not _is_internal_struct_arr_field(field_type, field) and _decay_eos_type(field_type) == struct_type:
                r_owned_structs.append(struct_name)
    return len(r_owned_structs) > 0


def __is_internal_struct_of_arr(struct_type: str, r_owned_structs: list[str]) -> bool:
    r_owned_structs.clear()
    if not _decay_eos_type(struct_type) in structs:
        return False
    for struct_name in structs:
        fields = __get_struct_fields(struct_name)
        for field in fields:
            field_type = fields[field]["type"]
            if not struct_name in r_owned_structs and _is_internal_struct_arr_field(field_type, field) and _decay_eos_type(field_type) == struct_type:
                r_owned_structs.append(struct_name)
    return len(r_owned_structs) > 0


def __is_method_input_only_struct(struct_type: str) -> bool:
    if not _decay_eos_type(struct_type) in structs:
        return False
    if __is_internal_struct(struct_type, []) or __is_internal_struct_of_arr(struct_type, []):
        return False
    if __is_arg_out_struct(struct_type) or __is_output_struct(struct_type):
        return False

    for infos in generate_infos.values():
        for m_info in infos["methods"].values():
            for arg in m_info["args"]:
                if struct_type == _decay_eos_type(arg["type"]):
                    return True
        for h_info in infos["handles"].values():
            methods = h_info["methods"]
            for m_info in methods.values():
                for arg in m_info["args"]:
                    if struct_type == _decay_eos_type(arg["type"]):
                        return True
    return False


def __is_callback_output_only_struct(struct_type: str) -> bool:
    if __is_internal_struct_of_arr(struct_type, []) or __is_internal_struct_of_arr(struct_type, []):
        return False
    if __is_arg_out_struct(struct_type) or __is_input_struct(struct_type):
        return False
    for infos in generate_infos.values():
        for cb_info in infos["callbacks"].values():
            for arg in cb_info["args"]:
                if struct_type == _decay_eos_type(arg["type"]):
                    return True
        for h_info in infos["handles"].values():
            for cb_info in h_info["callbacks"].values():
                for arg in cb_info["args"]:
                    if struct_type == _decay_eos_type(arg["type"]):
                        return True
    return False


def _make_additional_method_requirements():
    # 第一遍只检查自身
    for struct_name in structs:
        struct2additional_method_requirements[struct_name] = {
            "set_from": False,
            "from": False,
            "set_to": False,
            "to": False,
        }
        #
        if __is_input_struct(struct_name):
            struct2additional_method_requirements[struct_name]["set_to"] = True
            struct2additional_method_requirements[struct_name]["to"] = True
        if __is_output_struct(struct_name):
            struct2additional_method_requirements[struct_name]["set_from"] = True
            struct2additional_method_requirements[struct_name]["from"] = True
        if __is_arg_out_struct(struct_name):
            struct2additional_method_requirements[struct_name]["set_from"] = True
    # 第二遍检查内部
    for struct_name in structs:
        owned_structs: list[str] = []
        if __is_internal_struct(struct_name, owned_structs):
            for s in owned_structs:
                for k in struct2additional_method_requirements[s]:
                    if struct2additional_method_requirements[s][k]:
                        struct2additional_method_requirements[struct_name][k] = True

        owned_structs.clear()
        if __is_internal_struct_of_arr(struct_name, owned_structs):
            for s in owned_structs:
                if __is_input_struct(s):
                    struct2additional_method_requirements[struct_name]["set_to"] = True  # 不需要 to 附带的实例字段
                if __is_output_struct(s) or __is_arg_out_struct(s):
                    struct2additional_method_requirements[struct_name]["set_from"] = True
                    struct2additional_method_requirements[struct_name]["from"] = True

    # 检出应该被展开为参数的结构体
    for struct_type in structs:
        fields = __get_struct_fields(struct_type)
        field_count = (
            len(fields)
            - (1 if "ClientData" in fields else 0)
            - (1 if "ApiVersion" in fields else 0)
            - (1 if assume_only_one_local_user and "LocalUserId" in fields and _need_ignore_local_user_id_struct(struct_type) else 0)
        )
        if min_field_count_to_expand_input_structs > 0 and field_count <= min_field_count_to_expand_input_structs and __is_method_input_only_struct(struct_type):
            expanded_as_args_structs.append(struct_type)
        if min_field_count_to_expand_callback_structs > 0 and field_count <= min_field_count_to_expand_callback_structs and __is_callback_output_only_struct(struct_type):
            expanded_as_args_structs.append(struct_type)


def _is_deprecated_constant(name: str) -> bool:
    prefixes: list[str] = ["EOS_SAT_", "EOS_OCO_", "EOS_Platform_GetDesktopCrossplayStatusInfo"]
    for p in prefixes:
        if name.startswith(p):
            return True
    return False


def _is_need_skip_constant(name: str) -> bool:
    return (
        name
        in [
            "EOS_ANTICHEATCLIENT_PEER_SELF",  # 指针，非常量
        ]
        or "_RESERVED" in name
    )  # 被保留的常量，不能被用户调用


def _is_string_constant(val: str) -> bool:
    return val.startswith("(const char*)") or val.startswith('"')


def _parse_file(interface_lower: str, fp: str, r_file_lower2infos: dict[str, dict]):
    f = open(fp, "r")
    lines = f.readlines()
    f.close()

    i = 0

    while i < len(lines):
        line = lines[i]
        if len(r_file_lower2infos[interface_lower]["interface_doc"]) <= 0:
            # 尝试提取接口说明(仅识别多行注释)
            if line.startswith("/**") and not line.strip().endswith("*/"):
                is_interface_doc = False
                for j in range(i, len(lines)):
                    if lines[j].startswith(" * @see EOS_Platform_Get") and lines[j].strip().endswith("Interface"):
                        is_interface_doc = True

                    if lines[j].startswith(" */"):
                        if is_interface_doc:
                            i = j + 1
                            r_file_lower2infos[interface_lower]["interface_doc"] = _extract_doc(lines, j)
                            break

                    if len(lines[j].strip()) == 0:
                        doc: list[str] = _extract_doc(lines, j - 1)
                        if len(doc) <= 0:
                            # 非文档尾随空行，跳出
                            break

                        # 第一个非特定文档作为句柄文档, 补充确实的接口获取说明行
                        interface_type = _convert_interface_class_name(interface_lower)
                        if interface_type != "EOS":
                            interface_type = interface_type.removeprefix("EOS")
                        doc.append("\n")
                        doc.append(f"@see EOS_Platform_Get{interface_type}Interface\n")
                        i = j
                        r_file_lower2infos[interface_lower]["interface_doc"] = doc
                        break

        # ApiVersion 宏
        if line.startswith("#define EOS_") and "_API_LATEST" in line:
            macro = line.split(" ", 2)[1]
            api_latest_macros.append(macro)
            i += 1
            continue

        # 常量宏
        if line.startswith("#define EOS_"):
            text: str = line.strip().split(" ", 1)[1]
            splits: list[str] = []
            if len(text.split(" ", 1)) > 1 and not "(" in text.split(" ", 1)[0]:
                splits = text.split(" ", 1)
            if len(text.split("\t", 1)) > 1 and not "(" in text.split(" ", 1)[0]:
                splits = text.split("\t", 1)
            if splits:
                for j in range(len(splits)):
                    splits[j] = splits[j].strip()
                if not _is_deprecated_constant(splits[0]) and not _is_need_skip_constant(splits[0]):
                    r_file_lower2infos[interface_lower]["constants"][splits[0]] = {"doc": _extract_doc(lines, i - 1), "value": splits[1]}

        # 句柄类型
        if "typedef struct " in line:  #  and "Handle*" in line
            handle_type = line.split("* ", 1)[1].split(";", 1)[0]
            r_file_lower2infos[interface_lower]["handles"][handle_type] = {
                "doc": _extract_doc(lines, i - 1),
                "methods": {},
                "callbacks": {},
                "enums": {},
                "constants": {},
            }
            i += 1
            continue

        # 枚举
        if line.startswith("EOS_ENUM(") and not line.split("(")[0] in [
            "EOS_ENUM_START",
            "EOS_ENUM_END",
            "EOS_ENUM_BOOLEAN_OPERATORS",
        ]:
            enum_type = line.split("(")[1].rsplit(",")[0]

            r_file_lower2infos[interface_lower]["enums"][enum_type] = {"doc": _extract_doc(lines, i - 1), "members": []}

            i += 1
            while not lines[i].startswith(");"):
                line = lines[i].lstrip("\t").rstrip("\n").rstrip(",")
                if len(line) <= 0 or line.startswith(" ") or line.startswith("/"):
                    i += 1
                    continue

                splits = line.split(" = ")
                r_file_lower2infos[interface_lower]["enums"][enum_type]["members"].append({"doc": _extract_doc(lines, i - 1), "name": splits[0]})
                i += 1

            i += 1
            continue

        # 方法
        elif line.startswith("EOS_DECLARE_FUNC"):
            method_name = line.split(") ", 1)[1].split("(")[0]
            if method_name in [
                # 弃用却包含在.h文件中的方法
                "EOS_Achievements_AddNotifyAchievementsUnlocked"
            ]:
                i += 1
                continue

            method_info = {
                "doc": _extract_doc(lines, i - 1),
                "return": line.split("(", 1)[1].split(")")[0],
                "args": [],
            }
            args = line.split(" ", 1)[1].split("(", 1)[1].rsplit(")", 1)[0].split(", ")
            for a in args:
                if len(a) <= 0:
                    continue
                splits = a.rsplit(" ", 1)
                if splits[0] == "void":
                    continue
                method_info["args"].append(
                    {
                        "type": splits[0],
                        "name": splits[1],
                    }
                )
            #
            r_file_lower2infos[interface_lower]["methods"][method_name] = method_info

            i += 1
            continue

        # 回调
        elif line.startswith("EOS_DECLARE_CALLBACK"):
            has_return = line.startswith("EOS_DECLARE_CALLBACK_RETVALUE")

            args = line.split("(", 1)[1].rsplit(")")[0].split(", ")
            callback_name = args[1] if has_return else args[0]

            r_file_lower2infos[interface_lower]["callbacks"][callback_name] = {
                "doc": _extract_doc(lines, i - 1),
                "return": args[0] if has_return else "",
                "args": [],
            }

            for arg_idx in range((2 if has_return else 1), len(args)):
                a = args[arg_idx]
                r_file_lower2infos[interface_lower]["callbacks"][callback_name]["args"].append(
                    {
                        "type": a.rsplit(" ", 1)[0],
                        "name": a.rsplit(" ", 1)[1],
                    }
                )

            i += 1
            continue

        # 结构体
        elif line.startswith("EOS_STRUCT"):
            struct_name = line.lstrip("EOS_STRUCT").lstrip("(").rstrip("\n").rstrip(", (")
            r_file_lower2infos[interface_lower]["structs"][struct_name] = {"doc": _extract_doc(lines, i - 1), "fields": {}}

            i += 1

            while not lines[i].startswith("));"):
                line = lines[i].lstrip("\t").rstrip("\n")
                if line.startswith("/") or line.startswith("*") or line.startswith(" ") or len(line) == 0:
                    i += 1
                    continue

                line = line.rsplit(";")[0]
                doc = _extract_doc(lines, i - 1)
                if line.startswith("union"):
                    # Union
                    union_fields = {}
                    i += 2
                    while not lines[i].lstrip("\t").startswith("}"):
                        line = lines[i].lstrip("\t").rstrip("\n")
                        if line.startswith("/") or line.startswith("*") or line.startswith(" ") or len(line) == 0:
                            i += 1
                            continue
                        line = line.rsplit(";")[0]
                        splits = line.rsplit(" ", 1)
                        if len(splits) != 2:
                            print(f"-ERROR: {fp}:{i}\n")
                            print(f"{lines[i]}")
                        else:
                            union_fields[splits[1]] = splits[0]
                        i += 1

                    union_type = "Union{"
                    for union_f in union_fields.keys():
                        union_type += f"{union_fields[union_f]} : {union_f}, "
                    union_type = union_type.rstrip(" ").rstrip(",") + "}"

                    field = lines[i].lstrip("\t").lstrip("}").lstrip(" ").rstrip("\n").rstrip(";")
                    r_file_lower2infos[interface_lower]["structs"][struct_name]["fields"][field] = {"doc": doc, "type": union_type}
                else:
                    # Regular
                    splits = line.rsplit(" ", 1)
                    if len(splits) != 2:
                        print(f"ERROR: {fp}:{i}\n")
                        print(f"{lines[i]}")
                    else:
                        r_file_lower2infos[interface_lower]["structs"][struct_name]["fields"][splits[1]] = {"doc": doc, "type": splits[0]}

                i += 1

            if struct_name in ["EOS_AntiCheatCommon_Vec3f", "EOS_AntiCheatCommon_Quat"]:
                #
                r_file_lower2infos[interface_lower]["structs"].pop(struct_name)

            i += 1
            continue

        else:
            i += 1
            continue


def _extract_doc(lines: list[str], idx: int) -> list[str]:
    doc: list[str] = []
    while idx >= 0:
        line: str = lines[idx].lstrip("\t")

        valid = False
        for prefix in [" */", "//", "/**", " *"]:
            if line.startswith(prefix):
                line = line.removeprefix(prefix).removeprefix(" ")
                valid = True
                break

        if valid:
            # 将前置空格每 4 个转为一个 缩进
            prefix_space_count = 0
            while line.startswith(" "):
                prefix_space_count += 1
                line = line.removeprefix(" ")
            line = line.replace("*/\n", "\n")

            for _i in range(divmod(prefix_space_count, 4)[0]):
                line = "\t" + line

            doc.append(line)
            idx -= 1
        else:
            break

    # 去除首尾空行
    while len(doc) > 0:
        if len(doc[0].strip()) <= 0:
            doc.pop(0)
        else:
            break

    while len(doc) > 0:
        if len(doc[len(doc) - 1].strip()) <= 0:
            doc.pop(len(doc) - 1)
        else:
            break

    doc.reverse()

    for i in range(len(doc)):
        while "<" in doc[i] and "/>" in doc[i]:
            doc[i] = doc[i].replace("<", "(").replace("/>", ")")

    return doc


def _optimize_doc(doc: list[str]) -> list[str]:
    # 拼接: TODO 在所有信息处理后再进行(需要判断 _Options是否被展开)
    ret: list[str] = []
    in_details: bool = False
    for i in range(len(doc)):
        # 特殊处理
        if doc[i].lstrip().startswith("@"):
            line = doc[i].lstrip()
            if line.startswith("@see"):
                see_type: str = line.removeprefix("@see").strip()
                if see_type.endswith("_Release"):
                    # 跳过对句柄释放方法的说明（转为 GDScript 用的 SDK 后已管理好所有的内存问题）
                    continue
                if "RemoveNotify" in see_type:
                    # 由 EOSNotification 处理，不再需要手动移除
                    continue
                elif _is_expanded_struct(see_type):
                    # 跳过被展开的结构体类型说明
                    continue
            elif assume_only_one_local_user and line.startswith("@param LocalUserId"):
                # 假定只有一个本地用户时不需要该项说明
                continue
            elif line.startswith("@param ClientData"):
                # 不需要该参数
                continue

        if len(ret) <= 0:
            # 首行
            ret.append(doc[i])
            in_details = False
        elif len(doc[i].strip()) <= 0:
            # 跳过空行
            in_details = False
        elif doc[i].lstrip().startswith("@"):
            # 单行注释
            ret.append(doc[i])
            in_details = False
        elif doc[i].removeprefix(" ").startswith("\t"):
            # 前置缩进
            ret.append(doc[i])
            in_details = False
        elif __is_int_str(doc[i].lstrip().split(".")[0].strip()):
            # 标号开头
            ret.append(doc[i])
            in_details = False
        else:
            last_idx = len(ret) - 1

            if not in_details:
                # 详情行
                if ret[last_idx].rstrip().endswith(":"):
                    in_details = True

            if in_details:
                ret.append(doc[i])
            else:
                # 其他情况下拼接到上一行
                ret[last_idx] = ret[last_idx].rstrip() + doc[i]
    return ret


def __is_int_str(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        return False


def _decay_eos_type(t: str) -> str:
    ret = t.lstrip("const").lstrip(" ").rstrip("*").rstrip("&").rstrip("*").rstrip("&").lstrip(" ").rstrip(" ")
    return ret


def _is_client_data_field(type: str, field: str) -> bool:
    return type == "void*" and field == "ClientData"


def _is_internal_struct_field(type: str, field: str) -> bool:
    decayed = _decay_eos_type(type)
    if decayed in ["EOS_AntiCheatCommon_Vec3f", "EOS_AntiCheatCommon_Quat"]:
        return False
    if decayed in structs:
        return True
    return False


def _is_pure_handle_type(type: str) -> bool:
    return type in ["EOS_AntiCheatCommon_ClientHandle"]


def _is_variant_union_type(type: str, field: str) -> bool:
    return type.startswith("Union") and field != "AccountId"


def _is_internal_struct_arr_field(type: str, field: str) -> bool:
    # 特殊处理
    struct_arr_map = {
        "const EOS_Stats_IngestData*": ["Stats"],
        "const EOS_PresenceModification_DataRecordId*": ["Records"],
        "const EOS_Presence_DataRecord*": ["Records"],
        "const EOS_Leaderboards_UserScoresQueryStatInfo*": ["StatInfo"],
        "const EOS_Ecom_CheckoutEntry*": ["Entries"],
        "const EOS_AntiCheatCommon_RegisterEventParamDef*": ["ParamDefs"],
        "const EOS_AntiCheatCommon_LogEventParamPair*": ["Params"],
        "const EOS_Achievements_StatThresholds*": ["StatThresholds"],
        "const EOS_Achievements_PlayerStatInfo*": ["StatInfo"],
    }
    return type in struct_arr_map and field in struct_arr_map[type]


def _is_requested_channel_ptr_field(type: str, field: str) -> bool:
    return type == "const uint8_t*" and field == "RequestedChannel"


def _is_arr_field(type: str, field_or_arg: str) -> bool:
    if _is_internal_struct_arr_field(type, field_or_arg):
        return False
    if _is_internal_struct_field(type, field_or_arg):
        return False
    if _is_requested_channel_ptr_field(type, field_or_arg):
        return False
    if _is_nullable_float_pointer_field(type, field_or_arg):
        return False
    if type in [
        "const char*",
        "void*",
    ]:
        return False
    if type == "const void*":
        if field_or_arg in ["PlatformSpecificData", "SystemMemoryMonitorReport", "InitOptions"]:
            return False
    if _decay_eos_type(type) in ["EOS_AntiCheatCommon_Vec3f", "EOS_AntiCheatCommon_Quat"]:
        return False
    if field_or_arg.startswith("Out") or field_or_arg.startswith("InOut") or field_or_arg.startswith("bOut"):
        if type.endswith("**") or type.endswith("*"):
            return False  # 目前未发现有数组类型的Out参数
    return type.endswith("*")


def _is_handle_type(type: str, field: str = "") -> bool:
    return type in handles or (type.startswith("EOS") and "_H" in type) or type in ["EOS_ContinuanceToken"]


def _find_count_field(field: str, fields: list[str]) -> str:
    splits = to_snake_case(field).split("_")
    similar_fields: list[str] = []
    for f in fields:
        if f == fields:
            continue
        if f.endswith("Count") or f.endswith("Size") or f.endswith("Length") or f.endswith("LengthBytes") or f.endswith("SizeBytes"):
            f_splits = to_snake_case(f).split("_")
            similar = 0
            for i in range(min(2, len(f_splits), len(splits))):
                if f_splits[i].removesuffix("s").removesuffix("y") == splits[i].removesuffix("ies").removesuffix("s"):
                    similar += 1
                else:
                    break
            if similar >= min(2, len(f_splits), len(splits)):
                return f
            else:
                if similar > 0:
                    similar_fields.append(f)
    if len(similar_fields) == 1:
        return similar_fields[0]

    print("== error:", field, similar_fields)
    print(field, fields)
    _print_stack_and_exit()


def _is_todo_field(type: str, field: str) -> bool:
    # TODO：暂未实现的字段
    # type: [field1, field2, ...]
    map = {}
    return type in map and field in map[type]


def _is_system_initialize_options_filed(field: str, type: str) -> bool:
    return field == "SystemInitializeOptions" and type == "void*"


def _is_platform_specific_options_field(field: str) -> bool:
    return field == "PlatformSpecificOptions"


def _is_memory_func_type(type: str) -> bool:
    return type in ["EOS_AllocateMemoryFunc", "EOS_ReallocateMemoryFunc", "EOS_ReleaseMemoryFunc"]


def _is_integrated_platform_init_option(type: str, field: str) -> bool:
    return type == "const void*" and field == "InitOptions"


def _is_nullable_float_pointer_field(type: str, field: str) -> bool:
    map = {"double*": ["TaskNetworkTimeoutSeconds"]}
    return type in map and field in map[type]


def _is_struct_ptr(type: str) -> bool:
    return type in ["EOS_AntiCheatCommon_Vec3f*", "EOS_AntiCheatCommon_Quat*"]


def _is_str_type(type: str, name: str) -> bool:
    # HACK
    if _is_socket_id_type(type, name):
        return True
    return not type.startswith("Union") and remap_type(type, name) == "String"


def _is_str_arr_type(type: str, name: str) -> bool:
    return remap_type(type, name) == "PackedStringArray"


def _is_socket_id_type(type: str, name: str) -> bool:
    return type == "EOS_P2P_SocketId"


def _is_audio_frames_type(type: str, field: str) -> bool:
    map = {"int16_t*": ["Frames"]}
    return type in map and field in map[type]


def _is_local_user_id(field: str) -> bool:
    return field == "LocalUserId"


def _get_login_interface_of_local_user_id(field: str, eos_type: str) -> str:
    _assert(_is_local_user_id(field))
    interface_lower: str = ""
    if _decay_eos_type(eos_type) == "EOS_ProductUserId":
        interface_lower = "eos_connect"
    else:
        interface_lower = "eos_auth"
    return _convert_interface_class_name(interface_lower)


def _get_gd_type_of_local_user_id(field: str, eos_type: str) -> str:
    _assert(_is_local_user_id(field))
    return _convert_handle_class_name(_decay_eos_type(eos_type))


def _is_enum_flags_type(type: str) -> bool:
    return _is_enum_type(type) and (type.endswith("Flags") or type.endswith("Combination"))


def __find_count_and_variant_type_fields_in_struct(struct_type: bool) -> list[str]:
    ret: list[str] = []
    fields: dict[str, dict[str, str]] = structs[struct_type]["fields"]
    for field in fields.keys():
        if is_deprecated_field(field):
            ret.append(field)
            continue

        field_type = fields[field]["type"]
        # 检出count字段，Godot不需要及将其作为成员
        if _is_arr_field(field_type, field) or _is_internal_struct_arr_field(field_type, field):
            ret.append(_find_count_field(field, fields.keys()))

        # 检出Variant式的联合体类型字段，Godot不需要及将其作为成员
        elif _is_variant_union_type(field_type, field):
            for f in fields.keys():
                if f == field + "Type":
                    ret.append(f)
                    break

    return ret


def _gen_struct_v2(
    struct_type: str,
    struct_info: dict,
    r_structs_cpp: list[str],
) -> list[str]:
    fields: dict[str, dict[str, str]] = struct_info["fields"]
    member_lines: list[str] = []
    setget_declare_lines: list[str] = []
    setget_define_lines: list[str] = []
    bind_lines: list[str] = []

    #
    count_and_variant_type_fields: list[str] = __find_count_and_variant_type_fields_in_struct(struct_type)

    additional_methods_requirements = struct2additional_method_requirements[struct_type]

    typename = __convert_to_struct_class(struct_type)

    #
    for field in fields.keys():
        type: str = fields[field]["type"]
        snake_field_name: str = to_snake_case(field)
        decayed_type: str = _decay_eos_type(type)
        remapped_type: str = ""

        if not _is_need_skip_struct(decayed_type) and __is_struct_type(decayed_type) and not _is_internal_struct_arr_field(type, field):
            # 非数组的结构体
            remapped_type = remap_type(decayed_type, field)
        elif _is_nullable_float_pointer_field(type, field):
            remapped_type = _decay_eos_type(type)
        elif _is_handle_type(decayed_type):
            # 句柄类型使用Ref<RefCounted>作为成员变量，非 msvc 编译器不支持Ref<T>作为成员时T的前向声明
            remapped_type = "Ref<RefCounted>"
        else:
            remapped_type = remap_type(type, field)

        if is_deprecated_field(field):
            continue
        elif field in count_and_variant_type_fields:
            continue
        elif _is_memory_func_type(type):
            continue  # 内存分配方法不需要成员变量
        elif _is_todo_field(type, field):
            continue
        elif _is_platform_specific_options_field(field):
            continue
        elif _is_system_initialize_options_filed(field, type):
            continue
        elif _is_reserved_field(field, type):
            continue
        elif _is_client_data_field(type, field):
            continue  # 暴露的结构体不再含有 ClientData 字段
        elif __is_api_version_field(type, field):
            continue  # 不需要ApiVersion作为成员
        elif assume_only_one_local_user and _is_local_user_id(field) and _need_ignore_local_user_id_struct(struct_type=struct_type):
            if struct_type == "EOS_Connect_LoginCallbackInfo":
                # 特殊处理
                setget_declare_lines.append(f"\tRef<class {_convert_handle_class_name(type)}> get_local_user_id() const;")
                setget_define_lines.append(
                    f"Ref<{_convert_handle_class_name(type)}> {__convert_to_struct_class(struct_type)}::get_local_user_id() const {{ return eos::{_get_gd_type_of_local_user_id(field, type)}::get_local(); }}"
                )
            continue  # 假定只有一个本地用户时不生产该字段
        elif remapped_type == "bool":
            bind_lines.append(f"\t_BIND_PROP_BOOL({snake_field_name})")
            member_lines.append(f"\tbool {snake_field_name}{{}};")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_BOOL({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_BOOL({typename}, {snake_field_name})")
        elif _is_socket_id_type(decayed_type, field):
            bind_lines.append(f"\t_BIND_PROP_STR({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STR({snake_field_name})")
            if additional_methods_requirements["set_to"]:
                member_lines.append(f"\tEOS_P2P_SocketId {snake_field_name};")
                setget_define_lines.append(f"_DEFINE_SETGET_STR_SOCKET_ID({typename}, {snake_field_name})")
            else:
                member_lines.append(f"\tCharString {snake_field_name};")
                setget_define_lines.append(f"_DEFINE_SETGET_STR_SOCKET_NAME({typename}, {snake_field_name})")
        elif _is_str_type(type, field):
            bind_lines.append(f"\t_BIND_PROP_STR({snake_field_name})")
            member_lines.append(f"\tCharString {snake_field_name};")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STR({snake_field_name})")
            if not field.startswith("Socket"):
                setget_define_lines.append(f"_DEFINE_SETGET_STR({typename}, {snake_field_name})")
            else:
                setget_define_lines.append(f"_DEFINE_SETGET_STR_SOCKET_NAME({typename}, {snake_field_name})")
        elif _is_str_arr_type(type, field):
            bind_lines.append(f"\t_BIND_PROP_STR_ARR({to_snake_case(field)})")
            member_lines.append(f"\tLocalVector<CharString> {snake_field_name};")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STR_ARR({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_STR_ARR({typename}, {snake_field_name})")
            if additional_methods_requirements["to"]:
                # 需要转为eos类型的结构体数组才需要的字段
                element_type: str = __get_str_arr_element_type(type)
                if element_type != "const char*":  # 如果是C字符串则直接使用CharString
                    member_lines.append(f"\tLocalVector<{element_type}> _shadow_{snake_field_name}{{}};")
        elif _is_handle_arr_type(type, ""):
            bind_lines.append(f"\t_BIND_PROP_TYPED_ARR({snake_field_name}, {_convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\tTypedArray<class {_convert_handle_class_name(decayed_type)}> {snake_field_name};")
            if additional_methods_requirements["to"]:
                # 需要转为eos类型的结构体数组才需要的字段
                member_lines.append(f"\tLocalVector<{_decay_eos_type(type)}> _shadow_{snake_field_name}{{}};")
        elif _is_handle_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_field_name}, {_convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_TYPED({snake_field_name}, Ref<class {_convert_handle_class_name(decayed_type)}>)")
            setget_define_lines.append(f"_DEFINE_SETGET_TYPED({typename}, {snake_field_name}, {remap_type(decayed_type, field)})")
            member_lines.append(f"\t{remapped_type} {snake_field_name};")
        elif _is_struct_ptr(type):
            bind_lines.append(f"\t_BIND_PROP_STRUCT_PTR({snake_field_name}, {remap_type(type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STRUCT_PTR({remapped_type}, {snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_STRUCT_PTR({typename}, {remapped_type},  {snake_field_name})")
            member_lines.append(f"\t{_decay_eos_type(type)} {snake_field_name}{{}};")
        elif _is_internal_struct_arr_field(type, field):
            bind_lines.append(f"\t_BIND_PROP_TYPED_ARR({snake_field_name}, {_convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{}};")
            if additional_methods_requirements["to"]:
                # 需要转为eos类型的结构体数组才需要的字段
                member_lines.append(f"\tLocalVector<{_decay_eos_type(type)}> _shadow_{snake_field_name}{{}};")
        elif __is_struct_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_field_name}, {_convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{}};")
        elif _is_enum_flags_type(type):
            bind_lines.append(f"\t_BIND_PROP_FLAGS({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_FLAGS({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_FLAGS({typename}, {snake_field_name})")
            member_lines.append(f"\tBitField<{type}> {snake_field_name}{{{type}{{}}}};")
        elif _is_audio_frames_type(type, field):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\tPackedInt32Array {snake_field_name}{{}};")
            member_lines.append(f"\tLocalVector<int16_t> _shadow_{snake_field_name}{{}};")
        elif _is_nullable_float_pointer_field(type, field):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ -1.0 }};")
        elif _is_pure_handle_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ 0 }};")
        elif remapped_type.startswith("Ref") and not type.startswith("Ref<class ") and not decayed_type == "EOS_IntegratedPlatform_Steam_Options":
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name};")
        elif _is_requested_channel_ptr_field(type, field):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ -1 }};")
        elif type == "int32_t" and field == "ApiVersion":
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ {__get_api_latest_macro(struct_type)} }};")
        else:
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{}};")

        _insert_doc_property(typename, snake_field_name, fields[field]["doc"])

    # 对某些类型进行特殊处理
    if struct_type == "EOS_PlayerDataStorage_WriteFileDataCallbackInfo":
        # GDExtension 的数组与 godot 之间不是引用传递，无法以out参数将data_buffer传递给回调,
        # 因此为回调信息添加一个 out_data_buffer 字段作为输出- 2024.4.20
        member_lines.append(f"\tPackedByteArray out_data_buffer{{}};")
        setget_declare_lines.append(f"\t_DECLARE_SETGET(out_data_buffer)")
        setget_define_lines.append(f"_DEFINE_SETGET({typename}, out_data_buffer)")
        bind_lines.append(f"\t_BIND_PROP(out_data_buffer)")

    if struct_type in ["EOS_Lobby_AttributeData", "EOS_Sessions_AttributeData"]:
        # 为这两个类提供make方法
        setget_declare_lines.append("")
        setget_declare_lines.append(f"\tstatic Ref<{typename}> make(const String& p_key, const Variant& p_value);")
        setget_define_lines.append("")
        setget_define_lines.append(f"Ref<{typename}> {typename}::make(const String& p_key, const Variant& p_value) {{")
        setget_define_lines.append(f"\tRef<{typename}> ret; ret.instantiate();")
        setget_define_lines.append("\tret->set_key(p_key);")
        setget_define_lines.append("\tret->set_value(p_value);")
        setget_define_lines.append("\treturn ret;")
        setget_define_lines.append("}")
        bind_lines.append("")
        bind_lines.append(f'\tClassDB::bind_static_method(get_class_static(), D_METHOD("make", "key", "value"), &{typename}::make);')

    # h
    lines: list[str] = [""]
    lines.append(f"class {typename} : public EOSDataClass {{")
    lines.append(f"\tGDCLASS({typename}, EOSDataClass)")
    lines.append("")
    lines += member_lines
    if additional_methods_requirements["to"]:
        lines.append("")
        lines.append(f"\t{struct_type} m_eos_data{{}};")
    lines.append("")
    lines.append("public:")
    lines += setget_declare_lines
    lines.append("")
    if additional_methods_requirements["set_from"]:
        lines.append(f"\tvoid set_from_eos(const {struct_type} &p_origin);")
    if additional_methods_requirements["from"]:
        lines.append(f"\tstatic Ref<{typename}> from_eos(const {struct_type} &p_origin);")
    if additional_methods_requirements["set_to"]:
        lines.append(f"\tvoid set_to_eos({struct_type} &p_origin);")
    if additional_methods_requirements["to"]:
        lines.append(f"\t{struct_type} &to_eos() {{set_to_eos(m_eos_data); return m_eos_data;}}")
    lines.append("")
    lines.append(f"\tString _to_string() const;")
    lines.append("protected:")
    lines.append("\tstatic void _bind_methods();")
    lines.append("};")
    lines.append("")

    # cpp
    r_structs_cpp += setget_define_lines
    r_structs_cpp.append(f"void {typename}::_bind_methods() {{")
    r_structs_cpp.append(f"\t_BIND_BEGIN({typename})")
    r_structs_cpp += bind_lines
    r_structs_cpp.append(f"\t_BIND_END()")
    r_structs_cpp.append("}")
    r_structs_cpp.append("")

    optional_cpp_lines: list[str] = []

    if additional_methods_requirements["from"]:
        r_structs_cpp.append(f"Ref<{typename}> {typename}::from_eos(const {struct_type} &p_origin) {{")
        r_structs_cpp.append(f"\tRef<{typename}> ret;")
        r_structs_cpp.append(f"\tret.instantiate();")
        r_structs_cpp.append(f"\tret->set_from_eos(p_origin);")
        r_structs_cpp.append(f"\treturn ret;")
        r_structs_cpp.append("}")

    if additional_methods_requirements["set_from"]:
        r_structs_cpp.append(f"void {typename}::set_from_eos(const {struct_type} &p_origin) {{")
        for field in fields.keys():
            field_type = fields[field]["type"]
            snake_case_field = to_snake_case(field)

            if is_deprecated_field(field):
                continue
            if field in count_and_variant_type_fields:
                continue
            if _is_todo_field(field_type, field):
                continue
            if __is_api_version_field(field_type, field):
                continue
            if _is_client_data_field(field_type, field):
                continue  # 暴露的结构体不再含有 ClientData 字段
            if _is_memory_func_type(field_type):
                # 内存分配方法不需要成员变量
                print("ERROR Unsupported")
                _print_stack_and_exit()

            if _is_platform_specific_options_field(field):
                print("ERROR:", field)
                _print_stack_and_exit()
            elif _is_system_initialize_options_filed(field, field_type):
                print("ERROR:", field)
                _print_stack_and_exit()
            elif _is_reserved_field(field, field_type):
                print("ERROR:", field)
                _print_stack_and_exit()
            elif _is_nullable_float_pointer_field(field_type, field):
                print("ERROR:", field)
                _print_stack_and_exit()
            elif assume_only_one_local_user and _is_local_user_id(field) and _need_ignore_local_user_id_struct(struct_type=struct_type):
                # 假定只有一个本地用户时不生成该字段,仅做检查
                if _need_check_null_local_user_id_struct(struct_type):
                    r_structs_cpp.append(
                        f'\tif(!{_get_gd_type_of_local_user_id(field, field_type)}::_is_valid_local_id(p_origin.{field})) {{ ERR_PRINT("The local user id in output struct is not compatible with existing local user!!"); }}'
                    )
            elif _is_socket_id_type(_decay_eos_type(field_type), field):
                if additional_methods_requirements["set_to"]:
                    r_structs_cpp.append(f"\tmemcpy(&{snake_case_field}.SocketName[0], &p_origin.{field}.SocketName[0], EOS_P2P_SOCKETID_SOCKETNAME_SIZE);")
                else:
                    r_structs_cpp.append(f"\t{snake_case_field}.resize(EOS_P2P_SOCKETID_SOCKETNAME_SIZE);")
                    r_structs_cpp.append(f"\t{snake_case_field} = p_origin.{field}->SocketName;")
            elif _is_str_type(field_type, field):
                if field.startswith("SocketName"):
                    print("ERROR unreachable case: EOS_P2P_SocketId should not be wrap as a Godot class.")
                    _print_stack_and_exit()
                else:
                    r_structs_cpp.append(f"\t{snake_case_field} = to_godot_type<{field_type}, CharString>(p_origin.{field});")
            elif _is_str_arr_type(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_STR_ARR({snake_case_field}, p_origin.{field}, p_origin.{_find_count_field(field, fields.keys())});")
            elif _is_pure_handle_type(_decay_eos_type(field_type)):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_PURE_HANDLE({snake_case_field}, p_origin.{field});")
            elif _is_requested_channel_ptr_field(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_REQUESTED_CHANNEL({snake_case_field}, p_origin.{field});")
            elif field_type.startswith("Union"):
                if _is_variant_union_type(field_type, field):
                    r_structs_cpp.append(f"\t_FROM_EOS_FIELD_VARIANT_UNION({snake_case_field}, p_origin.{field});")
                else:
                    r_structs_cpp.append(f"\t_FROM_EOS_FIELD_METRICS_ACCOUNT_ID_UNION({snake_case_field}, p_origin.{field});")
            elif _is_handle_arr_type(field_type, ""):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_HANDLER_ARR({snake_case_field}, {_convert_handle_class_name(_decay_eos_type(field_type))}, p_origin.{field}, p_origin.{_find_count_field(field, fields.keys())});"
                )
            elif _is_handle_type(_decay_eos_type(field_type), field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_HANDLER({snake_case_field}, {_convert_handle_class_name(_decay_eos_type(field_type))}, p_origin.{field});")
            elif _is_internal_struct_arr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_STRUCT_ARR({__convert_to_struct_class(field_type)}, {snake_case_field}, p_origin.{field}, p_origin.{_find_count_field(field, fields.keys())});"
                )
            elif _is_internal_struct_field(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_STRUCT({snake_case_field}, p_origin.{field});")
            elif _is_arr_field(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_ARR({snake_case_field}, p_origin.{field}, p_origin.{_find_count_field(field, fields.keys())});")
            elif _is_enum_flags_type(field_type):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_FLAGS({snake_case_field}, p_origin.{field.split('[')[0]});")
            else:
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD({snake_case_field}, p_origin.{field.split('[')[0]});")
        r_structs_cpp.append("}")

    if additional_methods_requirements["set_to"]:
        r_structs_cpp.append(f"void {typename}::set_to_eos({struct_type} &p_data) {{")
        # r_structs_cpp.append(f"\tmemset(&p_data, 0, sizeof(p_data));")

        for field in fields.keys():
            field_type = fields[field]["type"]
            snake_field_name = to_snake_case(field)

            # if field == "Reserved" and field_type == "void*":
            #     # TODO：考虑使用memset直接将整个结构体清零避免对预留字段的特殊处理
            #     r_structs_cpp.append(f"\tp_data.Reserved = nullptr;")

            if is_deprecated_field(field):
                continue
            if field in count_and_variant_type_fields:
                continue
            if _is_todo_field(field_type, field):
                continue

            if field_type == "EOS_AllocateMemoryFunc":
                r_structs_cpp.append(f"\tp_data.AllocateMemoryFunction = &internal::_memallocate;")
            elif field_type == "EOS_ReallocateMemoryFunc":
                r_structs_cpp.append(f"\tp_data.ReallocateMemoryFunction = &internal::_memreallocate;")
            elif field_type == "EOS_ReleaseMemoryFunc":
                r_structs_cpp.append(f"\tp_data.ReleaseMemoryFunction = &internal::_memrelease;")
            else:
                if assume_only_one_local_user and _is_local_user_id(field) and _need_ignore_local_user_id_struct(struct_type=struct_type):
                    # 假定只有一个本地用户时不生成该字段,从静态变量中查找
                    interface_class = _get_login_interface_of_local_user_id(field, type)
                    if _need_check_null_local_user_id_struct(struct_type):
                        r_structs_cpp.append(
                            f'\tif({_get_gd_type_of_local_user_id(field, field_type)}::_get_local_native() == nullptr) {{ ERR_PRINT("Setup \\"{typename}\\" failed: has not local user, please login by using \\"{interface_class}.login()\\" first."); }}'
                        )
                    r_structs_cpp.append(f"\tp_data.{field} = {_get_gd_type_of_local_user_id(field, field_type)}::_get_local_native();")
                elif __is_api_version_field(field_type, field):
                    r_structs_cpp.append(f"\tp_data.{field} = {__get_api_latest_macro(struct_type)};")
                elif _is_audio_frames_type(field_type, field):
                    r_structs_cpp.append(f"\t_packed_int32_to_audio_frames({snake_field_name}, _shadow_{snake_field_name});")
                    r_structs_cpp.append(f"\tp_data.{field} = _shadow_{snake_field_name}.ptr();")
                    r_structs_cpp.append(f"\tp_data.{_find_count_field(field, fields.keys())} = _shadow_{snake_field_name}.size();")
                elif _is_struct_ptr(field_type):
                    r_structs_cpp.append(f"\tp_data.{field} = &{snake_field_name};")
                elif _is_socket_id_type(_decay_eos_type(field_type), field):
                    r_structs_cpp.append(f"\t{snake_field_name}.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;")
                    r_structs_cpp.append(f"\tp_data.{field} = &{snake_field_name};")
                elif _is_reserved_field(field, field_type):
                    r_structs_cpp.append(f"\tp_data.{field} = nullptr;")
                elif _is_str_type(field_type, field):
                    if field.startswith("SocketName"):
                        print("ERROR unreachable case: EOS_P2P_SocketId should not be wrap as a Godot class.")
                        _print_stack_and_exit()
                    else:
                        r_structs_cpp.append(f"\tp_data.{field} = to_eos_type<const CharString &, {field_type}>({snake_field_name});")
                elif _is_str_arr_type(field_type, field):
                    count_filed: str = _find_count_field(field, fields.keys())
                    if __get_str_arr_element_type(field_type) == "const char*":
                        # C字符串数组直接使用LocalVector<CharString>的指针
                        r_structs_cpp.append(f"\tp_data.{field} = (decltype(p_data.{field})){snake_field_name}.ptr();")
                        r_structs_cpp.append(f"\tp_data.{count_filed} = {snake_field_name}.size();")
                    else:
                        r_structs_cpp.append(f"\t_TO_EOS_STR_ARR(p_data.{field}, {snake_field_name}, _shadow_{snake_field_name}, p_data.{count_filed});")
                elif _is_nullable_float_pointer_field(field_type, field):
                    r_structs_cpp.append(f"\tp_data.{field} = ({snake_field_name} <= 0.0)? nullptr: (double*)(&{snake_field_name});")
                elif _is_platform_specific_options_field(field):
                    r_structs_cpp.append(f"\tp_data.{field} = get_platform_specific_options();")
                elif _is_system_initialize_options_filed(field, field_type):
                    r_structs_cpp.append(f"\tp_data.{field} = get_system_initialize_options();")
                elif _is_pure_handle_type(_decay_eos_type(field_type)):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_PURE_HANDLE(p_data.{field}, {snake_field_name});")
                elif _is_requested_channel_ptr_field(field_type, field):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_REQUESTED_CHANNEL(p_data.{field}, {snake_field_name});")
                elif field_type.startswith("Union"):
                    if _is_variant_union_type(field_type, field):
                        r_structs_cpp.append(f"\t_TO_EOS_FIELD_VARIANT_UNION(p_data.{field}, {snake_field_name});")
                    else:
                        r_structs_cpp.append(f"\t_TO_EOS_FIELD_METRICS_ACCOUNT_ID_UNION(p_data.{field}, {snake_field_name});")
                elif _is_handle_arr_type(field_type, ""):
                    r_structs_cpp.append(
                        f"\t_TO_EOS_FIELD_HANDLER_ARR(p_data.{field}, {snake_field_name}, _shadow_{snake_field_name}, p_data.{_find_count_field(field, fields.keys())});"
                    )
                elif _is_handle_type(_decay_eos_type(field_type), field):
                    gd_type = _convert_handle_class_name(_decay_eos_type(field_type))
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_HANDLER(p_data.{field}, {snake_field_name}, {gd_type});")
                elif _is_client_data_field(field_type, field):
                    # 没有需要设置ClientData的结构体
                    print("ERR:", struct_type)
                    _print_stack_and_exit()
                elif _is_internal_struct_arr_field(field_type, field):
                    r_structs_cpp.append(
                        f"\t_TO_EOS_FIELD_STRUCT_ARR(p_data.{field}, {snake_field_name}, _shadow_{snake_field_name}, p_data.{_find_count_field(field, fields.keys())});"
                    )
                elif _is_internal_struct_field(field_type, field) or _is_integrated_platform_init_option(field_type, field):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_STRUCT(p_data.{field}, {snake_field_name});")
                elif _is_arr_field(field_type, field):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_ARR(p_data.{field}, {snake_field_name}, p_data.{_find_count_field(field, fields.keys())});")
                elif _is_enum_flags_type(field_type):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_FLAGS(p_data.{field}, {snake_field_name});")
                elif __is_callback_type(_decay_eos_type(field_type)):
                    cb_arg = _get_callback_infos(_decay_eos_type(field_type))["args"][0]
                    eos_cb_type = _decay_eos_type(cb_arg["type"])
                    gd_cb_type = remap_type(eos_cb_type).removeprefix("Ref<").removesuffix(">")
                    signal_name = __convert_to_signal_name(_decay_eos_type(field_type), "")

                    const_str_line: str = f'constexpr char {signal_name}[] = "{signal_name}";'
                    if not const_str_line in optional_cpp_lines and not const_str_line in r_structs_cpp:
                        optional_cpp_lines.append(const_str_line)

                    if field_type == "EOS_PlayerDataStorage_OnReadFileDataCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::read_file_data_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    elif field_type == "EOS_PlayerDataStorage_OnWriteFileDataCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::write_file_data_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    elif field_type == "EOS_PlayerDataStorage_OnFileTransferProgressCallback":
                        r_structs_cpp.append(
                            f"\tp_data.{field} = &godot::eos::internal::file_transfer_progress_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;"
                        )
                    elif field_type == "EOS_TitleStorage_OnReadFileDataCallback":
                        r_structs_cpp.append(
                            f"\tp_data.{field} = &godot::eos::internal::title_storage_read_file_data_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;"
                        )
                    elif field_type == "EOS_TitleStorage_OnFileTransferProgressCallback":
                        r_structs_cpp.append(
                            f"\tp_data.{field} = &godot::eos::internal::file_transfer_progress_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;"
                        )
                    else:
                        print("ERROR: ", field_type)
                        _print_stack_and_exit()
                else:
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD(p_data.{field.split('[')[0]}, {to_snake_case(field)});")

        r_structs_cpp.append("}")

        insert_idx = 0
        for i in range(len(r_structs_cpp)):
            if not r_structs_cpp[i].startswith("namespace"):
                continue
            insert_idx = i
            break

        for line in optional_cpp_lines:
            r_structs_cpp.insert(insert_idx, line)

    r_structs_cpp.append("")
    r_structs_cpp.append(f'String {typename}::_to_string() const {{ return vformat("<{typename}#%d>", get_instance_id()); }}')
    r_structs_cpp.append("")
    # doc
    _insert_doc_class_brief(typename, struct_info["doc"])
    _insert_doc_class_description(typename)

    return lines


def _get_callback_infos(callback_type: str) -> dict:
    for infos in handles.values():
        callbacks = infos["callbacks"]
        for cb in callbacks:
            if cb == callback_type:
                return callbacks[cb]
    print("ERROR unknown callback type:", callback_type)
    _print_stack_and_exit()


def _get_callback_infos_v2(callback_type: str) -> tuple[dict, str, str]:
    info: dict = []
    handle: str = ""
    method: str = ""
    for h in handles:
        callbacks = handles[h]["callbacks"]
        for cb in callbacks:
            if cb == callback_type:
                info = callbacks[cb]
                handle = h
                break
        if len(handle):
            break
    if len(handle) == 0:
        print("ERROR unknown callback type:", callback_type)
        _print_stack_and_exit()

    methods = handles[handle]["methods"]
    for m in methods:
        for arg in methods[m]["args"]:
            if _decay_eos_type(arg["type"]) == callback_type:
                method = m
                break
        if len(method):
            break
    return (info, handle, method)


def __make_callback_doc(callback_type: str) -> list[str]:
    info = _get_callback_infos(callback_type)
    ret: list[str] = []

    for arg in info["args"]:
        name = arg["name"]
        type = arg["type"]

        decayed_type = _decay_eos_type(type)
        if not _is_expanded_struct(decayed_type):
            doc: list[str] = structs[decayed_type]["doc"]
            snake_name: str = to_snake_case(name)

            if len(doc) == 1:
                l = doc[0].lstrip("\t")
                ret.append(f"{snake_name} ({decayed_type}): {l}")
            else:
                ret.append(f"{snake_name} ({decayed_type}):\n")
                for l in doc:
                    ret.append(f"\t{l}")
        else:
            arg_fields = __get_struct_fields(decayed_type)

            count_and_variant_type_fields: list[str] = __find_count_and_variant_type_fields_in_struct(decayed_type)
            for f in arg_fields:
                # 处理要跳过的字段
                if f in count_and_variant_type_fields:
                    # 跳过其中Godot不需要的字段
                    continue
                info = arg_fields[f]
                doc: list[str] = info["doc"]
                f_type = _decay_eos_type(info["type"])
                f_snake_name: str = to_snake_case(f)

                if f_type.startswith("void") and f == "ClientData":
                    continue  # 跳过这个特殊字段

                if len(doc) == 1:
                    l = doc[0].lstrip("\t")
                    ret.append(f"{f_snake_name} ({f_type}): {l}")
                else:
                    ret.append(f"{f_snake_name} ({f_type}):\n")
                    for l in info["doc"]:
                        ret.append(f"\t{l}\n")
    ret.append("")  # 插入空字符用于标记改参数必须换行
    return ret


def _insert_doc_class_description(typename: str, doc: list[str] = []):
    lines: list[str] = __get_doc_file(typename=typename)
    if len(lines) == 0:
        return

    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line = lines[i]
        indent_count = 0
        while line.startswith("\t"):
            indent_count += 1
            line = line.removeprefix("\t")
        if line.startswith(f"<description>"):
            insert_idx = i + 1
            indent_count += 1
            break

    if insert_idx < 0:
        return

    # 移除已有的文档
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</description>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]

    doc = doc.copy()
    doc.insert(0, "[b]CAUTIOUS[/b]: This document is extracted from EOS C SDK, there have some differences between the EOS C SDK and this GDScript SDK APIs.\n")
    doc.insert(1, "[b]NOTE: Keep in mind that this document is for reference only.[/b]\n")
    # doc.insert(2, "[b]CAUTIOUS[/b]: 该文档是从 EOS C SDK 中提取的，与该 GDScript SDK 的 API 存在差异。\n")
    # doc.insert(3, "[b]NOTE: 请牢记该文档仅供参考。[/b]\n")
    # 插入
    __insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    # 保存
    __store_doc_file(typename=typename, content=lines)


def _insert_doc_class_brief(typename: str, doc: list[str]):
    lines: list[str] = __get_doc_file(typename=typename)
    if len(lines) == 0:
        return

    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line = lines[i]
        indent_count = 0
        while line.startswith("\t"):
            indent_count += 1
            line = line.removeprefix("\t")
        if line.startswith(f"<brief_description>"):
            insert_idx = i + 1
            indent_count += 1
            break

    if insert_idx < 0:
        return

    # 移除已有的文档
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</brief_description>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]

    # 插入
    __insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    # 保存
    __store_doc_file(typename=typename, content=lines)


def _insert_doc_property(typename: str, prop: str, doc: list[str]):
    lines: list[str] = __get_doc_file(typename=typename)
    if len(lines) == 0:
        return

    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line = lines[i]
        indent_count = 0
        while line.startswith("\t"):
            indent_count += 1
            line = line.removeprefix("\t")
        if line.startswith(f'<member name="{prop}"'):
            insert_idx = i + 1
            indent_count += 1
            break

    if insert_idx < 0:
        return

    # 移除已有的文档
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</member>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]

    # 插入
    __insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    # 保存
    __store_doc_file(typename=typename, content=lines)


def _insert_doc_constant(typename: str, constant: str, doc: list[str]):
    lines: list[str] = __get_doc_file(typename=typename)
    if len(lines) == 0:
        return

    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line = lines[i]

        indent_count = 0
        while line.startswith("\t"):
            indent_count += 1
            line = line.removeprefix("\t")

        if line.startswith(f'<constant name="{constant}"'):
            insert_idx = i + 1
            indent_count += 1
            break

    if insert_idx < 0:
        return

    # 移除已有的文档
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</constant>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]

    # 插入
    __insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    # 保存
    __store_doc_file(typename=typename, content=lines)


def _insert_doc_method(typename: str, method: str, doc: list[str], additional_args_doc: dict[str, list[str]] = {}, additional_doc: list[str] = []):
    __insert_doc_method_like("method", typename, method, doc, additional_args_doc, additional_doc)


def _insert_doc_signal(typename: str, signal: str, doc: list[str], additional_args_doc: dict[str, list[str]] = {}, additional_doc: list[str] = []):
    __insert_doc_method_like("signal", typename, signal, doc, additional_args_doc, additional_doc)


def __insert_doc_method_like(tag: str, typename: str, name: str, doc: list[str], additional_args_doc: dict[str, list[str]], additional_doc: list[str] = []):
    lines: list[str] = __get_doc_file(typename=typename)
    if len(lines) == 0:
        return

    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line = lines[i]
        if line.lstrip("\t").startswith(f'<{tag} name="{name}"'):
            for j in range(i + 1, len(lines)):
                line = lines[j]

                indent_count = 0
                while line.startswith("\t"):
                    indent_count += 1
                    line = line.removeprefix("\t")

                if line.startswith("<description>"):
                    insert_idx = j + 1
                    indent_count += 1

                    break
            if insert_idx >= 0:
                break

    if insert_idx < 0:
        return

    # 移除已有的文档
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</description>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]

    # 插入
    __insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    if len(additional_args_doc) > 0:
        insert_idx += len(doc)
        __insert_doc_to(typename, lines, insert_idx, ["-------------- Arguments Additional Descriptions --------------\n"], indent_count)
        insert_idx += 1

        for arg in additional_args_doc:
            arg_doc = additional_args_doc[arg].copy()

            for i in range(len(arg_doc)):
                if len(arg_doc[i].strip()):
                    # 非空行添加缩进
                    arg_doc[i] = "\t" + arg_doc[i]

            arg_snake_name = to_snake_case(arg)
            if len(arg_doc) == 1:
                arg_doc[0] = f"{arg_snake_name}: " + arg_doc[0].lstrip("\t")
            else:
                arg_doc.insert(0, f"{arg_snake_name}:\n")

            __insert_doc_to(typename, lines, insert_idx, arg_doc, indent_count)
            insert_idx += len(arg_doc)

    if len(additional_doc) > 0:
        __insert_doc_to(typename, lines, insert_idx, ["-------------- Additional Descriptions --------------\n"], indent_count)
        insert_idx += 1

        additional_doc_copy = additional_doc.copy()
        additional_doc_copy.insert(0, "\n")
        __insert_doc_to(typename, lines, insert_idx, additional_doc, indent_count)
        insert_idx += len(additional_doc_copy)

    # 保存
    __store_doc_file(typename=typename, content=lines)


def __get_sorted_descending_keys(d) -> list[str]:
    ret: list[str] = []
    for k in d:
        ret.append(k)

    ret.sort(key=len, reverse=True)
    return ret


def __convert_prefix_tab(line: str) -> str:
    return line.replace("\t", "    ")


def __insert_doc_to(typename: str, lines: list[str], insert_idx: int, doc: list[str], indent_count: int) -> list[str]:
    for line in doc:
        line = __convert_prefix_tab(line)
        if len(line.strip()) != 0:
            # 非空行再加缩进
            for i in range(indent_count):
                line = "\t" + line

        # 关键词替换
        for m in __get_sorted_descending_keys(doc_keyword_map_method):
            # 替换选项类关键字
            m_options = m + "Options"
            if line.count(m_options) > 0:
                mapped: dict = f"[{doc_keyword_map_struct[m_options]}]"
                line = line.replace(m_options, mapped)
                # print("rp s: ", typename, m_options, mapped)

            # 替换回调参数信息
            m_callback_info = m + "CallbackInfo"
            if line.count(m_callback_info) > 0:
                mapped: dict = f"[{doc_keyword_map_struct[m_callback_info]}]"
                line = line.replace(m_callback_info, mapped)
                # print("rp cb_info: ", typename, m_callback_info, mapped)

            # 替换回调关键字
            splits = m.split("_")
            splits[len(splits) - 1] = "On" + splits[len(splits) - 1] + "Callback"
            m_callback = "_".join(splits)
            if line.count(m_callback) > 0:
                data: dict[str, str] = doc_keyword_map_callback[m_callback]
                klass: str = data["class"]
                name: str = data["name"]
                replace_keyword: str = ""
                if klass == typename:
                    replace_keyword = f"[signal {name}]"
                else:
                    replace_keyword = f"[signal {klass}.{name}]"
                line = line.replace(m_callback, replace_keyword)
                # print("rp cb: ", typename, m_callback, replace_keyword)

            # 替换函数关键字
            if line.count(m) > 0:
                data: dict[str, str] = doc_keyword_map_method[m]
                klass: str = data["class"]
                name: str = data["name"]
                replace_keyword: str = ""
                if klass == typename:
                    replace_keyword = f"[method {name}]"
                else:
                    replace_keyword = f"[method {klass}.{name}]"

                line = line.replace(m, replace_keyword)
                # print("rp m: ", typename, m, replace_keyword)

        for em in __get_sorted_descending_keys(doc_keyword_map_enum_member):
            if line.count(em) <= 0:
                continue

            data: dict[str, str] = doc_keyword_map_enum_member[em]
            klass: str = data["class"]
            name: str = data["name"]
            replace_keyword: str = ""
            if klass == typename:
                replace_keyword = f"[constant {name}]"
            else:
                replace_keyword = f"[constant {klass}.{name}]"

            line = line.replace(em, replace_keyword)
            # print("rp em: ", typename, em, replace_keyword)

        for e in __get_sorted_descending_keys(doc_keyword_map_enum):
            if line.count(e) <= 0:
                continue

            data: dict[str, str] = doc_keyword_map_enum[e]
            klass: str = data["class"]
            name: str = data["name"]
            replace_keyword: str = ""
            if klass == typename:
                replace_keyword = f"[enum {name}]"
            else:
                replace_keyword = f"[enum {klass}.{name}]"

            line = line.replace(e, replace_keyword)
            # print("rp e: ", typename, e, replace_keyword)

        for c in __get_sorted_descending_keys(doc_keyword_map_constant):
            if line.count(c) <= 0:
                continue

            data: dict = doc_keyword_map_constant[c]
            klass: str = data["class"]
            name: str = data["name"]
            as_method: str = data["as_method"]
            replace_keyword: str = ""
            if as_method:
                if klass == typename:
                    replace_keyword = f"[method {name}]"
                else:
                    replace_keyword = f"[method {klass}.{name}]"
            else:
                if klass == typename:
                    replace_keyword = f"[enum {name}]"
                else:
                    replace_keyword = f"[enum {klass}.{name}]"

            line = line.replace(c, replace_keyword)
            # print("rp c: ", typename, c, replace_keyword)

        for s in __get_sorted_descending_keys(doc_keyword_map_struct):
            if line.count(s) <= 0:
                continue

            mapped: dict = f"[{doc_keyword_map_struct[s]}]"
            line = line.replace(s, mapped)
            # print("rp s: ", typename, s, mapped)

        lines.insert(insert_idx, line)
        insert_idx += 1


def __get_doc_file(typename: str) -> list[str]:
    try:
        f = open(os.path.join("./doc_classes", typename) + ".xml", "r", encoding="utf-8")
        ret: list[str] = f.readlines()
        f.close()
        return ret
    except:
        return []


def __store_doc_file(typename: str, content: list[str]):
    try:
        f = open(os.path.join("./doc_classes", typename) + ".xml", "w", encoding="utf-8")
        f.writelines(content)
        f.close()
    except:
        return


def _print_stack_and_exit():
    for l in traceback.format_stack():
        print(l)
    exit(1)


def _assert(condition: bool, msg: str = ""):
    if condition:
        return
    for l in traceback.format_stack():
        print(l)
    if len(msg) > 0:
        print("Assertion failed:", msg)
    else:
        print("Assertion failed.")
    exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

# 接口代码生成器

import os

from binding_generator.config import gen_include_dir, gen_src_dir, generate_config, sdk_include_dir
from binding_generator.context import (
    handles,
    interfaces,
)
from binding_generator.generator.enum_generator import gen_enums
from binding_generator.generator.handle_generator import (
    gen_disabled_macro,
    gen_handle,
    gen_handles,
)
from binding_generator.generator.packed_result_generator import gen_packed_results
from binding_generator.generator.struct_generator import gen_structs
from binding_generator.models import Enum, FileInfo, Handle, Method, Struct
from binding_generator.utils.naming import (
    convert_handle_class_name,
    remove_backslash_of_last_line,
)
from binding_generator.utils.type import (
    assert_condition,
    is_expanded_struct,
    is_need_skip_struct,
)


def gen_files(file_base_name: str, infos: FileInfo):
    eos_header: str = file_base_name + ".h"
    eos_types_header: str = file_base_name + ".h"
    if os.path.exists(os.path.join(sdk_include_dir, file_base_name + "_types.h")):
        eos_types_header = file_base_name + "_types.h"
    if not os.path.exists(os.path.join(sdk_include_dir, eos_header)):
        eos_header = eos_types_header

    if file_base_name == "eos_sdk":
        file_base_name = "eos_platform"

    enums_inline_file: str = os.path.join(gen_include_dir, "enums", file_base_name + ".enums.inl")

    structs_h_file: str = os.path.join(gen_include_dir, "structs", file_base_name + ".structs.h")
    structs_cpp_file: str = os.path.join(gen_src_dir, "structs", file_base_name + ".structs.cpp")

    packed_result_h_file: str = os.path.join(gen_include_dir, "packed_results", file_base_name + ".packed_results.h")
    packed_result_cpp_file: str = os.path.join(gen_src_dir, "packed_results", file_base_name + ".packed_results.cpp")

    handles_h_file: str = os.path.join(gen_include_dir, "handles", file_base_name + ".handles.h")
    handles_cpp_file: str = os.path.join(gen_src_dir, "handles", file_base_name + ".handles.cpp")

    interface_handle_h_file: str = os.path.join(gen_include_dir, "interfaces", file_base_name + "_interface.h")
    interface_handle_cpp_file: str = os.path.join(gen_src_dir, "interfaces", file_base_name + "_interface.cpp")

    methods: dict[str, Method] = {}
    for m in infos.methods:
        methods[m] = infos.methods[m]
    for h in infos.handles:
        for m in infos.handles[h].methods:
            methods[m] = infos.handles[h].methods[m]

    interface_handle: str = ""
    sub_handles: dict[str, Handle] = {}
    for h in infos.handles:
        if h in ["EOS", "EOS_HAntiCheatCommon"]:
            interface_handle = h
            continue
        if h.removeprefix("EOS_H") in interfaces:
            interface_handle = h
            continue
        sub_handles[h] = infos.handles[h]

    macro_suffix: str = convert_handle_class_name(interface_handle)

    packed_result_h_lines: list[str] = []
    packed_result_cpp_lines: list[str] = [f"#include <packed_results/{file_base_name + '.packed_results.h'}>"]
    if len(sub_handles):
        packed_result_cpp_lines.append(f"#include <handles/{file_base_name + '.handles.h'}>")

    if len(interface_handle):
        packed_result_cpp_lines.append(f"#include <interfaces/{file_base_name + '_interface.h'}>")
    else:
        packed_result_cpp_lines.append(f"#include <{'eos_common_interface.h'}>")

    packed_result_cpp_lines.append("")
    packed_result_cpp_lines.append("using namespace godot::eos::internal;")
    packed_result_cpp_lines.append("namespace godot::eos {")
    has_packed_result: bool = gen_packed_results(
        file_base_name,
        eos_types_header,
        macro_suffix,
        methods,
        packed_result_h_lines,
        packed_result_cpp_lines,
    )
    packed_result_cpp_lines.append("} // namespace godot::eos")
    packed_result_cpp_lines.append("")
    if has_packed_result:
        f = open(packed_result_h_file, "w")
        f.write("\n".join(packed_result_h_lines))
        f.close()
        f = open(packed_result_cpp_file, "w")
        f.write("\n".join(packed_result_cpp_lines))
        f.close()
    else:
        if os.path.exists(packed_result_h_file):
            os.remove(packed_result_h_file)
        if os.path.exists(packed_result_cpp_file):
            os.remove(packed_result_cpp_file)

    structs_to_gen: dict[str, Struct] = {}
    for st in infos.structs:
        if is_expanded_struct(st):
            continue
        if is_need_skip_struct(st):
            continue
        if infos.structs[st].deprecated:
            continue
        structs_to_gen[st] = infos.structs[st]

    has_structs: bool = len(structs_to_gen) > 0

    if len(sub_handles):
        handles_cpp_lines: list[str] = [f"#include <handles/{file_base_name + '.handles.h'}>"]
        handles_cpp_lines.append(f"#include <{file_base_name}.h>")

        if len(interface_handle):
            handles_cpp_lines.append(f"#include <interfaces/{file_base_name + '_interface.h'}>")
        else:
            handles_cpp_lines.append(f"#include <interfaces/{'eos_common_interface.h'}>")

        handles_cpp_lines.append("")
        additional_include_lines: list[str] = []
        if has_packed_result:
            additional_include_lines.append(f"#include <packed_results/{file_base_name + '.packed_results.h'}>")
        additional_include_lines.append(f"#include <{eos_types_header}>")
        additional_include_lines.append("#include <core/utils.h>")

        if generate_config.assume_only_one_local_user and file_base_name == "eos_common":
            additional_include_lines.append("")
            additional_include_lines.append("#define EOS_ASSUME_ONLY_ONE_USER")

        handles_hpp_lines: list[str] = gen_handles(interface_handle, additional_include_lines, sub_handles, handles_cpp_lines, file_base_name, has_structs)

        if len(handles_hpp_lines):
            f = open(handles_h_file, "w")
            f.write("\n".join(handles_hpp_lines))
            f.close()

            f = open(handles_cpp_file, "w")
            f.write("\n".join(handles_cpp_lines))
            f.close()
    else:
        if os.path.exists(handles_h_file):
            os.remove(handles_h_file)
        if os.path.exists(handles_cpp_file):
            os.remove(handles_cpp_file)

    if has_structs:
        structs_cpp_lines: list[str] = [f"#include <structs/{file_base_name + '.structs.h'}>"]
        if len(sub_handles) and len(handles_hpp_lines):
            structs_cpp_lines.append(f"#include <handles/{file_base_name + '.handles.h'}>")
        if file_base_name.startswith("eos_titlestorage") or file_base_name.startswith("eos_playerdatastorage"):
            structs_cpp_lines.append("#include <core/file_transfer.inl>")
        if file_base_name == "eos_platform":
            structs_cpp_lines.append("#include <handles/eos_integratedplatform.handles.h>")

        if len(interface_handle):
            structs_cpp_lines.append(f"#include <interfaces/{file_base_name + '_interface.h'}>")
        else:
            structs_cpp_lines.append(f"#include <interfaces/{'eos_common_interface.h'}>")

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

        f = open(structs_h_file, "w")
        f.write("\n".join(structs_h_lines))
        f.close()

        f = open(structs_cpp_file, "w")
        f.write("\n".join(structs_cpp_lines))
        f.close()
    else:
        if os.path.exists(structs_h_file):
            os.remove(structs_h_file)
        if os.path.exists(structs_cpp_file):
            os.remove(structs_cpp_file)

    if len(infos.enums):
        print(f"[interface_generator] {file_base_name} 枚举: {list(infos.enums.keys())}")
    if len(infos.methods):
        print(f"[interface_generator] {file_base_name} 方法: {list(infos.methods.keys())}")
    if len(infos.callbacks):
        print(f"[interface_generator] {file_base_name} 回调: {list(infos.callbacks.keys())}")

    if len(interface_handle) <= 0:
        if file_base_name not in ["eos_logging"]:
            print(f"[interface_generator] 接口 '{file_base_name}' 没有对应的句柄类型")
        return

    enums: dict[str, Enum] = {}
    for e in infos.enums:
        enums[e] = infos.enums[e]
    for h in infos.handles:
        handle_enums: dict[str, Enum] = infos.handles[h].enums
        for e in handle_enums:
            enums[e] = handle_enums[e]
    if len(enums):
        enums_inl: str = gen_enums(macro_suffix, interface_handle, enums)
        f = open(enums_inline_file, "w")
        f.write(enums_inl)
        f.close()

    disabled_macro: str = gen_disabled_macro(interface_handle)
    interface_handle_h_lines: list[str] = []
    interface_handle_cpp_lines: list[str] = []
    interface_handle_h_lines.append("#pragma once")

    if len(disabled_macro):
        interface_handle_h_lines.append(f"#ifndef {disabled_macro}")
        interface_handle_cpp_lines.append(f"#ifndef {disabled_macro}")

    interface_handle_cpp_lines.append(f"#include <{eos_header}>")
    interface_handle_cpp_lines.append(f"#include <interfaces/{file_base_name + '_interface.h'}>")
    interface_handle_cpp_lines.append("")
    if file_base_name.startswith("eos_playerdatastorage") or file_base_name.startswith("eos_titlestorage"):
        interface_handle_cpp_lines.append("#include <core/file_transfer.inl>")
        interface_handle_cpp_lines.append("")

    for m in infos.handles[interface_handle].methods:
        if m.endswith("Interface"):
            splits: list[str] = m.split("_")
            assert_condition(len(splits) == 3)
            owner_handle_type: str = splits[1]
            interface: str = splits[2].removesuffix("Interface").removeprefix("Get")
            interface_low: str = interface.lower()

            interface_handle_type: str = ""
            if owner_handle_type == "Platform":
                interface_handle_type = "EOS_H" + interface
            else:
                interface_handle_type = "EOS_H" + owner_handle_type + interface
                owner_sub_handles: dict[str, str] = handles["EOS_H" + owner_handle_type].sub_handles
                owner_sub_handles[interface_handle_type] = m
                handles["EOS_H" + owner_handle_type].sub_handles = owner_sub_handles

            _disabled_macro: str = gen_disabled_macro(interface_handle_type)

            assert_condition(len(_disabled_macro) > 0)
            if interface_low != "rtc" and (interface_low.startswith("rtc") or owner_handle_type == "RTC"):
                interface_low = "rtc_" + interface_low.removeprefix("rtc")

            interface_handle_cpp_lines.append(f"#ifndef {_disabled_macro}")
            interface_handle_cpp_lines.append(f"#include <interfaces/eos_{interface_low}_interface.h>")
            interface_handle_cpp_lines.append(f"#endif // {_disabled_macro}")
    interface_handle_cpp_lines.append("")

    if file_base_name == "eos_common":
        interface_handle_h_lines.append("#include <eos_types.h>")
        interface_handle_h_lines.append("#include <eos_logging.h>")
        interface_handle_h_lines.append("#include <eos_version.h>")
        interface_handle_h_lines.append("#include <godot_cpp/classes/object.hpp>")
        interface_handle_h_lines.append("#include <godot_cpp/core/binder_common.hpp>")
        interface_handle_h_lines.append("#include <core/utils.h>")
    elif file_base_name == "eos_anticheatcommon":
        interface_handle_h_lines.append('#include "eos_common_interface.h"')
    elif file_base_name.startswith("eos_anticheat"):
        interface_handle_h_lines.append('#include "eos_anticheatcommon_interface.h"')
    else:
        interface_handle_h_lines.append('#include "eos_common_interface.h"')

    if file_base_name.startswith("eos_platform"):
        interface_handle_h_lines.append("#include <godot_cpp/classes/engine.hpp>")
        interface_handle_h_lines.append("#include <godot_cpp/classes/main_loop.hpp>")
    interface_handle_h_lines.append("")

    if len(enums):
        interface_handle_h_lines.append(f"#include <enums/{file_base_name + '.enums.inl'}>")
    if len(structs_to_gen):
        interface_handle_h_lines.append(f"#include <structs/{file_base_name + '.structs.h'}>")
    if has_packed_result:
        interface_handle_h_lines.append(f"#include <packed_results/{file_base_name + '.packed_results.h'}>")
    if len(sub_handles):
        interface_handle_h_lines.append(f"#include <handles/{file_base_name + '.handles.h'}>")

    interface_handle_h_lines.append("")
    interface_handle_cpp_lines.append("using namespace godot::eos::internal;")
    interface_handle_cpp_lines.append("namespace godot::eos {")

    interface_handle_h_lines += gen_handle(
        interface_handle,
        infos.handles[interface_handle],
        convert_handle_class_name("EOS") if file_base_name == "eos_common" else macro_suffix,
        interface_handle_cpp_lines,
        [],
        True,
    )
    remove_backslash_of_last_line(interface_handle_h_lines)
    interface_handle_cpp_lines.append("} // namespace godot::eos")
    interface_handle_cpp_lines.append("")

    interface_handle_h_lines.append(f"#define EOS_REGISTER_{macro_suffix}\\")
    interface_handle_h_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS(godot::eos::{convert_handle_class_name(interface_handle)})\\")
    if len(structs_to_gen):
        interface_handle_h_lines.append(f"\tREGISTER_DATA_CLASSES_OF_{macro_suffix}()\\")
    if has_packed_result:
        interface_handle_h_lines.append(f"\tREGISTER_PACKED_RESULTS_{macro_suffix}()\\")
    if len(sub_handles):
        interface_handle_h_lines.append(f"\tREGISTER_HANDLES_OF_{macro_suffix}()\\")

    remove_backslash_of_last_line(interface_handle_h_lines)

    interface_handle_h_lines.append("")
    if len(disabled_macro):
        interface_handle_h_lines.append(f"#else // {disabled_macro}")
        interface_handle_h_lines.append(f"#define EOS_REGISTER_{macro_suffix}")
        interface_handle_h_lines.append(f"#endif // {disabled_macro}")
        interface_handle_h_lines.append("")

        interface_handle_cpp_lines.append(f"#endif // {disabled_macro}")
        interface_handle_cpp_lines.append("")

    f = open(interface_handle_h_file, "w")
    f.write("\n".join(interface_handle_h_lines))
    f.close()

    f = open(interface_handle_cpp_file, "w")
    f.write("\n".join(interface_handle_cpp_lines))
    f.close()

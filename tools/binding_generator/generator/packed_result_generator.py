# 打包结果类型代码生成器

from binding_generator.context import handles
from binding_generator.doc.doc_processor import (
    insert_doc_class_brief,
    insert_doc_class_description,
)
from binding_generator.models import Arg, Method
from binding_generator.utils.common import print_stack_and_exit
from binding_generator.utils.naming import (
    convert_enum_type,
    convert_handle_class_name,
    convert_method_name,
    convert_result_type,
    convert_to_struct_class,
    decay_eos_type,
    is_out_param_name,
    remove_backslash_of_last_line,
    strip_out_param_prefix,
    to_snake_case,
)
from binding_generator.utils.type import (
    get_enum_owned_interface,
    is_arr_field,
    is_audio_frames_type,
    is_enum_flags_type,
    is_enum_type,
    is_handle_arr_type,
    is_handle_type,
    is_internal_struct_arr_field,
    is_need_skip_method,
    is_pure_handle_type,
    is_socket_id_type,
    is_str_arr_type,
    is_str_type,
    is_struct_type,
    remap_type,
)


def gen_packed_results(
    file_base_name: str,
    types_include_file: str,
    register_macro_suffix: str,
    methods: dict[str, Method],
    r_h_lines: list[str],
    r_cpp_lines: list[str],
) -> bool:
    ret: bool = False
    r_h_lines.append("#pragma once")
    r_h_lines.append("")
    r_h_lines.append("#include <core/eos_packed_result.h>")
    r_h_lines.append(f"#include <{types_include_file}>")
    r_h_lines.append(f"#include <structs/{file_base_name + '.structs.h'}>")
    r_h_lines.append("")
    r_h_lines.append("namespace godot::eos {")

    register_lines: list[str] = [f"#define REGISTER_PACKED_RESULTS_{register_macro_suffix}()\\"]
    for method in methods:
        if method.endswith("Release"):
            continue
        if is_need_skip_method(method):
            continue
        if methods[method].deprecated:
            continue
        if len(gen_packed_result_type(method, methods[method], r_h_lines, r_cpp_lines, register_lines, [])):
            ret = True

    r_h_lines.append("")
    r_h_lines += register_lines
    remove_backslash_of_last_line(r_h_lines)

    r_h_lines.append("")
    r_h_lines.append("} // namespace godot::eos")
    r_h_lines.append("")
    return ret


def gen_packed_result_type(
    method_name: str,
    method_info: Method,
    r_h_lines: list[str],
    r_cpp_lines: list[str],
    r_register_lines: list[str],
    r_need_convert_to_return_value: list[bool],
    get_type_name_only: bool = False,
    r_remapped_result_type: list[str] = [],
) -> str:
    out_args: list[Arg] = []
    for i in range(len(method_info.args)):
        arg_name: str = method_info.args[i].name
        arg_type: str = method_info.args[i].type
        if is_out_param_name(arg_name) and arg_type.endswith("*"):
            out_args.append(method_info.args[i])
    if len(out_args) <= 0:
        return ""
    if len(method_info.return_type) <= 0 or method_info.return_type == "void":
        if len(out_args) == 1:
            r_need_convert_to_return_value.append(True)
            return ""
        if len(out_args) == 2:
            if (out_args[0].type == "char*" and out_args[1].type.endswith("int32_t*") and out_args[1].name.endswith("Length")) or (
                out_args[0].type == "void*" and out_args[1].type.endswith("int32_t*")
            ):
                r_need_convert_to_return_value.append(True)
                return ""

    if method_info.return_type == "EOS_EResult" and len(out_args) == 1:
        arg_name = out_args[0].name
        arg_type = out_args[0].type
        decayed_type: str = decay_eos_type(arg_type)
        if is_handle_type(decayed_type) and not is_handle_arr_type(arg_type, arg_name):
            r_remapped_result_type.append(f"Ref<{convert_handle_class_name(decayed_type)}>")
            return ""
        if is_struct_type(decayed_type):
            r_remapped_result_type.append(f"Ref<{convert_to_struct_class(decayed_type)}>")
            return ""
        if arg_type == "char*":
            r_need_convert_to_return_value.append(True)
            return ""

    if method_info.return_type == "EOS_EResult" and len(out_args) == 2:
        if out_args[0].type == "char*" and (out_args[1].type.endswith("int32_t*") or out_args[1].type.endswith("uint32_t*")) and out_args[1].name.endswith("Length"):
            r_need_convert_to_return_value.append(True)
            return ""

    typename: str = convert_result_type(method_name)
    if get_type_name_only:
        return typename

    members_lines: list[str] = []
    setget_lines: list[str] = []
    bind_lines: list[str] = []
    i: int = 0
    while i < len(out_args):
        arg: Arg = out_args[i]
        arg_type = arg.type
        arg_name = arg.name
        decayed_type = decay_eos_type(arg_type)
        snake_name: str = to_snake_case(strip_out_param_prefix(arg_name))
        if is_handle_arr_type(arg_type, arg_name):
            print(f"[packed_result_generator] 不支持的句柄数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")

            print_stack_and_exit()
        elif is_handle_type(decayed_type):
            handle_class: str = convert_handle_class_name(decayed_type)
            members_lines.append(f"\tRef<RefCounted> {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET_TYPED({snake_name}, Ref<class {handle_class}>)")
            r_cpp_lines.append(f"_DEFINE_SETGET_TYPED({typename}, {snake_name}, Ref<{handle_class}>)")
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_name}, {handle_class})")
        elif is_struct_type(decayed_type):
            members_lines.append(f"\tRef<{convert_to_struct_class(decayed_type)}> {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_name}, {convert_to_struct_class(decayed_type)})")
        elif is_pure_handle_type(decayed_type):
            members_lines.append(f"\t{remap_type(decayed_type)} {snake_name}{{ 0 }};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_name}, {remap_type(arg_type).removesuffix('*')})")
        elif is_enum_type(decayed_type):
            enum_owner: str = get_enum_owned_interface(decayed_type)
            members_lines.append(f"\t{decayed_type} {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP_ENUM({snake_name}, {enum_owner}, {convert_enum_type(decayed_type)})")
        elif is_socket_id_type(decayed_type, arg_name):
            members_lines.append(f"\tString {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP({snake_name})")
        elif is_str_type(arg_type, arg_name):
            print(f"[packed_result_generator] 不支持的字符串类型输出参数: 方法 '{method_name}', 参数 '{arg_name}'")

            print_stack_and_exit()
        elif is_str_arr_type(arg_type, arg_name):
            print(f"[packed_result_generator] 不支持的字符串数组类型输出参数: 方法 '{method_name}', 参数 '{arg_name}'")

            print_stack_and_exit()
        elif arg_type == "char*" and (i + 1) < len(out_args) and out_args[i + 1].type.endswith("int32_t*") and out_args[i + 1].name.endswith("Length"):
            members_lines.append(f"\tString {snake_name};")
            setget_lines.append(f"\t_DECLARE_SETGET({snake_name})")
            r_cpp_lines.append(f"_DEFINE_SETGET({typename}, {snake_name})")
            bind_lines.append(f"\t_BIND_PROP({snake_name})")
            i += 1
        elif arg_type == "void*" and (i + 1) <= len(out_args) and out_args[i + 1].type.endswith("int32_t*"):
            if out_args[i + 1].name != "OutBytesWritten":
                print(f"[packed_result_generator] 警告: 方法 '{method_name}' 的 void* 输出参数的长度字段名不是 'OutBytesWritten'")
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
        elif is_arr_field(arg_type, arg_name):
            print(f"[packed_result_generator] 不支持的数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")

            print_stack_and_exit()
        elif is_internal_struct_arr_field(arg_type, arg_name):
            print(f"[packed_result_generator] 不支持的结构体数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")

            print_stack_and_exit()
        elif is_audio_frames_type(arg_type, arg_name):
            print(f"[packed_result_generator] 不支持的音频帧数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")

            print_stack_and_exit()
        elif is_enum_flags_type(arg_type):
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

    r_h_lines.append(f"class {typename} : public EOSPackedResult {{")
    r_h_lines.append(f"\tGDCLASS({typename}, EOSPackedResult)")
    r_h_lines.append("public:")
    if method_info.return_type == "EOS_EResult":
        r_h_lines.append("\tEOS_EResult result_code{ EOS_EResult::EOS_InvalidParameters };")
    else:
        print(f"[packed_result_generator] 不支持为方法 '{method_name}' 生成打包结果类型: 返回类型 '{method_info.return_type}' 不是 EOS_EResult")
    r_h_lines += members_lines
    r_h_lines.append("")
    r_h_lines.append("public:")
    if method_info.return_type == "EOS_EResult":
        r_h_lines.append("\t_DECLARE_SETGET(result_code);")
        r_cpp_lines.append(f"_DEFINE_SETGET({typename}, result_code)")
    r_h_lines += setget_lines
    r_h_lines.append("")
    r_h_lines.append("protected:")
    r_h_lines.append("\tstatic void _bind_methods();")
    r_h_lines.append("};")
    r_h_lines.append("")

    r_cpp_lines.append(f"void {typename}::_bind_methods() {{")
    r_cpp_lines.append(f"\t_BIND_BEGIN({typename});")
    if method_info.return_type == "EOS_EResult":
        r_cpp_lines.append(f"\t_BIND_PROP_ENUM(result_code, EOS_Common, {convert_enum_type('EOS_EResult')})")
    r_cpp_lines += bind_lines
    r_cpp_lines.append("\t_BIND_END();")
    r_cpp_lines.append("}")
    r_cpp_lines.append("")

    r_register_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS(godot::eos::{typename})\\")

    handle: str = _find_method_handle_type(method_name)
    insert_doc_class_brief(
        typename,
        [f"The result type of [method {convert_handle_class_name(handle)}.{convert_method_name(method_name)}].\n"],
    )
    insert_doc_class_description(typename)
    return typename


def _find_method_handle_type(method_name: str) -> str:
    for h in handles:
        for m in handles[h].methods:
            if m == method_name:
                return h
    print_stack_and_exit(f"[packed_result_generator] 方法 '{method_name}' 没有对应的句柄类型")

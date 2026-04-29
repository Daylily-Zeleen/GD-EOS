# 句柄类代码生成器

import re

from binding_generator.config import generate_config
from binding_generator.context import (
    callback_to_method,
    handles,
)
from binding_generator.doc.doc_processor import (
    insert_doc_class_brief,
    insert_doc_class_description,
    insert_doc_constant,
    insert_doc_method,
    insert_doc_signal,
    make_callback_doc,
)
from binding_generator.generator.packed_result_generator import gen_packed_result_type
from binding_generator.models import Arg, Callback, Handle, Method, StructField
from binding_generator.utils.naming import (
    convert_constant_as_method_name,
    convert_constant_name,
    convert_enum_type,
    convert_handle_class_name,
    convert_method_name,
    convert_to_signal_name,
    convert_to_struct_class,
    decay_eos_type,
    is_out_param_name,
    remove_backslash_of_last_line,
    strip_out_param_prefix,
    to_snake_case,
)
from binding_generator.utils.common import assert_condition, print_stack_and_exit
from binding_generator.utils.type import (
    find_count_and_variant_type_fields_in_struct,
    find_count_field,
    get_api_latest_macro,
    get_base_class,
    get_callback_infos,
    get_enum_owned_interface,
    get_gd_type_of_local_user_id,
    get_login_interface_of_local_user_id,
    get_str_arr_element_type,
    get_str_result_max_length_macro,
    get_struct_fields,
    has_str_result_max_length_macro,
    is_api_version_field,
    is_arr_field,
    is_audio_frames_type,
    is_base_handle_type,
    is_callback_type,
    is_client_data,
    is_client_data_field,
    is_enum_flags_type,
    is_enum_type,
    is_expanded_struct,
    is_handle_arr_type,
    is_handle_type,
    is_internal_platform_specific_field,
    is_internal_struct_arr_field,
    is_internal_struct_field,
    is_local_user_id,
    is_method_input_only_struct,
    is_need_skip_callback,
    is_need_skip_method,
    is_nullable_float_pointer_field,
    is_pure_handle_type,
    is_requested_channel_ptr_field,
    is_socket_id_type,
    is_str_arr_type,
    is_str_type,
    is_string_constant,
    is_struct_ptr,
    is_struct_type,
    is_variant_union_type,
    need_check_null_local_user_id_struct,
    need_ignore_local_user_id_struct,
    remap_type,
)


def _collect_forward_declared_struct_types(p_handles: dict[str, Handle]) -> set[str]:
    struct_types: set[str] = set()
    for h in p_handles:
        if not is_handle_type(h):
            continue
        for m_name in p_handles[h].methods:
            method: Method = p_handles[h].methods[m_name]
            for arg in method.args:
                decayed: str = decay_eos_type(arg.type)
                if is_struct_type(decayed):
                    if is_internal_struct_arr_field(arg.type, arg.name):
                        struct_types.add(convert_to_struct_class(decayed))
                    if is_out_param_name(arg.name) and not is_expanded_struct(decayed):
                        struct_types.add(convert_to_struct_class(decayed))
                    if is_expanded_struct(decayed):
                        fields: dict[str, StructField] = get_struct_fields(decayed)
                        for field_name in fields:
                            field: StructField = fields[field_name]
                            if is_internal_struct_arr_field(field.type, field_name, decayed):
                                struct_types.add(convert_to_struct_class(decay_eos_type(field.type)))
    return struct_types


def gen_handles(
    interface_handle_class: str,
    additional_include_lines: list[str],
    p_handles: dict[str, Handle],
    r_cpp_lines: list[str],
    file_base_name: str = "",
    has_structs: bool = False,
) -> list[str]:
    register_lines: list[str] = [f"#define REGISTER_HANDLES_OF_{convert_handle_class_name(interface_handle_class)}()\\"]

    h_lines: list[str] = ["#pragma once"]

    h_lines.append("#include <godot_cpp/classes/ref_counted.hpp>")
    h_lines.append("")
    if len(additional_include_lines):
        h_lines += additional_include_lines
        h_lines.append("")

    forward_declared_types: set[str] = _collect_forward_declared_struct_types(p_handles)
    if len(forward_declared_types):
        h_lines.append("namespace godot::eos {")
        for t in sorted(forward_declared_types):
            h_lines.append(f"class {t};")
        h_lines.append("} // namespace godot::eos")
        h_lines.append("")

    if file_base_name and has_structs:
        r_cpp_lines.append(f"#include <structs/{file_base_name}.structs.h>")

    r_cpp_lines.append("#include <core/utils.h>")
    r_cpp_lines.append("using namespace godot::eos::internal;")
    r_cpp_lines.append("namespace godot::eos {")
    for h in p_handles:
        if not is_handle_type(h):
            continue
        h_lines += gen_handle(h, p_handles[h], convert_handle_class_name(h), r_cpp_lines, register_lines)
    remove_backslash_of_last_line(register_lines)

    r_cpp_lines.append("} // namespace godot::eos")
    r_cpp_lines.append("")

    register_lines.append("")

    return h_lines + register_lines


def gen_handle(
    handle_name: str,
    infos: Handle,
    macro_suffix: str,
    r_cpp_lines: list[str],
    r_register_lines: list[str],
    need_singleton: bool = False,
) -> list[str]:
    base_handle_type: bool = is_base_handle_type(handle_name)
    base_class: str = get_base_class(handle_name)
    if base_handle_type:
        need_singleton = False

    method_infos: dict[str, Method] = infos.methods
    callback_infos: dict[str, Callback] = infos.callbacks

    klass: str = convert_handle_class_name(handle_name)
    release_method: str = ""

    if generate_config.assume_only_one_local_user and handle_name in ["EOS_ProductUserId", "EOS_EpicAccountId"]:
        r_cpp_lines.append(f"_CODE_SNIPPET_LOCAL_ID_DEFINE({klass})")

    if need_singleton:
        r_cpp_lines.append(f"{klass} *{klass}::singleton{{ nullptr }};")

    method_bind_lines: list[str] = []
    method_define_lines: list[str] = []

    notifies_member_lines: list[str] = []
    setup_notifies_lines: list[str] = []
    remove_notifies_lines: list[str] = []

    for method in method_infos:
        if method.endswith("Release"):
            release_method = method
            break

    skip_remove_notify_methods: list[str] = []
    methods_name_list: list[str] = []
    for m in method_infos:
        methods_name_list.append(m)
    methods_name_list.sort()

    need_notification_header: bool = False
    need_signal_callback_list: list[str] = []
    for method in methods_name_list:
        if method.endswith("Release"):
            continue
        if is_need_skip_method(method):
            continue
        if method.endswith("Interface"):
            continue

        method_info: Method = method_infos[method]
        if method_info.deprecated:
            continue
        if "AddNotify" in method:
            options_arg: Arg = method_info.args[1]
            options_type: str = options_arg.type
            decayed_options_type: str = decay_eos_type(options_type)
            if is_struct_type(decayed_options_type) and options_arg.name.endswith("Options"):
                options_fields: dict[str, StructField] = get_struct_fields(decayed_options_type)

                valid_field_count: int = 0
                for field in options_fields:
                    if is_internal_platform_specific_field(field) or options_fields[field].deprecated:
                        continue
                    valid_field_count += 1

                if valid_field_count == 1 and "ApiVersion" in options_fields:
                    cb_type: str = _get_callback_type_of_method(method_info)
                    assert_condition(len(cb_type) > 0, f"{method} - {cb_type}")
                    need_signal_callback_list.append(cb_type)
                    _make_notify_code(
                        handle_name,
                        klass,
                        method,
                        method_info,
                        decayed_options_type,
                        notifies_member_lines,
                        setup_notifies_lines,
                        remove_notifies_lines,
                    )

                    for m in method_infos:
                        if m == method:
                            continue
                        if method.replace("AddNotify", "RemoveNotify") in m:
                            skip_remove_notify_methods.append(m)
                    continue

        if "RemoveNotify" in method:
            continue

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
            need_notification_header = True
        else:
            cb_type: str = _get_callback_type_of_method(method_info)
            if len(cb_type) > 0:
                need_signal_callback_list.append(cb_type)

    method_define_lines.append("")
    method_define_lines.append("\tString _to_string() const;")
    method_define_lines.append("")

    if klass == "EOS":
        method_define_lines.append("\t_EOS_GET_VERSION()")
        method_define_lines.append("\t_CODE_SNIPPET_DECLARE_LAST_RESULT_CODE()")
        method_define_lines.append("")

    has_string_constants: bool = False
    for constant in infos.constants:
        if infos.constants[constant].deprecated:
            continue
        const_value: str = infos.constants[constant].value
        if is_string_constant(const_value):
            method_define_lines.append(f"\tstatic String {convert_constant_as_method_name(constant)}() {{ return {constant}; }}")
            has_string_constants = True
    if has_string_constants:
        method_define_lines.append("")

    if need_singleton:
        r_cpp_lines.append(f"{klass}::{klass}() {{")
        r_cpp_lines.append("\tERR_FAIL_COND(singleton!= nullptr);")
        r_cpp_lines.append("\tsingleton = this;")
        r_cpp_lines.append("}")
        r_cpp_lines.append("")

    if len(release_method) or len(remove_notifies_lines):
        r_cpp_lines.append(f"{klass}::~{klass}() {{")
        if len(remove_notifies_lines) or len(release_method):
            r_cpp_lines.append("\tif (m_handle) {")
            r_cpp_lines.append("\t\tHandleCache::remove(m_handle);")
            for line in remove_notifies_lines:
                r_cpp_lines.append("\t" + line)
            if len(release_method):
                r_cpp_lines.append(f"\t\t{release_method}(m_handle);")
            r_cpp_lines.append("\t}")
        if need_singleton:
            r_cpp_lines.append("\tERR_FAIL_COND(singleton != this);")
            r_cpp_lines.append("\tsingleton = nullptr;")
            if handle_name == "EOS_HPlatform":
                r_cpp_lines.append("\tEOS_Shutdown();")
        r_cpp_lines.append("}")

    if not base_handle_type:
        r_cpp_lines.append(f"void {klass}::set_handle({handle_name} p_handle) {{")
        r_cpp_lines.append("\tERR_FAIL_COND(m_handle); m_handle = p_handle;")

        if len(handles[handle_name].sub_handles):
            for sub_handle in handles[handle_name].sub_handles:
                get_method = handles[handle_name].sub_handles[sub_handle]
                sub_handle_snake_name = to_snake_case(sub_handle.removeprefix("EOS_H")) + "_handle"
                r_cpp_lines.append(f"#ifndef {gen_disabled_macro(sub_handle)}")
                r_cpp_lines.append("\tif (m_handle) {")
                r_cpp_lines.append(f"\t\tauto {sub_handle_snake_name} = {get_method}(m_handle);")
                r_cpp_lines.append(f"\t\t{convert_handle_class_name(sub_handle)}::get_singleton()->set_handle({sub_handle_snake_name});")
                r_cpp_lines.append("\t}")
                r_cpp_lines.append(f"#endif // {gen_disabled_macro(sub_handle)}")

        if len(setup_notifies_lines):
            for line in setup_notifies_lines:
                r_cpp_lines.append(line)
        r_cpp_lines.append("}")
        r_cpp_lines.append("")

    ret: list[str] = []
    if need_notification_header:
        ret.append("#include <core/eos_notification.h>")

    inherits = f"public {base_class}"
    if base_class in [convert_handle_class_name("EOS_HAntiCheatCommon")]:
        base_class = "Object"

    ret.append("namespace godot::eos {")
    ret.append(f"class {klass} : {inherits} {{")
    ret.append(f"\tGDCLASS({klass}, {base_class})")
    ret.append("")
    if not base_handle_type:
        ret.append(f"\t{handle_name} m_handle{{ nullptr }};")
        ret.append("")
    if len(notifies_member_lines):
        ret += notifies_member_lines
        ret.append("")
    if need_singleton:
        ret.append(f"\tstatic {klass} *singleton;")
        ret.append("")
    if klass == "EOS":
        ret.append("public:")
        ret.append("\tstatic Callable &get_log_message_callback() {{ static Callable ret; return ret; }}")

    ret.append("protected:")
    ret.append("\tstatic void _bind_methods();")
    ret.append("")
    ret.append("public:")
    if len(infos.enums):
        ret.append(f"\t_USING_ENUMS_{macro_suffix}()")
        ret.append("")
    if need_singleton:
        ret.append(f"\tstatic {klass} *get_singleton() {{ if (singleton == nullptr) {{singleton = memnew({klass});}} return singleton; }}")
        ret.append("")
    if need_singleton:
        ret.append(f"\t{klass}();")
    if len(release_method) or len(remove_notifies_lines):
        ret.append(f"\tvirtual ~{klass}() override;")
    if not base_handle_type:
        ret.append(f"\tvoid set_handle({handle_name} p_handle);")
        ret.append(f"\t{handle_name} get_handle() const {{ return m_handle; }}")
        ret.append("")

    ret += method_define_lines

    ret.append("")
    if handle_name == "EOS_HPlatform":
        ret.append("\t_EOS_PLATFORM_SETUP_TICK()")

    if generate_config.assume_only_one_local_user and handle_name in [
        "EOS_ProductUserId",
        "EOS_EpicAccountId",
    ]:
        ret.append(f"\t_CODE_SNIPPET_LOCAL_ID_DECLARE({klass})")

    ret.append("};")
    ret.append("} // namespace godot::eos")

    if len(infos.enums):
        ret.append(f"_CAST_ENUMS_{macro_suffix}()")
    ret.append("")

    r_cpp_lines.append(f'String {klass}::_to_string() const {{ return vformat("<{klass}#%d>", get_instance_id()); }}')
    r_cpp_lines.append("")

    r_cpp_lines.append(f"void {klass}::_bind_methods() {{")
    r_cpp_lines += method_bind_lines
    for callback in callback_infos:
        if is_need_skip_callback(callback):
            continue
        if callback_infos[callback].deprecated:
            continue
        if callback == "EOS_LogMessageFunc":
            continue
        if callback in need_signal_callback_list:
            method_name: str = callback_to_method.get(callback, "")
            _gen_callback(callback, handle_name, method_name, r_cpp_lines, True)
    if len(infos.enums):
        r_cpp_lines.append(f"\t_BIND_ENUMS_{macro_suffix}()")
    for constant in infos.constants:
        if infos.constants[constant].deprecated:
            continue
        doc = infos.constants[constant].doc
        if is_string_constant(infos.constants[constant].value):
            converted_method_name: str = convert_constant_as_method_name(constant)
            r_cpp_lines.append(f'\tClassDB::bind_static_method(get_class_static(), D_METHOD("{converted_method_name}"), &{klass}::{converted_method_name});')
            insert_doc_method(klass, converted_method_name, doc, {})
        else:
            r_cpp_lines.append(f'\t_BIND_CONSTANT({constant}, "{convert_constant_name(constant)}")')
            insert_doc_constant(klass, convert_constant_name(constant), doc)
    if klass == "EOS":
        r_cpp_lines.append("\t_EOS_BING_VERSION_CONSTANTS()")

    if generate_config.assume_only_one_local_user and handle_name in [
        "EOS_ProductUserId",
        "EOS_EpicAccountId",
    ]:
        r_cpp_lines.append(f"\t_CODE_SNIPPET_BINE_GET_LOCAL_ID({klass});")

    r_cpp_lines.append("}")

    if klass == "EOS":
        r_cpp_lines.append("_CODE_SNIPPET_DEFINE_LAST_RESULT_CODE()")

    r_register_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS(godot::eos::{klass})\\")

    insert_doc_class_brief(klass, infos.doc)
    insert_doc_class_description(klass)
    return ret


def gen_disabled_macro(handle_type: str) -> str:
    if handle_type in ["EOS", "EOS_HPlatform"]:
        return ""
    return "EOS_" + handle_type.removeprefix("EOS_H").upper() + "_DISABLED"


def _get_callback_type_of_method(method_info: dict) -> str:
    if len(method_info.args) > 0:
        arg = method_info.args[-1]
        decayed_type: str = decay_eos_type(arg.type)
        if is_callback_type(decayed_type):
            return decayed_type
    return ""


_REMOVE_NOTIFY_PATTERN = re.compile(r"EOS_\w+_RemoveNotify\w*")
_VERSION_SUFFIX_PATTERN = re.compile(r"V\d+$")


def _find_remove_notify_method(add_notify_method: str, method_doc: list[str], handle_type: str) -> str:
    for line in method_doc:
        if "@see" in line and "RemoveNotify" in line:
            match = _REMOVE_NOTIFY_PATTERN.search(line)
            if match:
                return match.group(0)

    remove_method = add_notify_method.replace("AddNotify", "RemoveNotify")

    if handle_type in handles and remove_method in handles[handle_type].methods:
        return remove_method

    remove_method_without_version = _VERSION_SUFFIX_PATTERN.sub("", remove_method)
    if handle_type in handles and remove_method_without_version in handles[handle_type].methods:
        return remove_method_without_version

    return remove_method


def _make_notify_code(
    handle_name: str,
    handle_class: str,
    add_notify_method: str,
    method_info: dict,
    options_type: str,
    r_member_lines: list,
    r_setup_lines: list,
    r_remove_lines: list,
):
    callback_type: str = ""
    for a in method_info.args:
        if is_callback_type(decay_eos_type(a.type)):
            callback_type = a.type
    decayed_callback_type: str = decay_eos_type(callback_type)
    signal_name = convert_to_signal_name(decayed_callback_type, add_notify_method)
    id_identifier: str = f"notify_id_{signal_name}"

    remove_method = _find_remove_notify_method(add_notify_method, method_info.doc, handle_name)
    cb = _gen_callback(decayed_callback_type, handle_name, add_notify_method, [])
    if "_EOS_METHOD_CALLBACK" in cb:
        if generate_config.assume_only_one_local_user and decayed_callback_type in [
            "EOS_Connect_OnLoginStatusChangedCallback",
            "EOS_Auth_OnLoginStatusChangedCallback",
        ]:
            gd_id_type = get_gd_type_of_local_user_id(
                "LocalUserId",
                "EOS_ProductUserId" if decayed_callback_type == "EOS_Connect_OnLoginStatusChangedCallback" else "EOS_EpicAccountId",
            )
            cb = cb.replace(
                "_EOS_METHOD_CALLBACK(",
                f"_CODE_SNIPPET_LOGIN_STATUS_CHANGED_CALLBACK({gd_id_type}, ",
            )
        else:
            cb = cb.replace("_EOS_METHOD_CALLBACK", "_EOS_SIMPLE_NOTIFY_CALLBACK")
    elif "_EOS_METHOD_CALLBACK_EXPANDED" in cb:
        cb = cb.replace("_EOS_METHOD_CALLBACK_EXPANDED", "_EOS_SIMPLE_NOTIFY_CALLBACK_EXPANDED")
    else:
        print_stack_and_exit(f"[handle_generator] 通知回调代码生成失败: 无法识别回调类型 '{callback_type}' 的回调宏")

    r_member_lines.append(f"\tEOS_NotificationId {id_identifier}{{EOS_INVALID_NOTIFICATIONID}};")
    r_setup_lines.append("\tif (m_handle){")
    r_setup_lines.append(f"\t\t{options_type} options;")
    r_setup_lines.append(f"\t\toptions.ApiVersion = {get_api_latest_macro(options_type)};")
    r_setup_lines.append(f"\t\t{id_identifier} = {add_notify_method}(m_handle, &options, this, {cb});")
    r_setup_lines.append("\t}")
    r_setup_lines.append(
        f'\tif ({id_identifier} == EOS_INVALID_NOTIFICATIONID) {{ WARN_PRINT("EOS: Setup signal \\"{handle_class}.{signal_name}\\" failed, this signal is not working."); }}'
    )
    r_remove_lines.append(f"\tif ({id_identifier} != EOS_INVALID_NOTIFICATIONID) {remove_method}(m_handle, {id_identifier});")


def _gen_method(
    handle_type: str,
    method_name: str,
    info: Method,
    r_declare_lines: list[str],
    r_define_lines: list[str],
    r_bind_lines: list[str],
):
    handle_klass: str = convert_handle_class_name(handle_type)

    return_type: str = ""
    callback_signal: str = ""

    out_to_ret: list[bool] = []
    _remapped_return_type_list: list[str] = []
    packed_result_type: str = gen_packed_result_type(method_name, info, [], [], [], out_to_ret, True, _remapped_return_type_list)
    remapped_return_type: str = _remapped_return_type_list[0] if len(_remapped_return_type_list) > 0 else ""
    need_out_to_ret: bool = False if len(out_to_ret) <= 0 else out_to_ret[0]

    for a in info.args:
        decayed_a_type: str = decay_eos_type(a.type)
        if is_callback_type(decayed_a_type):
            if len(info.return_type) <= 0 or info.return_type == "void":
                return_type = "Signal"
                callback_signal: str = convert_to_signal_name(decayed_a_type, method_name)
            break

    if (return_type == "Signal") and (len(packed_result_type) or len(remapped_return_type)):
        print_stack_and_exit(f"[handle_generator] 方法 '{method_name}' 同时存在回调信号和打包返回，二者冲突")

    if len(packed_result_type):
        return_type = f"Ref<{packed_result_type}>"
    if len(remapped_return_type):
        return_type = remapped_return_type
    elif is_handle_type(decay_eos_type(info.return_type)):
        decayed_return_type: str = decay_eos_type(info.return_type)
        return_type = f"Ref<class {convert_handle_class_name(decayed_return_type)}>"
    elif return_type == "" and info.return_type != "void":
        return_type = remap_type(info.return_type, "")
    elif return_type == "":
        return_type = "void"

    if "AddNotify" in method_name:
        return_type = "Ref<EOSNotification>"

    invalid_arg_return_val: str = ""
    if return_type != "void":
        if return_type == "EOS_EResult":
            invalid_arg_return_val = "EOS_EResult::EOS_InvalidParameters"
        else:
            invalid_arg_return_val = "{}"

    if method_name == "EOS_Platform_Create":
        return_type = "EOS_EResult"
        invalid_arg_return_val = "EOS_EResult::EOS_InvalidParameters"

    if is_enum_flags_type(return_type):
        return_type = f"BitField<{return_type}>"
        invalid_arg_return_val = f"{return_type}({{}})"

    snake_method_name: str = convert_method_name(method_name, handle_type)

    declare_args: list[str] = []
    call_args: list[str] = []
    bind_args: list[str] = []

    prepare_lines: list[str] = []
    after_call_lines: list[str] = []

    options_type: str = ""
    options_input_identifier: str = ""
    options_prepare_identifier: str = ""

    for_file_transfer: bool = False

    static: bool = True
    need_handle_null_check: bool = False
    has_str_result_with_result_code_out: list[bool] = []
    i: int = 0

    bind_def_vals: list[str] = []

    expanded_args_doc: dict[str, list[str]] = {}
    additional_doc: list[str] = []
    while i < len(info.args):
        type: str = info.args[i].type
        name: str = info.args[i].name
        decayed_type: str = decay_eos_type(type)
        snake_name: str = to_snake_case(name)

        if decayed_type == handle_type:
            call_args.append("m_handle")
            need_handle_null_check = True
            static = False
        elif is_callback_type(decayed_type):
            if method_name == "EOS_Logging_SetCallback":
                declare_args.append(f"const Callable &p_{snake_name}")
                bind_args.append(f'"{snake_name}"')
                prepare_lines.append(f"\tEOS::get_log_message_callback() = p_{snake_name};")
            else:
                declare_args.append(f"const Callable &p_{snake_name} = {{}}")
                bind_args.append(f'"{snake_name}"')

                if decayed_type in [
                    "EOS_PlayerDataStorage_OnWriteFileCompleteCallback",
                    "EOS_PlayerDataStorage_OnReadFileCompleteCallback",
                    "EOS_TitleStorage_OnReadFileCompleteCallback",
                ]:
                    cb: str = decay_eos_type(get_callback_infos(decayed_type).args[0].type)
                    gd_cb: str = remap_type(cb, name).removeprefix("Ref<").removesuffix(">")
                    signal_name: str = convert_to_signal_name(decayed_type, "")
                    interface_signal_name: str = convert_to_signal_name(decayed_type, "")
                    prepare_lines.append(f'\tstatic constexpr char {signal_name}[] = "{signal_name}";')
                    if signal_name != interface_signal_name:
                        prepare_lines.append(f'\tstatic constexpr char {interface_signal_name}[] = "{interface_signal_name}";')
                    prepare_lines.append(
                        f"\tconstexpr {decayed_type} callback = &godot::eos::internal::file_transfer_completion_callback<{cb}, {gd_cb}, {signal_name}, {interface_signal_name}>;"
                    )
                    call_args.append("callback")
                else:
                    call_args.append(f"{_gen_callback(decayed_type, handle_type, method_name, [], False, return_type == 'Ref<EOSNotification>')}")

                bind_def_vals.append("DEFVAL(Callable())")
            expanded_args_doc[name] = make_callback_doc(decayed_type)
        elif is_client_data(type, name):
            if return_type == "Ref<EOSNotification>":
                next_arg_name: str = decay_eos_type(info.args[i + 1].name)
                prepare_lines.append("\tRef<EOSNotification> ret; ret.instantiate();")
                call_args.append("ret.ptr()")
                after_call_lines.append("\tif (notification_id == EOS_INVALID_NOTIFICATIONID) return {};")
                after_call_lines.append(f"\tauto NotifyRemover = memnew(EOSNotifyRemover(m_handle, &{method_name.replace('AddNotify', 'RemoveNotify')}));")
                after_call_lines.append(f"\tret->_setup(notification_id, NotifyRemover, p_{to_snake_case(next_arg_name)});")

                additional_doc.append("[b]NOTE[/b]: The return value can be null, it means that add notify failed.\n")
            else:
                next_decayed_type: str = decay_eos_type(info.args[i + 1].type)
                if (i + 1) < len(info.args) and is_callback_type(next_decayed_type):
                    if next_decayed_type == "EOS_PlayerDataStorage_OnWriteFileCompleteCallback":
                        write_cb: str = f"{options_input_identifier}->get_{to_snake_case('WriteFileDataCallback')}()"
                        progress_cb: str = f"{options_input_identifier}->get_{to_snake_case('FileTransferProgressCallback')}()"
                        completion_cb: str = f"p_{to_snake_case(info.args[i + 1].name)}"

                        prepare_lines.append(f"\t{return_type} ret; ret.instantiate();")
                        prepare_lines.append(f"\tauto transfer_data = MAKE_FILE_TRANSFER_DATA(ret, {write_cb}, {progress_cb}, {completion_cb});")
                        call_args.append("transfer_data")
                        for_file_transfer = True
                    elif next_decayed_type in [
                        "EOS_PlayerDataStorage_OnReadFileCompleteCallback",
                        "EOS_TitleStorage_OnReadFileCompleteCallback",
                    ]:
                        read_cb: str = f"{options_input_identifier}->get_{to_snake_case('ReadFileDataCallback')}()"
                        progress_cb: str = f"{options_input_identifier}->get_{to_snake_case('FileTransferProgressCallback')}()"
                        completion_cb: str = f"p_{to_snake_case(info.args[i + 1].name)}"

                        prepare_lines.append(f"\t{return_type} ret; ret.instantiate();")
                        prepare_lines.append(f"\tauto transfer_data = MAKE_FILE_TRANSFER_DATA(ret, {read_cb}, {progress_cb}, {completion_cb});")
                        call_args.append("transfer_data")
                        for_file_transfer = True
                    elif next_decayed_type == "EOS_IntegratedPlatform_OnUserPreLogoutCallback":
                        prepare_lines.append("\tstatic auto ClientData = _CallbackClientData(this, {});")
                        prepare_lines.append("\tClientData.handle_wrapper = this;")
                        prepare_lines.append(f"\tClientData.callback = p_{to_snake_case(info.args[i + 1].name)};")
                        call_args.append("&ClientData")
                    else:
                        call_args.append(f"_CallbackClientData::create(this, p_{to_snake_case(info.args[i + 1].name)})")
                else:
                    call_args.append("_CallbackClientData::create(this)")
        elif generate_config.assume_only_one_local_user and is_local_user_id(name):
            interface_class: str = get_login_interface_of_local_user_id(name, type)
            prepare_lines.append(
                f'\tif({get_gd_type_of_local_user_id(name, type)}::_get_local_native() == nullptr) {{ ERR_PRINT("Call \\"{handle_klass}.{snake_method_name}()\\" failed: has not local user, please login by using \\"{interface_class}.login()\\" first."); }}'
            )
            prepare_lines.append(f"\t{type} {name} = {get_gd_type_of_local_user_id(name, type)}::_get_local_native();")
            call_args.append(name)
        elif is_method_input_only_struct(decayed_type) and not is_expanded_struct(decayed_type):
            if name.endswith("Options"):
                options_type: str = decayed_type
                options_input_identifier: str = f"p_{snake_name}"
                options_prepare_identifier: str = f"{name}"
            if len(invalid_arg_return_val):
                prepare_lines.append(f"\tERR_FAIL_NULL_V(p_{snake_name}, {invalid_arg_return_val});")
            else:
                prepare_lines.append(f"\tERR_FAIL_NULL(p_{snake_name});")
            declare_args.append(f"const {remap_type(decayed_type, name)}& p_{snake_name}")

            prepare_lines.append(f"\tauto &{options_prepare_identifier} = p_{snake_name}->to_eos();")

            bind_args.append(f'"{snake_name}"')
            call_args.append(f"&{options_prepare_identifier}")
        elif is_method_input_only_struct(decayed_type) and is_expanded_struct(decayed_type):
            if name.endswith("Options"):
                options_type: str = decayed_type
                options_input_identifier: str = f"p_{snake_name} "
                options_prepare_identifier: str = f"{name}"
            _expand_input_struct(
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
        elif is_out_param_name(name):
            if len(remapped_return_type) == 0:
                converted_return_type: list[str] = []
                _make_packed_result(
                    packed_result_type,
                    method_name,
                    info.return_type == "EOS_EResult",
                    options_prepare_identifier,
                    options_type,
                    i,
                    info.args,
                    call_args,
                    prepare_lines,
                    after_call_lines,
                    converted_return_type,
                    has_str_result_with_result_code_out,
                    handle_klass,
                    snake_method_name,
                )
                if len(converted_return_type):
                    assert_condition(len(converted_return_type) == 1, f"[handle_generator] 方法 '{method_name}' 的返回类型转换结果数量不为1: len={len(converted_return_type)}")

                    if return_type != "void" and not (return_type == "EOS_EResult" and converted_return_type[0] == "String"):
                        print_stack_and_exit(
                            f"[handle_generator] 方法 '{method_name}' 返回类型不匹配: 期望返回类型 '{return_type}' 与转换结果 '{converted_return_type[0]}' 不一致"
                        )

                    return_type = converted_return_type[0]
                    if return_type != "EOS_EResult":
                        invalid_arg_return_val = "{}"
            else:
                assert_condition(info.return_type == "EOS_EResult", f"[handle_generator] 方法 '{method_name}' 返回类型应为 EOS_EResult，实际为 '{info.return_type}'")

                if is_handle_type(decayed_type):
                    gd_handle_class: str = convert_handle_class_name(decayed_type)
                    prepare_lines.append(f"\t{decayed_type} {name}{{ nullptr }};")
                    call_args.append(f"&{name}")
                    after_call_lines.append(f"\treturn HandleCache::get<{decayed_type}, {gd_handle_class}>({name});")
                else:
                    after_call_lines.append(f"\t{remapped_return_type} ret;")
                    after_call_lines.append("\tif (result_code == EOS_EResult::EOS_Success) {")
                    if is_struct_type(decayed_type):
                        call_args.append(f"&{name}")
                        after_call_lines.append("\t\tret.instantiate();")
                        if type.endswith("**"):
                            prepare_lines.append(f"\t{decayed_type} *{name}{{}};")
                            after_call_lines.append(f"\t\tret->set_from_eos(*{name});")
                            after_call_lines.append(f"\t\t{decayed_type}_Release({name});")
                        else:
                            prepare_lines.append(f"\t{decayed_type} {name}{{}};")
                            after_call_lines.append(f"\t\tret->set_from_eos({name});")
                    after_call_lines.append("\t}")
            break
        elif is_str_type(type, name):
            declare_args.append(f"const String &p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            prepare_lines.append(f"\tCharString utf8_{snake_name} = p_{snake_name}.utf8();")
            call_args.append(f"to_eos_type<const CharString &, {type}>(utf8_{snake_name})")
        elif is_str_arr_type(type, name):
            print_stack_and_exit(f"[handle_generator] 不支持的字符串数组参数类型: 方法 '{method_name}', 参数 '{name}' 类型 '{type}'")
        elif is_enum_flags_type(type):
            declare_args.append(f"BitField<{type}> p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"to_eos_type<{type}>(p_{snake_name})")
        elif is_handle_arr_type(type, name):
            print_stack_and_exit(f"[handle_generator] 不支持的句柄数组参数: 方法 '{method_name}', 参数 '{name}' 类型 '{type}'")
        elif is_handle_type(decayed_type):
            declare_args.append(f"const {remap_type(decayed_type, name)} &p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"p_{snake_name}.is_valid()? p_{snake_name}->get_handle() : nullptr")
        elif name.endswith("StringBufferSizeBytes"):
            prepare_lines.append(f"\t{type} {name} = {get_str_result_max_length_macro(method_name)} + 1;")
            call_args.append(name)
        else:
            declare_args.append(f"gd_arg_t<{remap_type(type, name)}> p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"to_eos_type<gd_arg_t<{remap_type(type, name)}>, {type}>(p_{snake_name})")
        i += 1

    r_declare_lines.append(f"\t{'static ' if static else ''}{return_type} {snake_method_name}({', '.join(declare_args)});")

    if need_handle_null_check:
        if len(invalid_arg_return_val):
            prepare_lines.insert(0, f"\tERR_FAIL_NULL_V(m_handle, {invalid_arg_return_val});")
        else:
            prepare_lines.insert(0, "\tERR_FAIL_NULL(m_handle);")

    for i in range(len(declare_args)):
        declare_args[i] = declare_args[i].rsplit(" =", 1)[0]
        declare_args[i] = declare_args[i].replace(" class ", " ")
    r_define_lines.append(f"{return_type.replace('class ', '')} {handle_klass}::{snake_method_name}({', '.join(declare_args)}) {{")
    r_define_lines += prepare_lines
    if method_name == "EOS_Platform_Create":
        r_define_lines.append(f"\tauto platform_handle = {method_name}({', '.join(call_args)});")
        r_define_lines.append("\tERR_FAIL_COND_V(platform_handle == nullptr, EOS_EResult::EOS_UnexpectedError);")
        r_define_lines.append(f"\t{convert_handle_class_name('EOS_HPlatform')}::get_singleton()->set_handle(platform_handle);")
        for m in handles["EOS_HPlatform"].methods:
            if not m.endswith("Interface"):
                continue
            interface: str = "EOS_H" + m.rsplit("_", 1)[1].removeprefix("Get").removesuffix("Interface")
            disable_macro: str = gen_disabled_macro(interface)
            handle_identifier: str = interface.removeprefix("EOS_H").lower() + "_handle"
            r_define_lines.append(f"#ifndef {disable_macro}")
            if handle_identifier.startswith("rtc"):
                r_define_lines.append(f"\tif ({options_prepare_identifier}.RTCOptions != nullptr) {{")
                r_define_lines.append(f"\t\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\t\tERR_FAIL_COND_V({handle_identifier} == nullptr, EOS_EResult::EOS_UnexpectedError);")
                r_define_lines.append(f"\t\t{convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier});")
                r_define_lines.append("\t}")
            elif handle_identifier.startswith("anticheatclient"):
                r_define_lines.append(f"\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\tif ({handle_identifier}) {{ {convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier}); }};")
            elif handle_identifier.startswith("anticheatserver"):
                r_define_lines.append(f"\tif ({options_prepare_identifier}.bIsServer) {{")
                r_define_lines.append(f"\t\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\t\tERR_FAIL_COND_V({handle_identifier} == nullptr, EOS_EResult::EOS_UnexpectedError);")
                r_define_lines.append(f"\t\t{convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier});")
                r_define_lines.append("\t}")
            elif handle_identifier.startswith("playerdatastorage") or handle_identifier.startswith("titlestorage"):
                r_define_lines.append(f"\tif ({options_prepare_identifier}.EncryptionKey) {{")
                r_define_lines.append(f"\t\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\t\tERR_FAIL_COND_V({handle_identifier} == nullptr, EOS_EResult::EOS_UnexpectedError);")
                r_define_lines.append(f"\t\t{convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier});")
                r_define_lines.append("\t} else {")
                r_define_lines.append(f'\t\tWARN_PRINT("Create Platform without encryption_key, The singleton \\"{convert_handle_class_name(interface)}\\" is invalid.");')
                r_define_lines.append("\t}")
            else:
                r_define_lines.append(f"\tauto {handle_identifier} = {m}(platform_handle);")
                r_define_lines.append(f"\tif ({handle_identifier}) {{ {convert_handle_class_name(interface)}::get_singleton()->set_handle({handle_identifier}); }}")
                r_define_lines.append(
                    f'\telse {{ WARN_PRINT("Can\'t get \\"{convert_handle_class_name(interface).removeprefix("EOS")}\\" interface, \\"{convert_handle_class_name(interface)}\\" singleton is invalid, maybe due to platform\'s limitation."); }}'
                )
            r_define_lines.append(f"#endif // {disable_macro}")
    elif method_name == "EOS_Logging_SetCallback":
        r_define_lines.append(f"\tEOS_EResult result_code = {method_name}(_EOS_LOGGING_CALLBACK());")
        r_define_lines.append("\tEOS::_set_last_result_code(result_code);")
    elif is_handle_type(decay_eos_type(info.return_type)):
        r_define_lines.append(f"\tauto return_handle = {method_name}({', '.join(call_args)});")
    elif info.return_type == "EOS_EResult":
        r_define_lines.append(f"\tEOS_EResult result_code = {method_name}({', '.join(call_args)});")
        if not has_str_result_with_result_code_out:
            r_define_lines.append("\tEOS::_set_last_result_code(result_code);")
    elif return_type == "void" or return_type == "Signal" or need_out_to_ret:
        r_define_lines.append(f"\t{method_name}({', '.join(call_args)});")
    elif return_type == "Ref<EOSNotification>":
        r_define_lines.append(f"\tauto notification_id = {method_name}({', '.join(call_args)});")
    else:
        r_define_lines.append(f"\tauto ret = {method_name}({', '.join(call_args)});")
    r_define_lines += after_call_lines
    if method_name == "EOS_Platform_Create":
        r_define_lines.append("\treturn EOS_EResult::EOS_Success;")
    elif is_handle_type(decay_eos_type(info.return_type)):
        if not for_file_transfer:
            gd_handle_class: str = convert_handle_class_name(decayed_return_type)
            r_define_lines.append(f"\treturn HandleCache::get<{decayed_return_type}, {gd_handle_class}>(return_handle);")
        else:
            r_define_lines.append("\tret->set_handle(return_handle);")
            r_define_lines.append("\tHandleCache::put(return_handle, ret);")
            r_define_lines.append("\treturn ret;")
    elif len(packed_result_type):
        if info.return_type == "EOS_EResult":
            r_define_lines.append("\tret->result_code = result_code;")
        r_define_lines.append("\treturn ret;")
    elif len(remapped_return_type):
        if not any(line.strip().startswith("return ") for line in after_call_lines):
            r_define_lines.append("\treturn ret;")
        additional_doc.append("If the return value is null, please use [method EOS.get_last_result_code] to check the error.\n")
    elif return_type == "EOS_EResult":
        r_define_lines.append("\treturn result_code;")
    elif return_type == "Signal":
        r_define_lines.append(f'\treturn Signal(this, SNAME("{callback_signal}"));')
        additional_doc.append(f"Return signal [signal {callback_signal}].\n")
    elif return_type.startswith("BitField"):
        r_define_lines.append(f"\treturn _EXPAND_TO_GODOT_VAL_FLAGS({return_type}, ret);")
    elif return_type != "void":
        r_define_lines.append(f"\treturn _EXPAND_TO_GODOT_VAL({return_type}, ret);")

    r_define_lines.append("}")

    bind_args_text: str = ", ".join(bind_args)
    if len(bind_args_text):
        bind_args_text = ", " + bind_args_text
    default_val_arg: str = ""
    if len(bind_def_vals):
        default_val_arg = ", " + ", ".join(bind_def_vals)

    bind_prefix: str = "ClassDB::bind_static_method(get_class_static(), " if static else "ClassDB::bind_method("
    r_bind_lines.append(f'\t{bind_prefix}D_METHOD("{snake_method_name}"{bind_args_text}), &{handle_klass}::{snake_method_name}{default_val_arg});')

    insert_doc_method(
        handle_klass,
        snake_method_name,
        info.doc,
        expanded_args_doc,
        additional_doc,
        bool(has_str_result_with_result_code_out),
    )


def _gen_callback(
    callback_type: str,
    handle: str,
    method: str,
    r_bind_signal_lines: list[str],
    for_gen_signal_binding: bool = False,
    for_notification: bool = False,
) -> str:
    infos = get_callback_infos(callback_type)
    method = convert_method_name(method, handle) if len(method) else method
    handle = convert_handle_class_name(handle)

    if not len(infos.args) == 1:
        if callback_type not in ["EOS_PlayerDataStorage_OnWriteFileDataCallback"]:
            print_stack_and_exit(f"[handle_generator] 回调 '{callback_type}' 的参数数量不为1，无法生成回调代码")

    arg: Arg = infos.args[0]
    arg_type: str = arg.type
    arg_name: str = arg.name
    return_type: str = infos.return_type
    decayed_arg_type: str = decay_eos_type(arg_type)

    assert_condition(is_struct_type(decayed_arg_type), f"[handle_generator] 回调 '{callback_type}' 的参数类型 '{decayed_arg_type}' 不是结构体，无法生成回调代码")

    signal_name: str = convert_to_signal_name(callback_type)
    if not is_expanded_struct(decayed_arg_type):
        r_bind_signal_lines.append(f'\tADD_SIGNAL(MethodInfo("{signal_name}", _MAKE_PROP_INFO({convert_to_struct_class(decayed_arg_type)}, {to_snake_case(arg_name)})));')
        gd_cb_info_type: str = remap_type(decayed_arg_type, arg_name).removeprefix("Ref<").removesuffix(">")
        ret: str = ""
        if callback_type == "EOS_IntegratedPlatform_OnUserPreLogoutCallback":
            ret = f'_EOS_USER_PRE_LOGOUT_CALLBACK({arg_type}, data, "{signal_name}", {gd_cb_info_type})'
        elif len(return_type):
            if for_gen_signal_binding:
                return ""
            print_stack_and_exit(f"[handle_generator] 回调 '{callback_type}' 具有非空返回类型 '{return_type}'，不支持生成信号绑定")
        else:
            if not for_notification:
                ret = f'_EOS_METHOD_CALLBACK({arg_type}, data, "{signal_name}", {gd_cb_info_type})'
            else:
                ret = f"_EOS_NOTIFY_CALLBACK({arg_type}, data, {gd_cb_info_type})"

        additional_doc: list[str] = []
        if len(method) and signal_name.startswith("on_"):
            additional_doc.append(f"Callback of [method {method}].\n")
        insert_doc_signal(handle, signal_name, infos.doc, {}, additional_doc)
        return ret
    else:
        fields: dict[str, StructField] = get_struct_fields(decayed_arg_type)

        count_and_variant_type_fields: list[str] = find_count_and_variant_type_fields_in_struct(decayed_arg_type)

        ret: str = ""
        signal_bind_args: str = ""

        expanded_args_doc: dict[str, list[str]] = {}

        if len(return_type):
            if for_gen_signal_binding:
                return ""
            print_stack_and_exit(f"[handle_generator] 展开式回调 '{callback_type}' 具有非空返回类型 '{return_type}'，不支持生成信号绑定")
        else:
            if not for_notification:
                ret = f'\n\t\t_EOS_METHOD_CALLBACK_EXPANDED({arg_type}, data, "{signal_name}"'
            else:
                ret = f"\n\t\t_EOS_NOTIFY_CALLBACK_EXPANDED({arg_type}, data"

        for field in fields:
            field_type: str = fields[field].type
            decayed_field_type: str = decay_eos_type(field_type)
            if is_api_version_field(field_type, field):
                continue

            if is_internal_platform_specific_field(field) or fields[field].deprecated or field in count_and_variant_type_fields:
                continue

            if is_client_data_field(field_type, field):
                continue

            snake_case_field: str = to_snake_case(field)
            if generate_config.assume_only_one_local_user and is_local_user_id(field) and need_ignore_local_user_id_struct(struct_type=arg_type):
                continue

            if not ret.endswith(",\n\t\t\t"):
                ret += ",\n\t\t\t"
                signal_bind_args += ", "

            if is_enum_type(field_type):
                if is_enum_flags_type(field_type):
                    ret += f"_EXPAND_TO_GODOT_VAL_FLAGS({remap_type(field_type, field, struct_name=decayed_arg_type)}, data->{field})"
                else:
                    ret += f"_EXPAND_TO_GODOT_VAL({remap_type(field_type, field, struct_name=decayed_arg_type)}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO_ENUM({snake_case_field}, {get_enum_owned_interface(field_type)}, {convert_enum_type(field_type)})"
            elif is_pure_handle_type(decayed_field_type):
                ret += f"_EXPAND_TO_GODOT_VAL_PURE_HANDLE(data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({remap_type(field_type, field, struct_name=decayed_arg_type)}, {snake_case_field})"
            elif is_socket_id_type(decayed_field_type, field):
                ret += f"String(data->{field}.SocketName)"
                signal_bind_args += f'PropertyInfo(Variant::STRING, "{snake_case_field}")'
            elif is_requested_channel_ptr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_REQUESTED_CHANNEL({remap_type(field_type, field, struct_name=decayed_arg_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::INT, "{snake_case_field}")'
            elif field_type.startswith("Union"):
                ret += f"_EXPAND_TO_GODOT_VAL_UNION({remap_type(field_type, field, struct_name=decayed_arg_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::NIL, "{snake_case_field}")'
            elif is_internal_struct_arr_field(field_type, field, decayed_arg_type):
                ret += f"_EXPAND_TO_GODOT_VAL_STRUCT_ARR({remap_type(decayed_field_type, field, struct_name=decayed_arg_type)}, data->{field}, {find_count_field(field, fields.keys())})"
                signal_bind_args += f'PropertyInfo(Variant::ARRAY, "{snake_case_field}", PROPERTY_HINT_ARRAY_TYPE, "{convert_to_struct_class(decayed_field_type)}")'
            elif is_internal_struct_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_STRUCT({remap_type(decayed_field_type, field, struct_name=decayed_arg_type)}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({convert_to_struct_class(decayed_field_type)}, {snake_case_field})"
            elif is_handle_arr_type(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_HANDLER_ARR({convert_handle_class_name(decayed_field_type)}, data->{field}, {find_count_field(field, fields.keys())})"
                signal_bind_args += f"_MAKE_PROP_INFO_TYPED_ARR({convert_handle_class_name(decayed_field_type)}, {snake_case_field})"
            elif is_handle_type(decayed_field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_HANDLER({convert_handle_class_name(decayed_field_type)}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({convert_handle_class_name(decayed_field_type)}, {snake_case_field})"
            elif is_arr_field(field_type, field, decayed_arg_type):
                ret += (
                    f"_EXPAND_TO_GODOT_VAL_ARR({remap_type(field_type, field, struct_name=decayed_arg_type)}, data->{field}, data->{find_count_field(field, fields.keys())})"
                )
                signal_bind_args += f'PropertyInfo(Variant({remap_type(field_type, field, struct_name=decayed_arg_type)}()).get_type(), "{snake_case_field}")'
            else:
                ret += f"_EXPAND_TO_GODOT_VAL({remap_type(field_type, field, struct_name=decayed_arg_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant({remap_type(field_type, field, struct_name=decayed_arg_type)}()).get_type(), "{snake_case_field}")'

            expanded_args_doc[snake_case_field] = fields[field].doc
        ret += ")"

        r_bind_signal_lines.append(f'\tADD_SIGNAL(MethodInfo("{signal_name}"{signal_bind_args}));')

        additional_doc: list[str] = []
        if len(method) and signal_name.startswith("on_"):
            additional_doc.append(f"Callback of [method {method}].\n")
        insert_doc_signal(handle, signal_name, infos.doc, expanded_args_doc, additional_doc)
        return ret


def _expand_input_struct(
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
    r_required_arg_doc: dict[str, list[str]],
):
    decayed_type: str = decay_eos_type(arg_type)

    r_prepare_lines.append(f"\t{decayed_type} {arg_name}{{}};")
    r_call_args.append(f"&{arg_name}")

    fields: dict[str, StructField] = get_struct_fields(decayed_type)

    count_fields: list[str] = []
    variant_union_type_fields: list[str] = []
    for field in fields.keys():
        if is_internal_platform_specific_field(field) or fields[field].deprecated:
            continue

        field_type: str = fields[field].type
        if is_arr_field(field_type, field, decayed_type) or is_internal_struct_arr_field(field_type, field, decayed_type):
            count_fields.append(find_count_field(field, fields.keys()))

        if is_variant_union_type(field_type, field):
            for f in fields.keys():
                if f == field + "Type":
                    variant_union_type_fields.append(f)

    for field in fields:
        field_type: str = fields[field].type
        decay_field_type: str = decay_eos_type(field_type)
        snake_field: str = to_snake_case(field)

        if is_api_version_field(field_type, field):
            macro: str = get_api_latest_macro(decayed_type)
            r_prepare_lines.append(f"\t{arg_name}.ApiVersion = {macro};")
            continue
        elif is_internal_platform_specific_field(field) or fields[field].deprecated or field in count_fields or field in variant_union_type_fields:
            continue

        options_field: str = f"{arg_name}.{field}"
        if generate_config.assume_only_one_local_user and is_local_user_id(field) and need_ignore_local_user_id_struct(decayed_type):
            interface_class: str = get_login_interface_of_local_user_id(field, field_type)
            if need_check_null_local_user_id_struct(field_type):
                r_prepare_lines.append(
                    f'\tif({get_gd_type_of_local_user_id(field, field_type)}::_get_local_native() == nullptr) {{ ERR_PRINT("Call \\"{handle_klass}.{snake_method_name}()\\" failed: has not local user, please login by using \\"{interface_class}.login()\\" first."); }}'
                )
            r_prepare_lines.append(f"\t{options_field} = {get_gd_type_of_local_user_id(field, field_type)}::_get_local_native();")
            continue

        r_bind_args.append(f'"{snake_field}"')

        if is_pure_handle_type(decay_field_type):
            r_declare_args.append(f"{remap_type(decay_field_type, field, struct_name=decayed_type)} p_{snake_field}")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_PURE_HANDLE({options_field}, p_{snake_field});")
        elif is_audio_frames_type(arg_type, arg_name):
            r_declare_args.append(f"const PackedInt32Array &p_{snake_field}")
            r_prepare_lines.append(f"\tLocalVector<int32_t> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_packed_int32_to_audio_frames(p_{snake_field}, _shadow_{snake_field});")
            r_prepare_lines.append(f"\t{arg_name}.{find_count_field(field, fields.keys())} = _shadow_{snake_field}.size();")
            r_prepare_lines.append(f"\t{options_field} = _shadow_{snake_field}.ptr();")
        elif is_socket_id_type(decay_field_type, field):
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
            r_prepare_lines.append("\t}")
            r_prepare_lines.append(f"\tEOS_P2P_SocketId {field};")
            r_prepare_lines.append(f"\t{field}.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;")
            r_prepare_lines.append(f"\tmemcpy(&{field}.SocketName[0], ascii_{snake_field}.get_data(), MIN(ascii_{snake_field}.size(), EOS_P2P_SOCKETID_SOCKETNAME_SIZE));")
            r_prepare_lines.append(f"\t{options_field} = &{field};")
        elif is_str_type(field_type, field):
            r_declare_args.append(f"const String &p_{snake_field}")
            r_prepare_lines.append(f"\tCharString utf8_{snake_field} = p_{snake_field}.utf8();")
            r_prepare_lines.append(f"\t{options_field} = to_eos_type<const CharString &, decltype({options_field})>(utf8_{snake_field});")
        elif is_str_arr_type(field_type, field):
            r_declare_args.append(f"const PackedStringArray &p_{snake_field}")
            option_count_field: str = f"{arg_name}.{find_count_field(field, fields.keys())}"
            element_type: str = get_str_arr_element_type(field_type)
            r_prepare_lines.append(f"\tLocalVector<{element_type}> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_TO_EOS_STR_ARR_FROM_PACKED_STRING_ARR({options_field}, p_{snake_field}, _shadow_{snake_field}, {option_count_field});")
        elif is_nullable_float_pointer_field(field_type, field):
            r_declare_args.append(f"{decay_field_type} p_{snake_field} = -1.0")
            r_prepare_lines.append(f"\t{options_field} = p_{snake_field} < 0.0? nullptr: &p_{snake_field};")
        elif is_requested_channel_ptr_field(field_type, field):
            r_declare_args.append(f"{remap_type(field_type, field, struct_name=decayed_type)} p_{snake_field} = -1")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_REQUESTED_CHANNEL({options_field}, p_{snake_field});")
            r_bind_def_vals.append("DEFVAL(-1)")
        elif field_type.startswith("Union"):
            r_declare_args.append(f"const {remap_type(decay_field_type, field, struct_name=decayed_type)} &p_{snake_field}")
            if is_variant_union_type(field_type, field):
                r_prepare_lines.append(f"\t_TO_EOS_FIELD_VARIANT_UNION({options_field}, p_{snake_field});")
            else:
                r_prepare_lines.append(f"\t_TO_EOS_FIELD_METRICS_ACCOUNT_ID_UNION({options_field}, p_{snake_field});")
        elif is_handle_arr_type(field_type, field):
            r_declare_args.append(f"const TypedArray<{convert_handle_class_name(decay_field_type)}> &p_{snake_field}")
            option_count_field: str = f"{arg_name}.{find_count_field(field, fields.keys())}"
            r_prepare_lines.append(f"\tLocalVector<{decay_field_type}> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_HANDLER_ARR({options_field}, p_{snake_field}, _shadow_{snake_field}, {option_count_field});")
        elif is_handle_type(decay_field_type, field):
            r_declare_args.append(f"const class {remap_type(decay_field_type, field, struct_name=decayed_type)} &p_{snake_field}")
            if len(invalid_arg_return_value):
                r_prepare_lines.append(
                    f'\tERR_FAIL_NULL_V_MSG(p_{snake_field}, {{}}, (EOS::_set_last_result_code(EOS_EResult::EOS_InvalidParameters), "Execute {handle_klass}::{snake_method_name} failed: {snake_field} is null."));'
                )
            else:
                r_prepare_lines.append(
                    f'\tERR_FAIL_NULL_MSG(p_{snake_field}, (EOS::_set_last_result_code(EOS_EResult::EOS_InvalidParameters), "Execute {handle_klass}::{snake_method_name} failed: {snake_field} is null."));'
                )
            gd_type: str = convert_handle_class_name(decay_field_type)
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_HANDLER({options_field}, p_{snake_field}, {gd_type});")
        elif is_client_data_field(field_type, field):
            print_stack_and_exit(f"[handle_generator] 不支持的 ClientData 字段类型: '{arg_type}'")
        elif is_internal_struct_arr_field(field_type, field, decayed_type):
            r_declare_args.append(f"const TypedArray<{convert_to_struct_class(decay_field_type)}> &p_{snake_field}")
            option_count_field: str = f"{arg_name}.{find_count_field(field, fields.keys())}"
            r_prepare_lines.append(f"\tLocalVector<{decay_field_type}> _shadow_{snake_field};")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_STRUCT_ARR({options_field}, p_{snake_field}, _shadow_{snake_field}, {option_count_field});")
        elif is_internal_struct_field(field_type, field):
            r_declare_args.append(f"const {remap_type(decay_field_type, field, True, struct_name=decayed_type)} &p_{snake_field}")
            if len(invalid_arg_return_value):
                r_prepare_lines.append(
                    f'\tERR_FAIL_NULL_V_MSG(p_{snake_field}, {{}}, (EOS::_set_last_result_code(EOS_EResult::EOS_InvalidParameters), "Execute {handle_klass}::{snake_method_name} failed: {snake_field} is null."));'
                )
            else:
                r_prepare_lines.append(
                    f'\tERR_FAIL_NULL_MSG(p_{snake_field}, (EOS::_set_last_result_code(EOS_EResult::EOS_InvalidParameters), "Execute {handle_klass}::{snake_method_name} failed: {snake_field} is null."));'
                )

            r_prepare_lines.append(f"\t_TO_EOS_FIELD_STRUCT({options_field}, p_{snake_field});")

        elif is_arr_field(field_type, field, decayed_type):
            r_declare_args.append(f"const {remap_type(field_type, field, struct_name=decayed_type)} &p_{snake_field}")
            option_count_field: str = f"{arg_name}.{find_count_field(field, fields.keys())}"
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_ARR({options_field}, p_{snake_field}, {option_count_field});")
        elif is_struct_ptr(field_type):
            r_declare_args.append(f"gd_arg_t<{remap_type(field_type, field, struct_name=decayed_type)}> p_{snake_field}")
            r_prepare_lines.append(f"\t{field_type} shadow_{snake_field} = to_eos_type<decltype(p_{snake_field}), {decay_field_type}>(p_{snake_field});")
            r_prepare_lines.append(f"\t{options_field} = &shadow_{snake_field};")
        elif is_enum_flags_type(field_type):
            r_declare_args.append(f"BitField<{remap_type(field_type, field, struct_name=decayed_type)}> p_{snake_field}")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD_FLAGS({options_field.split('[')[0]}, p_{snake_field});")
        else:
            r_declare_args.append(f"gd_arg_t<{remap_type(field_type, field, struct_name=decayed_type)}> p_{snake_field}")
            r_prepare_lines.append(f"\t_TO_EOS_FIELD({options_field.split('[')[0]}, p_{snake_field});")

        r_required_arg_doc[field] = fields[field].doc


def _gen_str_retry_lines(
    arg_name: str,
    length_name: str,
    method_name: str,
    r_call_args: list[str],
    assign_expr: str,
    indent: str,
) -> list[str]:
    lines: list[str] = []
    lines.append(f"{indent}if (result_code == EOS_EResult::EOS_LimitExceeded) {{")
    for ca in r_call_args:
        if ca.endswith("StringBufferSizeBytes"):
            lines.append(f"{indent}\t{ca} = {length_name};")
            break
    lines.append(f"{indent}\tchar *{arg_name}_retry = memnew_arr(char, {length_name});")
    lines.append(f"{indent}\tmemset({arg_name}_retry, 0, {length_name});")
    lines.append(f"{indent}\tresult_code = {method_name}({', '.join(r_call_args).replace(f'&{arg_name}[0]', f'&{arg_name}_retry[0]')});")
    lines.append(f"{indent}\tif (result_code == EOS_EResult::EOS_Success) {{")
    lines.append(f"{indent}\t\t{assign_expr} = String::utf8(&{arg_name}_retry[0]);")
    lines.append(f"{indent}\t}}")
    lines.append(f"{indent}\tmemdelete_arr({arg_name}_retry);")
    return lines


def _make_packed_result(
    packed_result_type: str,
    method_name: str,
    has_result_code: bool,
    options_identifier: str,
    options_type: str,
    begin_idx: int,
    args: list[Arg],
    r_call_args: list[str],
    r_prepare_lines: list[str],
    r_after_call_lines: list[str],
    r_return_type_if_convert_to_return: list[str],
    r_has_str_result_with_result_code: list[bool] = [],
    handle_klass: str = "",
    snake_method_name: str = "",
):
    pack_result: bool = len(packed_result_type) > 0
    has_str_result_with_result_code: bool = False

    header_lines: list[str] = []
    if pack_result:
        header_lines.append(f"\tRef<{packed_result_type}> ret; ret.instantiate();")

    str_retry_lines: list[str] = []
    body_lines: list[str] = []
    acl_indents: str = "\t\t" if (has_result_code and pack_result) else "\t"
    i: int = begin_idx
    while i < len(args):
        arg_name: str = args[i].name
        arg_type: str = args[i].type
        decayed_type: str = decay_eos_type(arg_type)
        snake_name: str = to_snake_case(strip_out_param_prefix(arg_name))

        if is_handle_arr_type(arg_type, arg_name):
            print_stack_and_exit(f"[handle_generator] 不支持的句柄数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")
        elif is_handle_type(decayed_type):
            r_prepare_lines.append(f"\t{decayed_type} {arg_name}{{ nullptr }};")
            r_call_args.append(f"&{arg_name}")
            gd_handle_class: str = convert_handle_class_name(decayed_type)
            if pack_result:
                body_lines.append(f"{acl_indents}ret->{snake_name} = HandleCache::get<{decayed_type}, {gd_handle_class}>({arg_name});")
            else:
                r_return_type_if_convert_to_return.append(f"Ret<{gd_handle_class}>")
                body_lines.append(f"{acl_indents}Ret<{gd_handle_class}> ret = HandleCache::get<{decayed_type}, {gd_handle_class}>({arg_name});")
        elif is_struct_type(decayed_type):
            if arg_type.endswith("**"):
                r_prepare_lines.append(f"\t{decayed_type} *{arg_name}{{ nullptr }};")
                r_call_args.append(f"&{arg_name}")
                if pack_result:
                    body_lines.append(f"{acl_indents}ret->{snake_name}.instantiate(); ret->{snake_name}->set_from_eos(*{arg_name});")
                    body_lines.append(f"{acl_indents}{decayed_type}_Release({arg_name});")
                else:
                    return_type: str = remap_type(decayed_type, arg_name)
                    r_return_type_if_convert_to_return.append(f"Ret<{return_type}>")
                    body_lines.append(f"{acl_indents}Ret<{return_type}> ret; ret.instantiate(); ret->set_from_eos(*{arg_name});")
                    body_lines.append(f"{acl_indents}{decayed_type}_Release({arg_name});")
            else:
                r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
                r_call_args.append(f"&{arg_name}")
                if pack_result:
                    body_lines.append(f"{acl_indents}ret->{snake_name}.instantiate(); ret->{snake_name}->set_from_eos({arg_name});")
                else:
                    r_return_type_if_convert_to_return.append(f"Ret<{convert_to_struct_class(decayed_type)}>")
                    body_lines.append(f"{acl_indents}Ret<{convert_to_struct_class(decayed_type)}> ret; ret.instantiate(); ret->set_from_eos({arg_name});")
        elif is_socket_id_type(decayed_type, arg_name):
            r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
            r_call_args.append(f"&{arg_name}")
            if pack_result:
                body_lines.append(f"{acl_indents}ret->{snake_name} = String(&{arg_name}.SocketName[0]);")
            else:
                r_return_type_if_convert_to_return.append("String")
                body_lines.append(f"{acl_indents}String ret{{ &{arg_name}.SocketName[0] }};")
        elif is_enum_type(decayed_type):
            r_prepare_lines.append(f"\t{convert_enum_type(decayed_type)} {arg_name};")
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                body_lines.append(f"{acl_indents}ret->{snake_name} = {arg_name};")
            else:
                r_return_type_if_convert_to_return.append(f"{remap_type(decayed_type, arg_name)}")
                body_lines.append(f"{acl_indents}{remap_type(decayed_type, arg_name)} ret = {arg_name};")
        elif (
            arg_type == "char*"
            and (i + 1) < len(args)
            and (args[i + 1].type.endswith("int32_t*") or args[i + 1].type.endswith("uint32_t*"))
            and args[i + 1].name.endswith("Length")
        ):
            max_length_macro: str = get_str_result_max_length_macro(method_name)
            has_macro: bool = has_str_result_max_length_macro(method_name)
            length_name: str = args[i + 1].name
            length_type: str = decay_eos_type(args[i + 1].type)
            r_prepare_lines.append(f"\t{length_type} {length_name}{{ {max_length_macro} + 1 }};")

            if has_macro:
                r_prepare_lines.append(f"\tchar {arg_name} [{max_length_macro} + 1] {{}};")
            else:
                r_prepare_lines.append(f"\tchar {arg_name} [{max_length_macro} + 1] {{}};")

            r_call_args.append(f"&{arg_name}[0]")
            r_call_args.append(f"&{length_name}")

            if has_result_code and not has_macro:
                retry_assign: str = f"ret->{snake_name}" if pack_result else "ret"
                str_retry_lines.extend(_gen_str_retry_lines(arg_name, length_name, method_name, r_call_args, retry_assign, "\t"))

            if pack_result:
                body_lines.append(f"{acl_indents}ret->{snake_name} = String::utf8(&{arg_name}[0]);")
            else:
                r_return_type_if_convert_to_return.append("String")
                if has_result_code:
                    has_str_result_with_result_code = True
                    r_prepare_lines.append("\tString ret;")
                    if not has_macro:
                        body_lines.append(f"{acl_indents}if (result_code == EOS_EResult::EOS_Success) {{ ret = String::utf8(&{arg_name}[0]); }}")
                        body_lines.append(f"{acl_indents}else {{")
                        body_lines.extend(_gen_str_retry_lines(arg_name, length_name, method_name, r_call_args, "ret", f"{acl_indents}\t"))
                        body_lines.append(f"{acl_indents}\t}}")
                        body_lines.append(f"{acl_indents}}}")
                        str_retry_lines.clear()
                    else:
                        body_lines.append(f"{acl_indents}if (result_code == EOS_EResult::EOS_Success) {{ ret = String::utf8(&{arg_name}[0]); }}")
                    generated_func_name: str = f"{handle_klass}::{snake_method_name}" if handle_klass and snake_method_name else method_name
                    body_lines.append(f"{acl_indents}EOS::_set_last_result_code(result_code);")
                    body_lines.append(
                        f'{acl_indents}ERR_FAIL_COND_V_MSG(result_code != EOS_EResult::EOS_Success, {{}}, vformat("Execute {generated_func_name} failed: %s (%d)", EOS_EResult_ToString(result_code), result_code));'
                    )
                else:
                    body_lines.append(f"{acl_indents}String ret = String::utf8(&{arg_name}[0]);")
            i += 1
        elif arg_type == "void*" and (i + 1) <= len(args) and args[i + 1].type.endswith("int32_t*"):
            length_variable: str = ""
            options_fields: dict[str, StructField] = get_struct_fields(options_type)
            for field in options_fields:
                if field == arg_name + "SizeBytes":
                    length_variable = f"{options_identifier}.{field}"
                    break
                elif field in ["MaxDataSizeBytes"]:
                    length_variable = f"{options_identifier}.{field}"
                    break
            assert_condition(len(length_variable) > 0, f"[handle_generator] 找不到参数 '{arg_name}' 对应的长度变量")

            r_prepare_lines.append(f"\tPackedByteArray {arg_name};")
            r_prepare_lines.append(f"\t{arg_name}.resize({length_variable});")
            r_prepare_lines.append(f"\t{decay_eos_type(args[i + 1].type)} {args[i + 1].name} = {length_variable};")

            r_call_args.append(f"{arg_name}.ptrw()")
            r_call_args.append(f"&{args[i + 1].name}")

            body_lines.append(f"{acl_indents}{arg_name}.resize({args[i + 1].name});")

            if pack_result:
                body_lines.append(f"{acl_indents}ret->{snake_name} = {arg_name};")
            else:
                r_return_type_if_convert_to_return.append("PackedByteArray")
                body_lines.append(f"{acl_indents}PackedByteArray ret = {arg_name};")

            i += 1
        elif decayed_type == "EOS_Bool":
            r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                body_lines.append(f"{acl_indents}ret->{snake_name} = {arg_name};")
            else:
                r_return_type_if_convert_to_return.append(f"{remap_type(decayed_type, arg_name)}")
                body_lines.append(f"{acl_indents}{remap_type(decayed_type, arg_name)} ret = {arg_name};")

            i += 1
        elif is_arr_field(arg_type, arg_name):
            print_stack_and_exit(f"[handle_generator] 不支持的数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")
        elif is_internal_struct_arr_field(arg_type, arg_name):
            print_stack_and_exit(f"[handle_generator] 不支持的结构体数组输出参数: 方法 '{method_name}', 类型 '{arg_type}'")
        elif is_struct_ptr(arg_type):
            print_stack_and_exit(f"[handle_generator] 不支持的结构体指针输出参数: 方法 '{method_name}', 类型 '{arg_type}'")
        else:
            assert_condition(arg_type.endswith("*"), f"[handle_generator] 不支持的输出参数: 方法 '{method_name}', 类型 '{arg_type}', 参数名 '{arg_name}'")

            r_prepare_lines.append(f"\t{arg_type.removesuffix('*')} {arg_name};")
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                body_lines.append(f"{acl_indents}_FROM_EOS_FIELD(ret->{snake_name}, {arg_name.split('[')[0]});")
            else:
                r_return_type_if_convert_to_return.append(f"{remap_type(decayed_type, arg_name)}")
                body_lines.append(f"{acl_indents}{remap_type(decayed_type, arg_name)} ret; _FROM_EOS_FIELD(ret, {arg_name.split('[')[0]});")

        i += 1

    r_after_call_lines += header_lines
    if has_result_code:
        if pack_result:
            if has_str_result_with_result_code:
                r_after_call_lines.append("\tEOS::_set_last_result_code(result_code);")
            r_after_call_lines += str_retry_lines
            if len(str_retry_lines) > 0:
                r_after_call_lines.append("\t} else if (result_code == EOS_EResult::EOS_Success) {")
            else:
                r_after_call_lines.append("\tif (result_code == EOS_EResult::EOS_Success) {")
        elif len(str_retry_lines) > 0:
            r_after_call_lines += str_retry_lines
    r_after_call_lines += body_lines
    if has_result_code and pack_result:
        r_after_call_lines.append("\t}")
    if has_str_result_with_result_code and len(r_has_str_result_with_result_code) == 0:
        r_has_str_result_with_result_code.append(True)

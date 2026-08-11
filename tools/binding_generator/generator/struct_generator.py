# 结构体代码生成器

from binding_generator.config import eos_data_class_h_file, generate_config
from binding_generator.context import (
    struct2additional_method_requirements,
)
from binding_generator.doc.doc_processor import (
    insert_doc_class_brief,
    insert_doc_class_description,
    insert_doc_property,
)
from binding_generator.models import Arg, Struct, StructField
from binding_generator.utils.common import assert_condition, print_stack_and_exit
from binding_generator.utils.naming import (
    convert_handle_class_name,
    convert_to_signal_name,
    convert_to_struct_class,
    decay_eos_type,
    remove_backslash_of_last_line,
    to_snake_case,
)
from binding_generator.utils.type import (
    find_count_and_variant_type_fields_in_struct,
    find_count_field,
    get_api_latest_macro,
    get_callback_infos,
    get_gd_type_of_local_user_id,
    get_login_interface_of_local_user_id,
    get_str_arr_element_type,
    is_api_version_field,
    is_arr_field,
    is_audio_frames_type,
    is_callback_type,
    is_client_data_field,
    is_enum_flags_type,
    is_expanded_struct,
    is_handle_arr_type,
    is_handle_type,
    is_integrated_platform_init_option,
    is_integrated_platform_init_option_type,
    is_internal_platform_specific_field,
    is_internal_struct_arr_field,
    is_internal_struct_field,
    is_local_user_id,
    is_memory_func_type,
    is_need_skip_struct,
    is_nullable_float_pointer_field,
    is_platform_specific_options_field,
    is_pure_handle_type,
    is_requested_channel_ptr_field,
    is_reserved_field,
    is_socket_id_type,
    is_str_arr_type,
    is_str_type,
    is_struct_ptr,
    is_struct_type,
    is_system_initialize_options_filed,
    is_todo_field,
    is_variant_union_type,
    need_check_null_local_user_id_struct,
    need_ignore_local_user_id_struct,
    remap_type,
)


def gen_structs(
    file_base_name: str,
    types_include_file: str,
    handle_class: str,
    struct_infos: dict[str, Struct],
    additional_include_lines: list[str],
    r_cpp_lines: list[str],
) -> list[str]:
    r_cpp_lines.append("")
    r_cpp_lines.append("using namespace godot::eos::internal;")
    r_cpp_lines.append("namespace godot::eos {")

    lines: list[str] = []
    lines.append("#pragma once")
    lines.append("")
    lines.append(f"#include <{types_include_file}>")
    lines.append("#include <godot_cpp/classes/ref_counted.hpp>")
    lines.append("")
    lines.append(f"#include <{eos_data_class_h_file}>")
    lines.append("")
    if len(additional_include_lines):
        lines += additional_include_lines
        lines.append("")

    lines.append("namespace godot::eos {")
    for struct_type in struct_infos:
        if is_expanded_struct(struct_type):
            continue
        if is_need_skip_struct(struct_type):
            continue
        if struct_infos[struct_type].deprecated:
            continue
        lines += _gen_struct(struct_type, struct_infos[struct_type], r_cpp_lines)

    lines.append("")
    r_cpp_lines.append("} // namespace godot::eos")
    r_cpp_lines.append("")

    lines.append("} // namespace godot::eos")
    lines.append("")

    lines.append("// ====================")
    lines.append(f"#define REGISTER_DATA_CLASSES_OF_{convert_handle_class_name(handle_class)}()\\")
    for st in struct_infos:
        if is_expanded_struct(st):
            continue
        if is_need_skip_struct(st):
            continue
        if struct_infos[st].deprecated:
            continue
        lines.append(f"\tGDREGISTER_CLASS(godot::eos::{convert_to_struct_class(st)})\\")
    remove_backslash_of_last_line(lines)
    lines.append("")
    return lines


def _gen_struct(
    struct_type: str,
    struct_info: Struct,
    r_structs_cpp: list[str],
) -> list[str]:
    fields: dict[str, StructField] = struct_info.fields
    member_lines: list[str] = []
    setget_declare_lines: list[str] = []
    setget_define_lines: list[str] = []
    bind_lines: list[str] = []
    optional_cpp_lines: list[str] = []

    count_and_variant_type_fields: list[str] = find_count_and_variant_type_fields_in_struct(struct_type)
    additional_methods_requirements: dict[str, bool] = struct2additional_method_requirements[struct_type]
    typename: str = convert_to_struct_class(struct_type)

    for field in fields.keys():
        type: str = fields[field].type
        snake_field_name: str = to_snake_case(field)
        decayed_type: str = decay_eos_type(type)
        remapped_type: str = ""

        if not is_need_skip_struct(decayed_type) and is_struct_type(decayed_type) and not is_internal_struct_arr_field(type, field, struct_type):
            remapped_type = remap_type(decayed_type, field, struct_name=struct_type)
        elif is_nullable_float_pointer_field(type, field):
            remapped_type = decay_eos_type(type)
        elif is_handle_type(decayed_type):
            remapped_type = "Ref<RefCounted>"
        else:
            remapped_type = remap_type(type, field, struct_name=struct_type)

        if is_internal_platform_specific_field(field) or fields[field].deprecated:
            continue
        elif field in count_and_variant_type_fields:
            continue
        elif is_memory_func_type(type):
            continue
        elif is_todo_field(type, field):
            continue
        elif is_platform_specific_options_field(field):
            continue
        elif is_system_initialize_options_filed(field, type):
            continue
        elif is_reserved_field(field, type):
            continue
        elif is_client_data_field(type, field):
            continue
        elif is_api_version_field(type, field):
            continue
        elif generate_config.assume_only_one_local_user and is_local_user_id(field) and need_ignore_local_user_id_struct(struct_type=struct_type):
            if struct_type == "EOS_Connect_LoginCallbackInfo":
                setget_declare_lines.append(f"\tRef<class {convert_handle_class_name(type)}> get_local_user_id() const;")
                setget_define_lines.append(
                    f"Ref<{convert_handle_class_name(type)}> {convert_to_struct_class(struct_type)}::get_local_user_id() const {{ return eos::{get_gd_type_of_local_user_id(field, type)}::get_local(); }}"
                )
            continue
        elif remapped_type == "bool":
            bind_lines.append(f"\t_BIND_PROP_BOOL({snake_field_name})")
            member_lines.append(f"\tbool {snake_field_name}{{}};")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_BOOL({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_BOOL({typename}, {snake_field_name})")
        elif is_socket_id_type(decayed_type, field):
            bind_lines.append(f"\t_BIND_PROP_STR({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STR({snake_field_name})")
            if additional_methods_requirements["set_to"]:
                member_lines.append(f"\tEOS_P2P_SocketId {snake_field_name};")
                setget_define_lines.append(f"_DEFINE_SETGET_STR_SOCKET_ID({typename}, {snake_field_name})")
            else:
                member_lines.append(f"\tCharString {snake_field_name};")
                setget_define_lines.append(f"_DEFINE_SETGET_STR_SOCKET_NAME({typename}, {snake_field_name})")
        elif is_str_type(type, field):
            bind_lines.append(f"\t_BIND_PROP_STR({snake_field_name})")
            member_lines.append(f"\tCharString {snake_field_name};")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STR({snake_field_name})")
            if not field.startswith("Socket"):
                setget_define_lines.append(f"_DEFINE_SETGET_STR({typename}, {snake_field_name})")
            else:
                setget_define_lines.append(f"_DEFINE_SETGET_STR_SOCKET_NAME({typename}, {snake_field_name})")
        elif is_str_arr_type(type, field):
            bind_lines.append(f"\t_BIND_PROP_STR_ARR({to_snake_case(field)})")
            member_lines.append(f"\tLocalVector<CharString> {snake_field_name};")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STR_ARR({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_STR_ARR({typename}, {snake_field_name})")
            if additional_methods_requirements["to"]:
                element_type: str = get_str_arr_element_type(type)
                if element_type != "const char*":
                    member_lines.append(f"\tLocalVector<{element_type}> _shadow_{snake_field_name}{{}};")
        elif is_handle_arr_type(type, ""):
            bind_lines.append(f"\t_BIND_PROP_TYPED_ARR({snake_field_name}, {convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\tTypedArray<class {convert_handle_class_name(decayed_type)}> {snake_field_name};")
            if additional_methods_requirements["to"]:
                member_lines.append(f"\tLocalVector<{decay_eos_type(type)}> _shadow_{snake_field_name}{{}};")
        elif is_handle_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_field_name}, {convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_TYPED({snake_field_name}, Ref<class {convert_handle_class_name(decayed_type)}>)")
            setget_define_lines.append(f"_DEFINE_SETGET_TYPED({typename}, {snake_field_name}, {remap_type(decayed_type, field, struct_name=struct_type)})")
            member_lines.append(f"\t{remapped_type} {snake_field_name};")
        elif is_struct_ptr(type):
            bind_lines.append(f"\t_BIND_PROP_STRUCT_PTR({snake_field_name}, {remap_type(type, struct_name=struct_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_STRUCT_PTR({remap_type(type, struct_name=struct_type)}, {snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_STRUCT_PTR({typename}, {remap_type(type, struct_name=struct_type)},  {snake_field_name})")
            member_lines.append(f"\t{decay_eos_type(type)} {snake_field_name}{{}};")
        elif is_internal_struct_arr_field(type, field, struct_type):
            bind_lines.append(f"\t_BIND_PROP_TYPED_ARR({snake_field_name}, {convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{}};")
            if additional_methods_requirements["to"]:
                member_lines.append(f"\tLocalVector<{decay_eos_type(type)}> _shadow_{snake_field_name}{{}};")
        elif is_struct_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP_OBJ({snake_field_name}, {convert_handle_class_name(decayed_type)})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{}};")
        elif is_enum_flags_type(type):
            bind_lines.append(f"\t_BIND_PROP_FLAGS({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET_FLAGS({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET_FLAGS({typename}, {snake_field_name})")
            member_lines.append(f"\tBitField<{type}> {snake_field_name}{{{type}{{}}}};")
        elif is_audio_frames_type(type, field):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\tPackedInt32Array {snake_field_name}{{}};")
            member_lines.append(f"\tLocalVector<int16_t> _shadow_{snake_field_name}{{}};")
        elif is_nullable_float_pointer_field(type, field):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ -1.0 }};")
        elif is_pure_handle_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ 0 }};")
        elif remapped_type.startswith("Ref") and not type.startswith("Ref<class ") and not is_integrated_platform_init_option_type(decayed_type):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name};")
        elif is_requested_channel_ptr_field(type, field):
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ -1 }};")
        elif type == "int32_t" and field == "ApiVersion":
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{ {get_api_latest_macro(struct_type)} }};")
        else:
            bind_lines.append(f"\t_BIND_PROP({snake_field_name})")
            setget_declare_lines.append(f"\t_DECLARE_SETGET({snake_field_name})")
            setget_define_lines.append(f"_DEFINE_SETGET({typename}, {snake_field_name})")
            member_lines.append(f"\t{remapped_type} {snake_field_name}{{}};")

        insert_doc_property(typename, snake_field_name, fields[field].doc)

    if struct_type == "EOS_PlayerDataStorage_WriteFileDataCallbackInfo":
        member_lines.append("\tPackedByteArray out_data_buffer{};")
        setget_declare_lines.append("\t_DECLARE_SETGET(out_data_buffer)")
        setget_define_lines.append(f"_DEFINE_SETGET({typename}, out_data_buffer)")
        bind_lines.append("\t_BIND_PROP(out_data_buffer)")

    if struct_type in ["EOS_Lobby_AttributeData", "EOS_Sessions_AttributeData"]:
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

    lines: list[str] = [""]
    base_class: str = "EOSIntegratedPlatformInitOptions" if is_integrated_platform_init_option_type(struct_type) else "EOSDataClass"
    lines.append(f"class {typename} : public {base_class} {{")
    lines.append(f"\tGDCLASS({typename}, {base_class})")
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
    if is_integrated_platform_init_option_type(struct_type):
        lines.append("\tvoid *to_eos_ptr() override;")
    lines.append("")
    lines.append("\tString _to_string() const;")
    lines.append("protected:")
    lines.append("\tstatic void _bind_methods();")
    lines.append("};")
    lines.append("")

    r_structs_cpp += setget_define_lines
    r_structs_cpp.append(f"void {typename}::_bind_methods() {{")
    r_structs_cpp.append(f"\t_BIND_BEGIN({typename})")
    r_structs_cpp += bind_lines
    r_structs_cpp.append("\t_BIND_END()")
    r_structs_cpp.append("}")
    r_structs_cpp.append("")

    if additional_methods_requirements["from"]:
        r_structs_cpp.append(f"Ref<{typename}> {typename}::from_eos(const {struct_type} &p_origin) {{")
        r_structs_cpp.append(f"\tRef<{typename}> ret;")
        r_structs_cpp.append("\tret.instantiate();")
        r_structs_cpp.append("\tret->set_from_eos(p_origin);")
        r_structs_cpp.append("\treturn ret;")
        r_structs_cpp.append("}")

    if additional_methods_requirements["set_from"]:
        r_structs_cpp.append(f"void {typename}::set_from_eos(const {struct_type} &p_origin) {{")
        for field in fields.keys():
            field_type: str = fields[field].type
            decayed_field_type: str = decay_eos_type(field_type)
            snake_case_field: str = to_snake_case(field)
            if is_internal_platform_specific_field(field) or fields[field].deprecated:
                continue
            if field in count_and_variant_type_fields:
                continue
            if is_todo_field(field_type, field):
                continue
            if is_api_version_field(field_type, field):
                continue
            if is_client_data_field(field_type, field):
                continue
            if is_memory_func_type(field_type):
                print_stack_and_exit(f"[struct_generator] 不支持的内存函数字段类型: '{field_type}'")
            if is_platform_specific_options_field(field):
                print_stack_and_exit(f"[struct_generator] 不支持的平台特定选项字段: '{field}'")
            elif is_system_initialize_options_filed(field, field_type):
                print_stack_and_exit(f"[struct_generator] 不支持的系统初始化选项字段: '{field}'")
            elif is_reserved_field(field, field_type):
                print_stack_and_exit(f"[struct_generator] 不支持的保留字段: '{field}'")
            elif is_nullable_float_pointer_field(field_type, field):
                print_stack_and_exit(f"[struct_generator] 不支持的可空浮点指针字段: '{field}'")
            elif generate_config.assume_only_one_local_user and is_local_user_id(field) and need_ignore_local_user_id_struct(struct_type=struct_type):
                if need_check_null_local_user_id_struct(struct_type):
                    r_structs_cpp.append(
                        f'\tif(!{get_gd_type_of_local_user_id(field, field_type)}::_is_valid_local_id(p_origin.{field})) {{ ERR_PRINT("The local user id in output struct is not compatible with existing local user!!"); }}'
                    )
            elif is_socket_id_type(decayed_field_type, field):
                if additional_methods_requirements["set_to"]:
                    r_structs_cpp.append(f"\tmemcpy(&{snake_case_field}.SocketName[0], &p_origin.{field}.SocketName[0], EOS_P2P_SOCKETID_SOCKETNAME_SIZE);")
                else:
                    r_structs_cpp.append(f"\tinternal::resize_char_string({snake_case_field}, EOS_P2P_SOCKETID_SOCKETNAME_SIZE);")
                    r_structs_cpp.append(f"\t{snake_case_field} = p_origin.{field}->SocketName;")
            elif is_str_type(field_type, field):
                assert_condition(not field.startswith("SocketName"), "[struct_generator] EOS_P2P_SocketId 不应被包装为 Godot 类")
                r_structs_cpp.append(f"\t{snake_case_field} = to_godot_type<{field_type}, CharString>(p_origin.{field});")
            elif is_str_arr_type(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_STR_ARR({snake_case_field}, p_origin.{field}, p_origin.{find_count_field(field, fields.keys())});")
            elif is_pure_handle_type(decayed_field_type):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_PURE_HANDLE({snake_case_field}, p_origin.{field});")
            elif is_requested_channel_ptr_field(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_REQUESTED_CHANNEL({snake_case_field}, p_origin.{field});")
            elif field_type.startswith("Union"):
                if is_variant_union_type(field_type, field):
                    r_structs_cpp.append(f"\t_FROM_EOS_FIELD_VARIANT_UNION({snake_case_field}, p_origin.{field});")
                else:
                    r_structs_cpp.append(f"\t_FROM_EOS_FIELD_METRICS_ACCOUNT_ID_UNION({snake_case_field}, p_origin.{field});")
            elif is_handle_arr_type(field_type, ""):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_HANDLER_ARR({snake_case_field}, {convert_handle_class_name(decayed_field_type)}, p_origin.{field}, p_origin.{find_count_field(field, fields.keys())});"
                )
            elif is_handle_type(decayed_field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_HANDLER({snake_case_field}, {convert_handle_class_name(decayed_field_type)}, p_origin.{field});")
            elif is_internal_struct_arr_field(field_type, field, struct_type):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_STRUCT_ARR({convert_to_struct_class(field_type)}, {snake_case_field}, p_origin.{field}, p_origin.{find_count_field(field, fields.keys())});"
                )
            elif is_internal_struct_field(field_type, field):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_STRUCT({snake_case_field}, p_origin.{field});")
            elif is_arr_field(field_type, field, struct_type):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_ARR({snake_case_field}, p_origin.{field}, p_origin.{find_count_field(field, fields.keys())});")
            elif is_enum_flags_type(field_type):
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD_FLAGS({snake_case_field}, p_origin.{field.split('[')[0]});")
            else:
                r_structs_cpp.append(f"\t_FROM_EOS_FIELD({snake_case_field}, p_origin.{field.split('[')[0]});")
        r_structs_cpp.append("}")

    if additional_methods_requirements["set_to"]:
        r_structs_cpp.append(f"void {typename}::set_to_eos({struct_type} &p_data) {{")
        for field in fields.keys():
            field_type = fields[field].type
            decayed_field_type: str = decay_eos_type(field_type)
            snake_field_name: str = to_snake_case(field)
            if is_internal_platform_specific_field(field) or fields[field].deprecated:
                continue
            if field in count_and_variant_type_fields:
                continue
            if is_todo_field(field_type, field):
                continue
            if field_type == "EOS_AllocateMemoryFunc":
                r_structs_cpp.append("\tp_data.AllocateMemoryFunction = &internal::_memallocate;")
            elif field_type == "EOS_ReallocateMemoryFunc":
                r_structs_cpp.append("\tp_data.ReallocateMemoryFunction = &internal::_memreallocate;")
            elif field_type == "EOS_ReleaseMemoryFunc":
                r_structs_cpp.append("\tp_data.ReleaseMemoryFunction = &internal::_memrelease;")
            else:
                if generate_config.assume_only_one_local_user and is_local_user_id(field) and need_ignore_local_user_id_struct(struct_type=struct_type):
                    interface_class: str = get_login_interface_of_local_user_id(field, type)
                    if need_check_null_local_user_id_struct(struct_type):
                        r_structs_cpp.append(
                            f'\tif({get_gd_type_of_local_user_id(field, field_type)}::_get_local_native() == nullptr) {{ ERR_PRINT("Setup \\"{typename}\\" failed: has not local user, please login by using \\"{interface_class}.login()\\" first."); }}'
                        )
                    r_structs_cpp.append(f"\tp_data.{field} = {get_gd_type_of_local_user_id(field, field_type)}::_get_local_native();")
                elif is_api_version_field(field_type, field):
                    r_structs_cpp.append(f"\tp_data.{field} = {get_api_latest_macro(struct_type)};")
                elif is_audio_frames_type(field_type, field):
                    r_structs_cpp.append(f"\t_packed_int32_to_audio_frames({snake_field_name}, _shadow_{snake_field_name});")
                    r_structs_cpp.append(f"\tp_data.{field} = _shadow_{snake_field_name}.ptr();")
                    r_structs_cpp.append(f"\tp_data.{find_count_field(field, fields.keys())} = _shadow_{snake_field_name}.size();")
                elif is_struct_ptr(field_type):
                    r_structs_cpp.append(f"\tp_data.{field} = &{snake_field_name};")
                elif is_socket_id_type(decayed_field_type, field):
                    r_structs_cpp.append(f"\t{snake_field_name}.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;")
                    r_structs_cpp.append(f"\tp_data.{field} = &{snake_field_name};")
                elif is_reserved_field(field, field_type):
                    r_structs_cpp.append(f"\tp_data.{field} = nullptr;")
                elif is_str_type(field_type, field):
                    assert_condition(not field.startswith("SocketName"), "[struct_generator] EOS_P2P_SocketId 不应出现在 set_to_eos 中")
                    r_structs_cpp.append(f"\tp_data.{field} = to_eos_type<const CharString &, {field_type}>({snake_field_name});")
                elif is_str_arr_type(field_type, field):
                    count_filed: str = find_count_field(field, fields.keys())
                    if get_str_arr_element_type(field_type) == "const char*":
                        r_structs_cpp.append(f"\tp_data.{field} = (decltype(p_data.{field})){snake_field_name}.ptr();")
                        r_structs_cpp.append(f"\tp_data.{count_filed} = {snake_field_name}.size();")
                    else:
                        r_structs_cpp.append(f"\t_TO_EOS_STR_ARR(p_data.{field}, {snake_field_name}, _shadow_{snake_field_name}, p_data.{count_filed});")
                elif is_nullable_float_pointer_field(field_type, field):
                    r_structs_cpp.append(f"\tp_data.{field} = ({snake_field_name} <= 0.0)? nullptr: (double*)(&{snake_field_name});")
                elif is_platform_specific_options_field(field):
                    r_structs_cpp.append(f"\tp_data.{field} = get_platform_specific_options();")
                elif is_system_initialize_options_filed(field, field_type):
                    r_structs_cpp.append(f"\tp_data.{field} = get_system_initialize_options();")
                elif is_pure_handle_type(decayed_field_type):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_PURE_HANDLE(p_data.{field}, {snake_field_name});")
                elif is_requested_channel_ptr_field(field_type, field):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_REQUESTED_CHANNEL(p_data.{field}, {snake_field_name});")
                elif field_type.startswith("Union"):
                    if is_variant_union_type(field_type, field):
                        r_structs_cpp.append(f"\t_TO_EOS_FIELD_VARIANT_UNION(p_data.{field}, {snake_field_name});")
                    else:
                        r_structs_cpp.append(f"\t_TO_EOS_FIELD_METRICS_ACCOUNT_ID_UNION(p_data.{field}, {snake_field_name});")
                elif is_handle_arr_type(field_type, ""):
                    r_structs_cpp.append(
                        f"\t_TO_EOS_FIELD_HANDLER_ARR(p_data.{field}, {snake_field_name}, _shadow_{snake_field_name}, p_data.{find_count_field(field, fields.keys())});"
                    )
                elif is_handle_type(decayed_field_type, field):
                    gd_type: str = convert_handle_class_name(decayed_field_type)
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_HANDLER(p_data.{field}, {snake_field_name}, {gd_type});")
                elif is_client_data_field(field_type, field):
                    print_stack_and_exit(f"[struct_generator] 不支持的 ClientData 字段: 结构体 '{struct_type}'")
                elif is_internal_struct_arr_field(field_type, field, struct_type):
                    r_structs_cpp.append(
                        f"\t_TO_EOS_FIELD_STRUCT_ARR(p_data.{field}, {snake_field_name}, _shadow_{snake_field_name}, p_data.{find_count_field(field, fields.keys())});"
                    )
                elif is_integrated_platform_init_option(struct_type, field):
                    r_structs_cpp.append(f"\tp_data.{field} = {snake_field_name}.is_valid() ? {snake_field_name}->to_eos_ptr() : nullptr;")
                elif is_internal_struct_field(field_type, field):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_STRUCT(p_data.{field}, {snake_field_name});")
                elif is_arr_field(field_type, field, struct_type):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_ARR(p_data.{field}, {snake_field_name}, p_data.{find_count_field(field, fields.keys())});")
                elif is_enum_flags_type(field_type):
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD_FLAGS(p_data.{field}, {snake_field_name});")
                elif is_callback_type(decayed_field_type):
                    cb_arg: Arg = get_callback_infos(decayed_field_type).args[0]
                    eos_cb_type: str = decay_eos_type(cb_arg.type)
                    gd_cb_type: str = remap_type(eos_cb_type).removeprefix("Ref<").removesuffix(">")
                    signal_name: str = convert_to_signal_name(decayed_field_type, "")

                    const_str_line: str = f'constexpr char {signal_name}[] = "{signal_name}";'
                    if const_str_line not in optional_cpp_lines and const_str_line not in r_structs_cpp:
                        optional_cpp_lines.append(const_str_line)

                    if field_type == "EOS_PlayerDataStorage_OnReadFileDataCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::read_file_data_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    elif field_type == "EOS_PlayerDataStorage_OnWriteFileDataCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::write_file_data_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    elif field_type == "EOS_PlayerDataStorage_OnFileTransferProgressCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::file_transfer_progress_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    elif field_type == "EOS_TitleStorage_OnReadFileDataCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::title_storage_read_file_data_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    elif field_type == "EOS_TitleStorage_OnFileTransferProgressCallback":
                        r_structs_cpp.append(f"\tp_data.{field} = &godot::eos::internal::file_transfer_progress_callback<{eos_cb_type}, {gd_cb_type}, {signal_name}>;")
                    else:
                        print_stack_and_exit(f"[struct_generator] 不支持的回调字段类型: '{field_type}'")
                else:
                    r_structs_cpp.append(f"\t_TO_EOS_FIELD(p_data.{field.split('[')[0]}, {to_snake_case(field)});")
        r_structs_cpp.append("}")
    if is_integrated_platform_init_option_type(struct_type):
        r_structs_cpp.append(f"void *{typename}::to_eos_ptr() {{")
        r_structs_cpp.append("\tset_to_eos(m_eos_data);")
        r_structs_cpp.append("\treturn &m_eos_data;")
        r_structs_cpp.append("}")

    insert_idx: int = 0
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

    insert_doc_class_brief(typename, struct_info.doc)
    insert_doc_class_description(typename)

    return lines

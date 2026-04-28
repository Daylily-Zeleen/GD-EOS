from binding_generator.doc.doc_processor import insert_doc_constant
from binding_generator.models import Enum
from binding_generator.utils.naming import (
    convert_enum_type,
    convert_enum_value,
    convert_handle_class_name,
    remove_backslash_of_last_line,
)
from binding_generator.utils.type import (
    is_enum_flags_type,
    is_need_skip_enum_type,
    is_need_skip_enum_value,
)


def gen_enums(macro_suffix: str, handle_class: str, enums: dict[str, Enum]) -> str:
    lines: list[str] = ["#pragma once"]
    lines.append("")
    converted_handle_class: str = convert_handle_class_name(handle_class)

    for enum_type in enums:
        if is_need_skip_enum_type(enum_type):
            continue
        if enums[enum_type].deprecated:
            continue
        lines.append(f"#define _BIND_ENUM_{enum_type}()\\")
        if is_enum_flags_type(enum_type):
            for e_info in enums[enum_type].members:
                e: str = e_info.name
                if is_need_skip_enum_value(enum_type, e):
                    continue
                if e_info.deprecated:
                    continue
                lines.append(f'\t_BIND_ENUM_BITFIELD_FLAG({enum_type}, {e}, "{convert_enum_value(e)}")\\')
                insert_doc_constant(converted_handle_class, convert_enum_value(e), e_info.doc)
        else:
            for e_info in enums[enum_type].members:
                e = e_info.name
                if is_need_skip_enum_value(enum_type, e):
                    continue
                if e_info.deprecated:
                    continue
                lines.append(f'\t_BIND_ENUM_CONSTANT({enum_type}, {e}, "{convert_enum_value(e)}")\\')
                insert_doc_constant(converted_handle_class, convert_enum_value(e), e_info.doc)
        remove_backslash_of_last_line(lines)
        lines.append("")

    lines.append(f"#define _BIND_ENUMS_{macro_suffix}()\\")
    for enum_type in enums:
        if is_need_skip_enum_type(enum_type):
            continue
        if enums[enum_type].deprecated:
            continue
        lines.append(f"\t_BIND_ENUM_{enum_type}()\\")
    remove_backslash_of_last_line(lines)
    lines.append("")

    lines.append(f"#define _USING_ENUMS_{macro_suffix}()\\")
    for enum_type in enums:
        if is_need_skip_enum_type(enum_type):
            continue
        if enums[enum_type].deprecated:
            continue
        lines.append(f"\tusing {convert_enum_type(enum_type)} = {enum_type};\\")
    remove_backslash_of_last_line(lines)
    lines.append("")

    lines.append(f"#define _CAST_ENUMS_{macro_suffix}()\\")
    for enum_type in enums:
        if is_need_skip_enum_type(enum_type):
            continue
        if enums[enum_type].deprecated:
            continue
        if is_enum_flags_type(enum_type):
            lines.append(f"\tVARIANT_BITFIELD_CAST(godot::eos::{converted_handle_class}::{convert_enum_type(enum_type)})\\")
        else:
            lines.append(f"\tVARIANT_ENUM_CAST(godot::eos::{converted_handle_class}::{convert_enum_type(enum_type)})\\")
    remove_backslash_of_last_line(lines)
    lines.append("")

    return "\n".join(lines)

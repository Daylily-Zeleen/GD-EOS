# 文档处理器

import os

from binding_generator.config import generate_config, project_root
from binding_generator.context import (
    doc_keyword_map_callback,
    doc_keyword_map_constant,
    doc_keyword_map_enum,
    doc_keyword_map_enum_member,
    doc_keyword_map_method,
    doc_keyword_map_struct,
    handles,
    structs,
)
from binding_generator.models import (
    Callback,
    Constant,
    Enum,
    Handle,
    Method,
    Struct,
    StructField,
)
from binding_generator.utils.naming import (
    convert_constant_as_method_name,
    convert_constant_name,
    convert_enum_type,
    convert_enum_value,
    convert_method_name,
    convert_prefix_tab,
    convert_to_signal_name,
    to_snake_case,
)
from binding_generator.utils.type import (
    convert_handle_class_name,
    convert_to_struct_class,
    decay_eos_type,
    find_count_and_variant_type_fields_in_struct,
    get_callback_infos,
    get_struct_fields,
    is_expanded_struct,
)


def _optimize_doc(doc: list[str]) -> list[str]:
    ret: list[str] = []
    in_details: bool = False
    for i in range(len(doc)):
        if doc[i].lstrip().startswith("@"):
            line: str = doc[i].lstrip()
            if line.startswith("@see"):
                see_type: str = line.removeprefix("@see").strip()
                if see_type.endswith("_Release"):
                    continue
                if "RemoveNotify" in see_type:
                    continue
                elif is_expanded_struct(see_type):
                    continue
            elif generate_config.assume_only_one_local_user and line.startswith("@param LocalUserId"):
                continue
            elif line.startswith("@param ClientData"):
                continue

        if len(ret) <= 0:
            ret.append(doc[i])
            in_details = False
        elif len(doc[i].strip()) <= 0:
            in_details = False
        elif doc[i].lstrip().startswith("@"):
            ret.append(doc[i])
            in_details = False
        elif doc[i].removeprefix(" ").startswith("\t"):
            ret.append(doc[i])
            in_details = False
        elif _is_int_str(doc[i].lstrip().split(".")[0].strip()):
            ret.append(doc[i])
            in_details = False
        else:
            last_idx: int = len(ret) - 1
            if not in_details:
                if ret[last_idx].rstrip().endswith(":"):
                    in_details = True
            if in_details:
                ret.append(doc[i])
            else:
                ret[last_idx] = ret[last_idx].rstrip() + doc[i]
    return ret


def _is_int_str(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        return False


def preprocess_docs():
    for h in handles:
        h_info: Handle = handles[h]
        h_class: str = convert_handle_class_name(h)
        for m in h_info.methods:
            doc_keyword_map_method[m] = {
                "class": h_class,
                "name": convert_method_name(m, h),
            }
        for e in h_info.enums:
            doc_keyword_map_enum[e] = {
                "class": h_class,
                "name": convert_enum_type(e),
            }
            for e_member in h_info.enums[e].members:
                doc_keyword_map_enum_member[e_member.name] = {
                    "class": h_class,
                    "name": convert_enum_value(e_member.name),
                }
        for c in h_info.constants:
            from binding_generator.utils.type import is_string_constant

            as_method: bool = is_string_constant(c)
            doc_keyword_map_constant[c] = {
                "class": h_class,
                "name": convert_constant_as_method_name(c) if as_method else convert_constant_name(c),
                "as_method": as_method,
            }
        for cb in h_info.callbacks:
            doc_keyword_map_callback[cb] = {
                "class": h_class,
                "name": convert_to_signal_name(cb),
            }

    for s in structs:
        if structs[s].deprecated:
            continue
        doc_keyword_map_struct[s] = convert_to_struct_class(s)

    for struct in structs:
        struct_info: Struct = structs[struct]
        struct_info.doc = _optimize_doc(struct_info.doc)
        for field in struct_info.fields:
            field_info: StructField = struct_info.fields[field]
            field_info.doc = _optimize_doc(field_info.doc)

    for h in handles:
        handle_info: Handle = handles[h]
        handle_info.doc = _optimize_doc(handle_info.doc)
        for m in handle_info.methods:
            m_info: Method = handle_info.methods[m]
            m_info.doc = _optimize_doc(m_info.doc)
        for cb in handle_info.callbacks:
            cb_info: Callback = handle_info.callbacks[cb]
            cb_info.doc = _optimize_doc(cb_info.doc)
        for et in handle_info.enums:
            et_info: Enum = handle_info.enums[et]
            et_info.doc = _optimize_doc(et_info.doc)
            for e_info in handle_info.enums[et].members:
                e_info.doc = _optimize_doc(e_info.doc)
        for c in handle_info.constants:
            c_info: Constant = handle_info.constants[c]
            c_info.doc = _optimize_doc(c_info.doc)


def make_callback_doc(callback_type: str) -> list[str]:
    info: Callback = get_callback_infos(callback_type)
    ret: list[str] = []
    for arg in info.args:
        name: str = arg.name
        type: str = arg.type
        decayed_type: str = decay_eos_type(type)
        if not is_expanded_struct(decayed_type):
            doc: list[str] = structs[decayed_type].doc
            snake_name: str = to_snake_case(name)
            if len(doc) == 1:
                doc_line: str = doc[0].lstrip("\t")
                ret.append(f"{snake_name} ({decayed_type}): {doc_line}")
            else:
                ret.append(f"{snake_name} ({decayed_type}):\n")
                for doc_line in doc:
                    ret.append(f"\t{doc_line}")
        else:
            arg_fields: dict[str, StructField] = get_struct_fields(decayed_type)
            count_and_variant_type_fields: list[str] = find_count_and_variant_type_fields_in_struct(decayed_type)
            for f in arg_fields:
                if f in count_and_variant_type_fields:
                    continue
                info_f: StructField = arg_fields[f]
                doc = info_f.doc
                f_type: str = decay_eos_type(info_f.type)
                f_snake_name: str = to_snake_case(f)
                if f_type.startswith("void") and f == "ClientData":
                    continue
                if len(doc) == 1:
                    doc_line = doc[0].lstrip("\t")
                    ret.append(f"{f_snake_name} ({f_type}): {doc_line}")
                else:
                    ret.append(f"{f_snake_name} ({f_type}):\n")
                    for doc_line in info_f.doc:
                        ret.append(f"\t{doc_line}\n")
    ret.append("")
    return ret


def insert_doc_class_description(typename: str, doc: list[str] = []):
    lines: list[str] = _get_doc_file(typename=typename)
    if len(lines) == 0:
        return
    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line: str = lines[i]
        indent_count = 0
        while line.startswith("\t"):
            indent_count += 1
            line = line.removeprefix("\t")
        if line.startswith("<description>"):
            insert_idx = i + 1
            indent_count += 1
            break
    if insert_idx < 0:
        return
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</description>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]
    doc = doc.copy()
    doc.insert(
        0,
        "[b]CAUTIOUS[/b]: This document is extracted from EOS C SDK, there have some differences between the EOS C SDK and this GDScript SDK APIs.\n",
    )
    doc.insert(1, "[b]NOTE: Keep in mind that this document is for reference only.[/b]\n")
    _insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    _store_doc_file(typename=typename, content=lines)


def insert_doc_class_brief(typename: str, doc: list[str]):
    lines: list[str] = _get_doc_file(typename=typename)
    if len(lines) == 0:
        return
    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line: str = lines[i]
        indent_count = 0
        while line.startswith("\t"):
            indent_count += 1
            line = line.removeprefix("\t")
        if line.startswith("<brief_description>"):
            insert_idx = i + 1
            indent_count += 1
            break
    if insert_idx < 0:
        return
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</brief_description>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]
    _insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    _store_doc_file(typename=typename, content=lines)


def insert_doc_property(typename: str, prop: str, doc: list[str]):
    lines: list[str] = _get_doc_file(typename=typename)
    if len(lines) == 0:
        return
    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line: str = lines[i]
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
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</member>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]
    _insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    _store_doc_file(typename=typename, content=lines)


def insert_doc_constant(typename: str, constant: str, doc: list[str]):
    lines: list[str] = _get_doc_file(typename=typename)
    if len(lines) == 0:
        return
    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line: str = lines[i]
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
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</constant>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]
    _insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    _store_doc_file(typename=typename, content=lines)


# 过滤直接返回字符串的接口文档：移除 @return 及 Success/LimitExceeded 描述，保留其他错误码说明
def _filter_str_result_doc(doc: list[str]) -> list[str]:
    ret: list[str] = []
    error_lines: list[str] = []
    skip_return: bool = False
    for doc_line in doc:
        stripped: str = doc_line.lstrip()
        if stripped.startswith("@return"):
            skip_return = True
            continue
        if skip_return:
            if stripped.startswith("@"):
                skip_return = False
            else:
                lower: str = stripped.lower()
                if "eos_success" in lower or "success" in lower or "limitexceeded" in lower or "limit_exceeded" in lower:
                    continue
                error_lines.append(doc_line)
                continue
        ret.append(doc_line)
    ret.append("@return If an empty String is returned, use [method EOS.get_last_result_code] to check the error code.\n")
    ret.extend(error_lines)
    return ret


def insert_doc_method(
    typename: str,
    method: str,
    doc: list[str],
    additional_args_doc: dict[str, list[str]] = {},
    additional_doc: list[str] = [],
    is_str_result_method: bool = False,
):
    if is_str_result_method:
        doc = _filter_str_result_doc(doc)
    _insert_doc_method_like("method", typename, method, doc, additional_args_doc, additional_doc)


def insert_doc_signal(
    typename: str,
    signal: str,
    doc: list[str],
    additional_args_doc: dict[str, list[str]] = {},
    additional_doc: list[str] = [],
):
    _insert_doc_method_like("signal", typename, signal, doc, additional_args_doc, additional_doc)


def _insert_doc_method_like(
    tag: str,
    typename: str,
    name: str,
    doc: list[str],
    additional_args_doc: dict[str, list[str]],
    additional_doc: list[str] = [],
):
    lines: list[str] = _get_doc_file(typename=typename)
    if len(lines) == 0:
        return
    insert_idx: int = -1
    indent_count: int = 0
    for i in range(len(lines)):
        line: str = lines[i]
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
    line = lines[insert_idx]
    while not line.lstrip("\t").startswith("</description>"):
        lines.pop(insert_idx)
        line = lines[insert_idx]
    _insert_doc_to(typename, lines, insert_idx, doc, indent_count)
    if len(additional_args_doc) > 0:
        insert_idx += len(doc)
        _insert_doc_to(
            typename,
            lines,
            insert_idx,
            ["-------------- Arguments Additional Descriptions --------------\n"],
            indent_count,
        )
        insert_idx += 1
        for arg in additional_args_doc:
            arg_doc: list[str] = additional_args_doc[arg].copy()
            for i in range(len(arg_doc)):
                if len(arg_doc[i].strip()):
                    arg_doc[i] = "\t" + arg_doc[i]
            arg_snake_name: str = to_snake_case(arg)
            if len(arg_doc) == 1:
                arg_doc[0] = f"{arg_snake_name}: " + arg_doc[0].lstrip("\t")
            else:
                arg_doc.insert(0, f"{arg_snake_name}:\n")
            _insert_doc_to(typename, lines, insert_idx, arg_doc, indent_count)
            insert_idx += len(arg_doc)
    if len(additional_doc) > 0:
        _insert_doc_to(
            typename,
            lines,
            insert_idx,
            ["-------------- Additional Descriptions --------------\n"],
            indent_count,
        )
        insert_idx += 1
        additional_doc_copy: list[str] = additional_doc.copy()
        additional_doc_copy.insert(0, "\n")
        _insert_doc_to(typename, lines, insert_idx, additional_doc, indent_count)
        insert_idx += len(additional_doc_copy)
    _store_doc_file(typename=typename, content=lines)


_sorted_keys_cache: dict[int, list[str]] = {}


def _get_sorted_descending_keys(d: dict) -> list[str]:
    cache_key = id(d)
    if cache_key in _sorted_keys_cache:
        return _sorted_keys_cache[cache_key]
    ret: list[str] = list(d.keys())
    ret.sort(key=len, reverse=True)
    _sorted_keys_cache[cache_key] = ret
    return ret


def _insert_doc_to(typename: str, lines: list[str], insert_idx: int, doc: list[str], indent_count: int) -> list[str]:
    for line in doc:
        line = convert_prefix_tab(line)
        if len(line.strip()) != 0:
            for i in range(indent_count):
                line = "\t" + line
        for m in _get_sorted_descending_keys(doc_keyword_map_method):
            m_options: str = m + "Options"
            if m_options in line:
                mapped: str = f"[{doc_keyword_map_struct[m_options]}]"
                line = line.replace(m_options, mapped)
            m_callback_info: str = m + "CallbackInfo"
            if m_callback_info in line:
                mapped = f"[{doc_keyword_map_struct[m_callback_info]}]"
                line = line.replace(m_callback_info, mapped)
            splits: list[str] = m.split("_")
            splits[len(splits) - 1] = "On" + splits[len(splits) - 1] + "Callback"
            m_callback: str = "_".join(splits)
            if m_callback in line:
                data: dict[str, str] = doc_keyword_map_callback[m_callback]
                klass: str = data["class"]
                name: str = data["name"]
                replace_keyword: str = ""
                if klass == typename:
                    replace_keyword = f"[signal {name}]"
                else:
                    replace_keyword = f"[signal {klass}.{name}]"
                line = line.replace(m_callback, replace_keyword)
            if m in line:
                data = doc_keyword_map_method[m]
                klass = data["class"]
                name = data["name"]
                replace_keyword = ""
                if klass == typename:
                    replace_keyword = f"[method {name}]"
                else:
                    replace_keyword = f"[method {klass}.{name}]"
                line = line.replace(m, replace_keyword)
        for em in _get_sorted_descending_keys(doc_keyword_map_enum_member):
            if em not in line:
                continue
            data = doc_keyword_map_enum_member[em]
            klass = data["class"]
            name = data["name"]
            replace_keyword = ""
            if klass == typename:
                replace_keyword = f"[constant {name}]"
            else:
                replace_keyword = f"[constant {klass}.{name}]"
            line = line.replace(em, replace_keyword)
        for e in _get_sorted_descending_keys(doc_keyword_map_enum):
            if e not in line:
                continue
            data = doc_keyword_map_enum[e]
            klass = data["class"]
            name = data["name"]
            replace_keyword = ""
            if klass == typename:
                replace_keyword = f"[enum {name}]"
            else:
                replace_keyword = f"[enum {klass}.{name}]"
            line = line.replace(e, replace_keyword)
        for c in _get_sorted_descending_keys(doc_keyword_map_constant):
            if c not in line:
                continue
            data = doc_keyword_map_constant[c]
            klass = data["class"]
            name = data["name"]
            as_method: bool = data["as_method"]
            replace_keyword = ""
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
        for s in _get_sorted_descending_keys(doc_keyword_map_struct):
            if s not in line:
                continue
            mapped = f"[{doc_keyword_map_struct[s]}]"
            line = line.replace(s, mapped)
        lines.insert(insert_idx, line)
        insert_idx += 1
    return lines


def _get_doc_file(typename: str) -> list[str]:
    try:
        f = open(
            os.path.join(project_root, "doc_classes", typename) + ".xml",
            "r",
            encoding="utf-8",
        )
        ret: list[str] = f.readlines()
        f.close()
        return ret
    except Exception:
        return []


def _store_doc_file(typename: str, content: list[str]):
    try:
        f = open(
            os.path.join(project_root, "doc_classes", typename) + ".xml",
            "w",
            encoding="utf-8",
        )
        f.writelines(content)
        f.close()
    except Exception:
        return

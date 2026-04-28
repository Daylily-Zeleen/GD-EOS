# EOS SDK 头文件解析器

import os
import re

from binding_generator.config import sdk_include_dir
from binding_generator.context import api_latest_macros
from binding_generator.models import (
    Arg,
    Callback,
    Constant,
    Enum,
    EnumMember,
    FileInfo,
    Handle,
    Method,
    Struct,
    StructField,
)
from binding_generator.utils.naming import convert_to_interface_lower
from binding_generator.utils.type import is_need_skip_constant, is_special_builtin_type

_deferred_include_enums: list[tuple[str, str, str]] = []


def _is_doc_deprecated(doc: list[str]) -> bool:
    for line in doc:
        stripped: str = line.strip()
        lower: str = stripped.lower()
        if lower.startswith("deprecated") or lower.startswith("- deprecated") or lower.startswith("* deprecated"):
            return True
        if stripped.startswith("DEPRECATED"):
            return True
        if " is deprecated" in lower or " are deprecated" in lower:
            return True
    return False


_DEPRECATED_SPECIAL_NAMES: set[str] = {
    "EOS_ConsoleInit_OnNetworkRequestedDeprecatedCallbackNotSet",
}


def _is_deprecated(name: str, doc: list[str], is_deprecated_file: bool = False) -> bool:
    return is_deprecated_file or _is_doc_deprecated(doc) or name.endswith("_DEPRECATED") or name in _DEPRECATED_SPECIAL_NAMES


def _parse_enum_members_from_include(include_path: str, enum_obj: Enum):
    fp: str = os.path.join(sdk_include_dir, include_path)
    if not os.path.exists(fp):
        return
    f = open(fp, "r")
    lines: list[str] = f.readlines()
    f.close()
    for i in range(len(lines)):
        line: str = lines[i].strip()
        if not line or line.startswith("//") or line.startswith("/*") or line.startswith("*"):
            continue
        m = re.match(r"^(\w+)\((.+)\)\s*$", line)
        if not m:
            continue
        args_str: str = m.group(2)
        args: list[str] = [a.strip() for a in args_str.split(",")]
        if len(args) >= 3:
            member_name: str = args[0] + args[1]
        elif len(args) == 2:
            if args[0].endswith("_"):
                member_name = args[0] + args[1]
            else:
                member_name = args[0]
        else:
            continue
        doc: list[str] = _extract_doc(lines, i - 1)
        enum_obj.members.append(EnumMember(name=member_name, doc=doc, deprecated=_is_deprecated(member_name, doc)))


def _extract_doc(lines: list[str], idx: int, skip_defines: bool = False) -> list[str]:
    doc: list[str] = []
    while idx >= 0:
        ori_line: str = lines[idx]
        if ori_line.strip() == "":
            # 访问到空行，停止向上解析
            break

        line: str = ori_line.lstrip("\t")
        valid_comment_line: bool = False
        for prefix in [" */", "//", "/**", " *"]:
            if line.startswith(prefix):
                line = line.removeprefix(prefix).removeprefix(" ")
                valid_comment_line = True
                break

        if valid_comment_line:
            prefix_space_count: int = 0
            while line.startswith(" "):
                prefix_space_count += 1
                line = line.removeprefix(" ")
            line = line.replace("*/\n", "\n")
            for _i in range(divmod(prefix_space_count, 4)[0]):
                line = "\t" + line
            doc.append(line)
            idx -= 1
        elif skip_defines and len(doc) == 0 and line.startswith("#define"):
            idx -= 1
        else:
            break
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


_SKIP_INCLUDES: set[str] = {
    "eos_common.h",
    "eos_base.h",
    "eos_result.h",
    "eos_platform_prereqs.h",
    "eos_version.h",
    "eos_init.h",
    "eos_sdk.h",
}


def parse_file(
    interface_lower: str,
    fp: str,
    r_file_lower2infos: dict[str, FileInfo],
    is_deprecated_file: bool = False,
    _visited: set[str] | None = None,
    _skip_includes: bool = False,
):
    if _visited is None:
        _visited = set()
    abs_fp: str = os.path.abspath(fp)
    if abs_fp in _visited:
        return
    _visited.add(abs_fp)

    f = open(fp, "r")
    lines: list[str] = f.readlines()
    f.close()
    i: int = 0
    while i < len(lines):
        line: str = lines[i]
        if len(r_file_lower2infos[interface_lower].interface_doc) <= 0:
            if line.startswith("/**") and not line.strip().endswith("*/"):
                is_interface_doc: bool = False
                for j in range(i, len(lines)):
                    if lines[j].startswith(" * @see EOS_Platform_Get") and lines[j].strip().endswith("Interface"):
                        is_interface_doc = True
                    if lines[j].startswith(" */"):
                        if is_interface_doc:
                            i = j + 1
                            r_file_lower2infos[interface_lower].interface_doc = _extract_doc(lines, j)
                            break
                    if len(lines[j].strip()) == 0:
                        doc: list[str] = _extract_doc(lines, j - 1)
                        if len(doc) <= 0:
                            break
                        from binding_generator.utils.naming import (
                            convert_interface_class_name,
                        )

                        interface_type: str = convert_interface_class_name(interface_lower)
                        if interface_type != "EOS":
                            interface_type = interface_type.removeprefix("EOS")
                        doc.append("\n")
                        doc.append(f"@see EOS_Platform_Get{interface_type}Interface\n")
                        i = j
                        r_file_lower2infos[interface_lower].interface_doc = doc
                        break

        if line.startswith("#include"):
            if _skip_includes:
                i += 1
                continue
            include_match = re.search(r'"([^"]+)"', line)
            if include_match:
                include_name: str = include_match.group(1)
                if include_name in _SKIP_INCLUDES:
                    i += 1
                    continue
                if include_name.endswith("_types.h"):
                    main_header: str = include_name.removesuffix("_types.h") + ".h"
                    main_header_il: str = convert_to_interface_lower(main_header)
                    if main_header_il != interface_lower and os.path.exists(os.path.join(sdk_include_dir, main_header)):
                        i += 1
                        continue
                include_fp: str = os.path.join(sdk_include_dir, include_name)
                if os.path.exists(include_fp):
                    include_deprecated: bool = "deprecated" in include_name
                    saved_interface_doc: list[str] = r_file_lower2infos[interface_lower].interface_doc
                    parse_file(
                        interface_lower,
                        include_fp,
                        r_file_lower2infos,
                        is_deprecated_file=is_deprecated_file or include_deprecated,
                        _visited=_visited,
                    )
                    if include_deprecated:
                        r_file_lower2infos[interface_lower].interface_doc = saved_interface_doc
            i += 1
            continue

        if line.startswith("#define EOS_") and "_API_LATEST" in line:
            macro: str = line.split(" ", 2)[1]
            api_latest_macros.add(macro)
            i += 1
            continue

        if line.startswith("#define EOS_"):
            text: str = line.strip().split(" ", 1)[1]
            splits: list[str] = []
            if len(text.split(" ", 1)) > 1 and "(" not in text.split(" ", 1)[0]:
                splits = text.split(" ", 1)
            if len(text.split("\t", 1)) > 1 and "(" not in text.split(" ", 1)[0]:
                splits = text.split("\t", 1)
            if splits:
                for j in range(len(splits)):
                    splits[j] = splits[j].strip()
                if not is_need_skip_constant(splits[0]):
                    doc: list[str] = _extract_doc(lines, i - 1, skip_defines=True)
                    r_file_lower2infos[interface_lower].constants[splits[0]] = Constant(
                        name=splits[0],
                        value=splits[1],
                        doc=doc,
                        deprecated=_is_deprecated(splits[0], doc, is_deprecated_file),
                    )

        if "typedef struct " in line:
            handle_type: str = line.split("* ", 1)[1].split(";", 1)[0]
            r_file_lower2infos[interface_lower].handles[handle_type] = Handle(
                name=handle_type,
                doc=_extract_doc(lines, i - 1),
            )
            i += 1
            continue

        if line.startswith("EOS_ENUM_START("):
            enum_type: str = line.strip().split("(")[1].rstrip(")").rstrip(";").strip()
            j: int = i + 1
            while j < len(lines):
                next_line: str = lines[j].strip()
                if next_line.startswith("#include"):
                    include_match = re.search(r'"([^"]+)"', next_line)
                    if include_match:
                        _deferred_include_enums.append((interface_lower, enum_type, include_match.group(1)))
                    j += 1
                elif next_line.startswith("EOS_ENUM_END") or next_line.startswith("EOS_ENUM_BOOLEAN_OPERATORS"):
                    j += 1
                else:
                    break
            i = j
            continue

        if line.startswith("EOS_ENUM(") and line.split("(")[0] not in [
            "EOS_ENUM_START",
            "EOS_ENUM_END",
            "EOS_ENUM_BOOLEAN_OPERATORS",
        ]:
            enum_type: str = line.split("(")[1].rsplit(",")[0]
            enum_doc: list[str] = _extract_doc(lines, i - 1)
            enum_obj: Enum = Enum(
                name=enum_type,
                doc=enum_doc,
                deprecated=_is_deprecated(enum_type, enum_doc, is_deprecated_file),
            )
            r_file_lower2infos[interface_lower].enums[enum_type] = enum_obj
            i += 1
            while not lines[i].startswith(");"):
                line = lines[i].lstrip("\t").rstrip("\n").rstrip(",")
                if len(line) <= 0 or line.startswith(" ") or line.startswith("/"):
                    i += 1
                    continue
                splits = line.split(" = ")
                member_doc: list[str] = _extract_doc(lines, i - 1)
                enum_obj.members.append(
                    EnumMember(
                        name=splits[0],
                        doc=member_doc,
                        deprecated=_is_deprecated(splits[0], member_doc),
                    )
                )
                i += 1
            i += 1
            continue

        elif line.startswith("EOS_DECLARE_FUNC"):
            method_name: str = line.split(") ", 1)[1].split("(")[0]
            method_doc: list[str] = _extract_doc(lines, i - 1)
            method_obj: Method = Method(
                name=method_name,
                return_type=line.split("(", 1)[1].split(")")[0],
                doc=method_doc,
                deprecated=_is_deprecated(method_name, method_doc, is_deprecated_file),
            )
            args: list[str] = line.split(" ", 1)[1].split("(", 1)[1].rsplit(")", 1)[0].split(", ")
            for a in args:
                if len(a) <= 0:
                    continue
                splits = a.rsplit(" ", 1)
                if splits[0] == "void":
                    continue
                method_obj.args.append(Arg(type=splits[0], name=splits[1]))
            r_file_lower2infos[interface_lower].methods[method_name] = method_obj
            i += 1
            continue

        elif line.startswith("EOS_DECLARE_CALLBACK"):
            has_return: bool = line.startswith("EOS_DECLARE_CALLBACK_RETVALUE")
            args = line.split("(", 1)[1].rsplit(")")[0].split(", ")
            callback_name: str = args[1] if has_return else args[0]
            callback_doc: list[str] = _extract_doc(lines, i - 1)
            callback_obj: Callback = Callback(
                name=callback_name,
                return_type=args[0] if has_return else "",
                doc=callback_doc,
                deprecated=_is_deprecated(callback_name, callback_doc, is_deprecated_file),
            )
            for arg_idx in range((2 if has_return else 1), len(args)):
                a: str = args[arg_idx]
                callback_obj.args.append(Arg(type=a.rsplit(" ", 1)[0], name=a.rsplit(" ", 1)[1]))
            r_file_lower2infos[interface_lower].callbacks[callback_name] = callback_obj
            i += 1
            continue

        elif line.startswith("EOS_STRUCT"):
            struct_name: str = line.lstrip("EOS_STRUCT").lstrip("(").rstrip("\n").rstrip(", (")
            struct_doc: list[str] = _extract_doc(lines, i - 1)
            struct_obj: Struct = Struct(
                name=struct_name,
                doc=struct_doc,
                deprecated=_is_deprecated(struct_name, struct_doc, is_deprecated_file),
            )
            r_file_lower2infos[interface_lower].structs[struct_name] = struct_obj
            i += 1
            while not lines[i].startswith("));"):
                line = lines[i].lstrip("\t").rstrip("\n")
                if line.startswith("/") or line.startswith("*") or line.startswith(" ") or len(line) == 0:
                    i += 1
                    continue
                line = line.rsplit(";")[0]
                field_doc = _extract_doc(lines, i - 1)
                if line.startswith("union"):
                    union_fields: dict[str, str] = {}
                    i += 2
                    while not lines[i].lstrip("\t").startswith("}"):
                        line = lines[i].lstrip("\t").rstrip("\n")
                        if line.startswith("/") or line.startswith("*") or line.startswith(" ") or len(line) == 0:
                            i += 1
                            continue
                        line = line.rsplit(";")[0]
                        splits = line.rsplit(" ", 1)
                        if len(splits) != 2:
                            print(f"[header_parser] 联合体字段解析失败: {fp}:{i}")
                            print(f"[header_parser] 原始行: {lines[i]}")
                        else:
                            union_fields[splits[1]] = splits[0]
                        i += 1
                    union_type: str = "Union{"
                    for union_f in union_fields.keys():
                        union_type += f"{union_fields[union_f]} : {union_f}, "
                    union_type = union_type.rstrip(" ").rstrip(",") + "}"
                    field: str = lines[i].lstrip("\t").lstrip("}").lstrip(" ").rstrip("\n").rstrip(";")
                    struct_obj.fields[field] = StructField(
                        type=union_type,
                        doc=field_doc,
                        deprecated=_is_deprecated(field, field_doc),
                    )
                else:
                    splits = line.rsplit(" ", 1)
                    if len(splits) != 2:
                        print(f"[header_parser] 结构体字段解析失败: {fp}:{i}")
                        print(f"[header_parser] 原始行: {lines[i]}")
                    else:
                        struct_obj.fields[splits[1]] = StructField(
                            type=splits[0],
                            doc=field_doc,
                            deprecated=_is_deprecated(splits[1], field_doc),
                        )
                i += 1
            if is_special_builtin_type(struct_name):
                r_file_lower2infos[interface_lower].structs.pop(struct_name)
            i += 1
            continue
        else:
            i += 1
            continue


def parse_deferred_include_enums(r_file_lower2infos: dict[str, FileInfo]):
    for interface_lower, enum_type, include_path in _deferred_include_enums:
        enum_obj: Enum = Enum(name=enum_type, doc="")
        _parse_enum_members_from_include(include_path, enum_obj)
        r_file_lower2infos[interface_lower].enums[enum_type] = enum_obj
    _deferred_include_enums.clear()

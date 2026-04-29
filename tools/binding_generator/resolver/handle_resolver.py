# 句柄类型解析器

import os

from binding_generator.config import sdk_include_dir
from binding_generator.context import (
    generate_infos,
    handles,
    interfaces,
    release_methods,
    structs,
    unhandled_callbacks,
    unhandled_constants,
    unhandled_enums,
    unhandled_infos,
    unhandled_methods,
)
from binding_generator.models import (
    Arg,
    FileInfo,
    Handle,
    Method,
)
from binding_generator.parser.header_parser import (
    parse_deferred_include_enums,
    parse_file,
)
from binding_generator.utils.naming import (
    convert_interface_class_name,
    convert_to_interface_lower,
    decay_eos_type,
)
from binding_generator.utils.common import assert_condition
from binding_generator.utils.type import (
    is_callback_type_name,
    is_handle_type,
)

_SPECIAL_METHOD_MAPPINGS: dict[str, str] = {
    "EOS_EpicAccountId_FromString": "EOS_EpicAccountId",
    "EOS_ProductUserId_FromString": "EOS_ProductUserId",
    "EOS_Platform_Create": "EOS_HPlatform",
}

_SPECIAL_CALLBACK_MAPPINGS: dict[str, str] = {
    "EOS_TitleStorage_OnReadFileDataCallback": "EOS_HTitleStorageFileTransferRequest",
    "EOS_TitleStorage_OnFileTransferProgressCallback": "EOS_HTitleStorageFileTransferRequest",
    "EOS_PlayerDataStorage_OnReadFileDataCallback": "EOS_HPlayerDataStorageFileTransferRequest",
    "EOS_PlayerDataStorage_OnWriteFileDataCallback": "EOS_HPlayerDataStorageFileTransferRequest",
    "EOS_PlayerDataStorage_OnFileTransferProgressCallback": "EOS_HPlayerDataStorageFileTransferRequest",
}

_CONSTANT_PREFIX_TO_HANDLE: dict[str, str] = {
    "IPT": "EOS_HIntegratedPlatform",
    "ANTICHEATCOMMON": "EOS_HAntiCheatCommon",
}

_INTERFACE_LOWER_TO_HANDLE: dict[str, str] = {
    "anticheatcommon": "EOS_HAntiCheatCommon",
}

# 枚举路由到 EOS（全局）的 interface_lower 集合
_GLOBAL_ENUM_FILES: set[str] = {
    "platform",
    "common",
}

# 常量路由到 EOS（全局）的 interface_lower 集合
# 注意：platform（eos_types.h）的常量属于 EOS_HPlatform，不应路由到 EOS
_GLOBAL_CONSTANT_FILES: set[str] = {
    "common",
}


def _find_handle_by_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    handle_candidate: str = "EOS_H" + prefix
    if handle_candidate in handles:
        return handle_candidate
    return ""


def _extract_constant_prefix(constant_name: str) -> str:
    if not constant_name.startswith("EOS_"):
        return ""
    rest: str = constant_name[4:]
    for i in range(len(rest)):
        if rest[i] == "_":
            return rest[:i]
    return ""


def _extract_method_interface(method_name: str) -> str:
    if not method_name.startswith("EOS_"):
        return ""
    rest: str = method_name[4:]
    for i in range(len(rest)):
        if rest[i] == "_":
            return rest[:i]
    return ""


def _cheat_as_handle_method(method_name: str) -> str:
    if method_name in _SPECIAL_METHOD_MAPPINGS:
        return _SPECIAL_METHOD_MAPPINGS[method_name]
    interface_prefix: str = _extract_method_interface(method_name)
    if interface_prefix:
        handle: str = _find_handle_by_prefix(interface_prefix)
        if handle:
            return handle
    return "EOS"


def _find_best_match_handle_for_enum(enum_type: str) -> str:
    if not enum_type.startswith("EOS_E"):
        return ""
    enum_prefix: str = enum_type[5:]
    best_match: str = ""
    best_len: int = 0
    for handle_name in handles:
        if not handle_name.startswith("EOS_H"):
            continue
        handle_prefix: str = handle_name[5:]
        if enum_prefix.startswith(handle_prefix):
            if len(handle_prefix) > best_len:
                best_len = len(handle_prefix)
                best_match = handle_name
    return best_match


def _cheat_as_handle_enum(enum_type: str) -> str:
    handle: str = _find_best_match_handle_for_enum(enum_type)
    if handle:
        return handle
    return "EOS"


def _cheat_as_handle_callback(callback_type: str) -> str:
    if callback_type in _SPECIAL_CALLBACK_MAPPINGS:
        return _SPECIAL_CALLBACK_MAPPINGS[callback_type]
    interface_prefix: str = _extract_method_interface(callback_type)
    if interface_prefix:
        handle: str = _find_handle_by_prefix(interface_prefix)
        if handle:
            return handle
    return "EOS"


def _cheat_as_handle_constant(constant_name: str) -> str:
    prefix: str = _extract_constant_prefix(constant_name)
    if prefix:
        if prefix in _CONSTANT_PREFIX_TO_HANDLE:
            return _CONSTANT_PREFIX_TO_HANDLE[prefix]
        handle: str = _find_handle_by_prefix(prefix)
        if handle:
            return handle
        return "EOS"
    return ""


def _is_not_included_directly_header(fp: str) -> bool:
    # inl 不能直接被包含
    if fp.endswith(".inl"):
        return True

    f = open(fp, "r")
    content: str = f.read()
    f.close()

    # 文件中说明不能被直接包含
    return "This file is not intended to be included directly" in content


_SKIP_HEADERS: set[str] = {
    "eos_base.h",
    "eos_version.h",
    "eos_platform_prereqs.h",
}


def _route_by_interface(
    file_lower2infos: dict[str, FileInfo],
    attr_name: str,
    routed: set[str],
):
    for il in file_lower2infos:
        interface: str = convert_interface_class_name(il).removeprefix("EOS")
        items: dict = getattr(file_lower2infos[il], attr_name)
        if not items:
            continue
        if interface in interfaces:
            global_files: set[str] = _GLOBAL_CONSTANT_FILES if attr_name == "constants" else _GLOBAL_ENUM_FILES
            target_handle: str = "EOS" if il in global_files else "EOS_H" + interface
            gen_file: str = "eos_common" if il in global_files else file_lower2infos[il].file
            for key in items:
                if key in routed:
                    continue
                routed.add(key)
                handles[target_handle].__dict__[attr_name][key] = items[key]
                generate_infos[gen_file].handles[target_handle].__dict__[attr_name][key] = items[key]
            setattr(file_lower2infos[il], attr_name, type(items)())
        else:
            handle_type: str = _INTERFACE_LOWER_TO_HANDLE.get(il, "")
            if handle_type and handle_type in handles:
                for key in items:
                    if key in routed:
                        continue
                    routed.add(key)
                    handles[handle_type].__dict__[attr_name][key] = items[key]
                    generate_infos[file_lower2infos[il].file].handles[handle_type].__dict__[attr_name][key] = items[key]
                setattr(file_lower2infos[il], attr_name, type(items)())


def _route_by_cheat(
    file_lower2infos: dict[str, FileInfo],
    attr_name: str,
    cheat_fn,
    routed: set[str],
    element_label: str,
):
    for il in file_lower2infos:
        items: dict = getattr(file_lower2infos[il], attr_name)
        to_remove: list[str] = []
        for key in items:
            if key in routed:
                to_remove.append(key)
                continue
            cheat_handle_type: str = cheat_fn(key)
            if not len(cheat_handle_type):
                print(f"[handle_resolver] 警告: {element_label} '{key}' 没有对应的句柄类型")
                continue
            assert_condition(cheat_handle_type in handles, f"[handle_resolver] 未知的句柄类型 '{cheat_handle_type}'")
            routed.add(key)
            handles[cheat_handle_type].__dict__[attr_name][key] = items[key]
            to_remove.append(key)
        for key in to_remove:
            items.pop(key)


def _collect_unhandled(
    file_lower2infos: dict[str, FileInfo],
):
    for il in file_lower2infos:
        info: FileInfo = file_lower2infos[il]
        for attr_name, unhandled_dict in [
            ("callbacks", unhandled_callbacks),
            ("methods", unhandled_methods),
            ("enums", unhandled_enums),
            ("constants", unhandled_constants),
        ]:
            items: dict = getattr(info, attr_name)
            for key in items:
                unhandled_dict[key] = items[key]
                generate_infos[info.file].__dict__[attr_name][key] = items[key]
            if items:
                if il not in unhandled_infos:
                    unhandled_infos[il] = FileInfo()
                setattr(unhandled_infos[il], attr_name, items.copy())
                if attr_name == "constants":
                    print(f"[handle_resolver] 未处理的常量: {list(items.keys())}")
        info.callbacks = {}
        info.methods = {}
        info.enums = {}
        info.constants = {}


def parse_all_file():
    file_lower2infos: dict[str, FileInfo] = {}
    file_lower2infos[convert_to_interface_lower("eos_common.h")] = FileInfo(file="eos_common")

    visited: set[str] = set()

    file_lower2infos["platform"] = FileInfo(file="eos_sdk")
    parse_file("platform", os.path.join(sdk_include_dir, "eos_types.h"), file_lower2infos, visited=visited)

    file_lower2infos["anticheatcommon"] = FileInfo(file="eos_anticheatcommon")
    parse_file("anticheatcommon", os.path.join(sdk_include_dir, "eos_anticheatcommon_types.h"), file_lower2infos, visited=visited)

    for f in os.listdir(sdk_include_dir):
        fp: str = os.path.join(sdk_include_dir, f)
        if os.path.isdir(fp):
            continue

        if f in _SKIP_HEADERS:
            continue

        if f.endswith(".inl") or f.endswith("_types.h"):
            continue

        if _is_not_included_directly_header(fp):
            continue

        is_deprecated_file: bool = "deprecated" in f
        interface_lower: str = convert_to_interface_lower(f)
        if interface_lower not in file_lower2infos.keys():
            file_lower2infos[interface_lower] = FileInfo(file=f.removesuffix("_types.h").removesuffix(".h"))
        skip_includes: bool = f == "eos_sdk.h"
        parse_file(interface_lower, fp, file_lower2infos, is_deprecated_file=is_deprecated_file, skip_includes=skip_includes, visited=visited)

    parse_deferred_include_enums(file_lower2infos)

    extra_handles_methods: dict[str, dict[str, Method]] = {}
    for il in file_lower2infos:
        _handles: dict[str, Handle] = file_lower2infos[il].handles
        for infos in file_lower2infos.values():
            methods: dict[str, Method] = infos.methods
            to_remove_methods: list[str] = []
            for method_name in methods.keys():
                handle_type: str = ""
                callback_type: str = ""
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
                    handle_type = decay_eos_type(methods[method_name].args[0].type)
                    if handle_type not in extra_handles_methods:
                        extra_handles_methods[handle_type] = {}
                    extra_handles_methods[handle_type][method_name] = methods[method_name]
                    continue
                for i in range(len(methods[method_name].args)):
                    arg: Arg = methods[method_name].args[i]
                    arg_type: str = decay_eos_type(arg.type)
                    if arg_type in _handles.keys() and i == 0:
                        if method_name not in to_remove_methods:
                            handle_type = arg_type
                            _handles[handle_type].methods[method_name] = methods[method_name]
                            to_remove_methods.append(method_name)
                    elif i == 0 and is_handle_type(arg_type) and method_name.endswith("_Release"):
                        handle_type = decay_eos_type(methods[method_name].args[0].type)
                        if handle_type not in extra_handles_methods:
                            extra_handles_methods[handle_type] = {}
                        extra_handles_methods[handle_type][method_name] = methods[method_name]
                        to_remove_methods.append(method_name)
                    if is_callback_type_name(arg_type):
                        callback_type = arg_type
                if method_name.endswith("_Release"):
                    if not len(handle_type):
                        release_methods[method_name] = methods[method_name]
                        to_remove_methods.append(method_name)
                        continue
                if len(handle_type) and len(callback_type):
                    _handles[handle_type].callbacks[callback_type] = infos.callbacks[callback_type]
                    infos.callbacks.pop(callback_type)
            for m in to_remove_methods:
                infos.methods.pop(m)

        interface_doc: list[str] = file_lower2infos[il].interface_doc
        if len(interface_doc):
            interface_handle_type: str = ""
            for i in range(len(interface_doc)):
                line: str = interface_doc[i]
                if line.startswith("@see EOS_Platform_Get") and line.strip().endswith("Interface"):
                    interface_handle_type = line.removeprefix("@see EOS_Platform_Get").strip().removesuffix("Interface")
                    if interface_handle_type != "EOS":
                        interface_handle_type = "EOS_H" + interface_handle_type
                    interface_doc.pop(i)
                    if len(interface_doc[i - 1].strip()) <= 0:
                        interface_doc.pop(i - 1)
                    break
            if interface_handle_type in _handles:
                _handles[interface_handle_type].doc = interface_doc
            else:
                handles[interface_handle_type].doc = interface_doc
            file_lower2infos[il].interface_doc = []
        assert_condition(len(file_lower2infos[il].interface_doc) == 0, f"[handle_resolver] 接口 '{il}' 的文档不为空，可能存在未处理的接口文档")

    for il in file_lower2infos:
        infos: FileInfo = file_lower2infos[il]
        generate_infos[infos.file] = FileInfo(infos.file)

    for il in file_lower2infos:
        for h in file_lower2infos[il].handles:
            if h in handles:
                handles[h].methods.update(file_lower2infos[il].handles[h].methods)
                handles[h].callbacks.update(file_lower2infos[il].handles[h].callbacks)
                handles[h].enums.update(file_lower2infos[il].handles[h].enums)
                handles[h].constants.update(file_lower2infos[il].handles[h].constants)
                if not handles[h].doc and file_lower2infos[il].handles[h].doc:
                    handles[h].doc = file_lower2infos[il].handles[h].doc
                generate_infos[file_lower2infos[il].file].handles[h] = handles[h]
            else:
                handles[h] = file_lower2infos[il].handles[h]
                generate_infos[file_lower2infos[il].file].handles[h] = file_lower2infos[il].handles[h]
        file_lower2infos[il].handles = {}

    generate_infos["eos_common"].handles["EOS"] = handles["EOS"]
    generate_infos["eos_anticheatcommon"].handles["EOS_HAntiCheatCommon"] = handles["EOS_HAntiCheatCommon"]

    _routed_structs: set[str] = set()
    for il in file_lower2infos:
        for s in file_lower2infos[il].structs:
            if s in _routed_structs:
                continue
            _routed_structs.add(s)
            structs[s] = file_lower2infos[il].structs[s]
            generate_infos[file_lower2infos[il].file].structs[s] = file_lower2infos[il].structs[s]
        file_lower2infos[il].structs = {}

    _routed_enums: set[str] = set()
    _route_by_interface(file_lower2infos, "enums", _routed_enums)

    _routed_constants: set[str] = set()
    _route_by_interface(file_lower2infos, "constants", _routed_constants)

    _route_by_cheat(file_lower2infos, "methods", _cheat_as_handle_method, set(), "方法")

    _route_by_cheat(file_lower2infos, "enums", _cheat_as_handle_enum, _routed_enums, "枚举类型")

    to_remove_enum_types: list[str] = []
    for enum in handles["EOS_HPlatform"].enums:
        cheat: str = _cheat_as_handle_enum(enum)
        if len(cheat) and cheat != "EOS_HPlatform":
            handles[cheat].enums[enum] = handles["EOS_HPlatform"].enums[enum]
            to_remove_enum_types.append(enum)
    for e in to_remove_enum_types:
        handles["EOS_HPlatform"].enums.pop(e)

    for h in extra_handles_methods:
        for m in extra_handles_methods[h]:
            handles[h].methods[m] = extra_handles_methods[h][m]

    _route_by_cheat(file_lower2infos, "callbacks", _cheat_as_handle_callback, set(), "回调类型")
    _route_by_cheat(file_lower2infos, "constants", _cheat_as_handle_constant, _routed_constants, "常量")

    handles["EOS_HTitleStorageFileTransferRequest"].callbacks["EOS_TitleStorage_OnReadFileCompleteCallback"] = handles["EOS_HTitleStorage"].callbacks[
        "EOS_TitleStorage_OnReadFileCompleteCallback"
    ]
    handles["EOS_HPlayerDataStorageFileTransferRequest"].callbacks["EOS_PlayerDataStorage_OnReadFileCompleteCallback"] = handles["EOS_HPlayerDataStorage"].callbacks[
        "EOS_PlayerDataStorage_OnReadFileCompleteCallback"
    ]
    handles["EOS_HPlayerDataStorageFileTransferRequest"].callbacks["EOS_PlayerDataStorage_OnWriteFileCompleteCallback"] = handles["EOS_HPlayerDataStorage"].callbacks[
        "EOS_PlayerDataStorage_OnWriteFileCompleteCallback"
    ]

    _collect_unhandled(file_lower2infos)

    classes: list[str] = []
    for il in file_lower2infos.keys():
        classes.append(convert_interface_class_name(il).removeprefix("EOS"))
    for up in interfaces:
        if up not in classes:
            print(f"[handle_resolver] 未分类的接口: '{up}'")
        else:
            classes.remove(up)

    from binding_generator.utils.type import make_additional_method_requirements

    make_additional_method_requirements()

    from binding_generator.context import callback_to_method

    for h in handles:
        h_methods: dict[str, Method] = handles[h].methods
        for m in h_methods:
            for arg in h_methods[m].args:
                arg_type: str = decay_eos_type(arg.type)
                if is_callback_type_name(arg_type):
                    callback_to_method[arg_type] = m

    for il in unhandled_infos:
        print(
            f"{il}\t\t\tcb:{len(unhandled_infos[il].callbacks)}\tmethods:{len(unhandled_infos[il].methods)}\tenums:{len(unhandled_infos[il].enums)}\tconstants:{len(unhandled_infos[il].constants)}"
        )

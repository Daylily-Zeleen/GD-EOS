# 命名转换工具

import re
from functools import lru_cache
from binding_generator.utils.common import assert_condition

_SNAKE_CASE_MULTI_UNDERSCORE = re.compile(r"_+")
_VERSION_SUFFIX_PATTERN = re.compile(r"_v(\d+)$")

_OUT_PARAM_PREFIXES = ("Out", "InOut", "bOut")


def is_out_param_name(name: str) -> bool:
    return name.startswith(_OUT_PARAM_PREFIXES)


def strip_out_param_prefix(name: str) -> str:
    return name.removeprefix("InOut").removeprefix("bOut").removeprefix("Out")


_ABBREVIATION_PATTERNS = [
    (re.compile(r"(?<=_)u_r_i(?=_|$)"), "uri"),
    (re.compile(r"(?<=_)u_r_l(?=_|$)"), "url"),
    (re.compile(r"(?<=_)r_t_c(?=_|$)"), "rtc"),
    (re.compile(r"(?<=_)u_i(?=_|$)"), "ui"),
    (re.compile(r"(?<=_)k_w_s(?=_|$)"), "kws"),
    (re.compile(r"(?<=_)n_a_t(?=_|$)"), "nat"),
    (re.compile(r"(?<=_)a_p_i(?=_|$)"), "api"),
    (re.compile(r"(?<=_)i_d(?=_|$)"), "id"),
    (re.compile(r"(?<=_)e_o_s(?=_|$)"), "eos"),
    (re.compile(r"(?<=_)s_d_k(?=_|$)"), "sdk"),
    (re.compile(r"(?<=_)p2_p(?=_|$)"), "p2p"),
    (re.compile(r"^u_r_i_"), "uri_"),
    (re.compile(r"^u_r_l_"), "url_"),
    (re.compile(r"^r_t_c_"), "rtc_"),
    (re.compile(r"^u_i_"), "ui_"),
    (re.compile(r"^k_w_s_"), "kws_"),
    (re.compile(r"^n_a_t_"), "nat_"),
    (re.compile(r"^a_p_i_"), "api_"),
    (re.compile(r"^i_d_"), "id_"),
    (re.compile(r"^e_o_s_"), "eos_"),
    (re.compile(r"^s_d_k_"), "sdk_"),
    (re.compile(r"^p2_p_"), "p2p_"),
]

_HUNGARIAN_PREFIXES = ("b", "p", "n", "sz", "l", "dw", "h", "f")


def remove_backslash_of_last_line(lines: list[str]):
    assert_condition(len(lines), "[naming] 移除末尾反斜杠失败: 行列表为空")
    lines[len(lines) - 1] = lines[len(lines) - 1].removesuffix("\\")


@lru_cache(maxsize=4096)
def to_snake_case(text: str) -> str:
    text = text.split("[", 1)[0].removeprefix("b")
    snake_str: str = "".join(["_" + char.lower() if char.isupper() else char for char in text])
    result = snake_str.lstrip("_")
    result = _SNAKE_CASE_MULTI_UNDERSCORE.sub("_", result)

    for pattern, replacement in _ABBREVIATION_PATTERNS:
        result = pattern.sub(replacement, result)

    for prefix in _HUNGARIAN_PREFIXES:
        if result.startswith(prefix + "_") and len(result) > len(prefix) + 1:
            next_char = result[len(prefix) + 1]
            if next_char.islower():
                result = result[len(prefix) + 1 :]
                break

    result = result.removesuffix("_handle").replace("_handle_", "_")
    return result


def convert_handle_class_name(handle_type: str) -> str:
    if handle_type == "EOS_HUserInfo":
        return "EOSUserInfoInterface"
    text: str = handle_type.removeprefix("EOS_H")
    if text == "EOS":
        return text
    if text.startswith("EOS_"):
        text = text.replace("EOS_", "EOS")
    if not text.startswith("EOS"):
        text = "EOS" + text
    return text


_ABBREVIATIONS: set[str] = {
    "rtc",
    "p2p",
    "ui",
    "kws",
}

_SPECIAL_WORD_MAPPINGS: dict[str, str] = {
    "sdk": "Platform",
}

_WORD_BOUNDARIES: list[str] = [
    "player",
    "data",
    "storage",
    "title",
    "anti",
    "cheat",
    "server",
    "client",
    "common",
    "progression",
    "snapshot",
    "custom",
    "invites",
    "integrated",
    "platform",
    "user",
    "info",
]


def _split_compound_word(word: str) -> list[str]:
    for boundary in _WORD_BOUNDARIES:
        if word.startswith(boundary) and len(word) > len(boundary):
            rest = word[len(boundary) :]
            return [boundary] + _split_compound_word(rest)
    return [word] if word else []


def _convert_word(word: str) -> str:
    if word in _ABBREVIATIONS:
        return word.upper()
    if word in _SPECIAL_WORD_MAPPINGS:
        return _SPECIAL_WORD_MAPPINGS[word]
    parts = _split_compound_word(word)
    return "".join(p.capitalize() for p in parts)


def convert_interface_class_name(interface_name_lower: str) -> str:
    if interface_name_lower in ["eos_common", "common", "e_o_s"]:
        interface_name_lower = "eos"
    if interface_name_lower == "eos":
        return "EOS"
    if interface_name_lower == "eos_userinfo":
        return "EOSUserInfoInterface"
    name_splits: list[str] = interface_name_lower.removeprefix("eos_").split("_")
    converted_parts: list[str] = [_convert_word(part) for part in name_splits]
    return "EOS" + "".join(converted_parts)


def convert_to_interface_lower(file_name: str) -> str:
    splits: list[str] = file_name.rsplit("\\", 1)
    f: str = splits[len(splits) - 1]
    if f == "eos_types.h":
        return "platform"
    if f in ["eos_init.h", "eos_logging.h"]:
        return "common"
    return f.removesuffix("_types.h").removesuffix(".h").replace("_sdk", "_platform").removeprefix("eos_")


def convert_enum_type(ori: str) -> str:
    if ori.startswith("EOS_E"):
        return ori.replace("EOS_E", "")
    elif "_E" in ori:
        splits: list[str] = ori.split("_")
        splits[2] = splits[2].removeprefix("E")
        splits.pop(0)
        return "_".join(splits)
    else:
        print(f"[naming] 不支持的类型转换: '{ori}'")
        return ori


def convert_enum_value(ori: str) -> str:
    return ori.removeprefix("EOS_")


def convert_constant_name(name: str) -> str:
    return name.removeprefix("EOS_")


def convert_constant_as_method_name(name: str) -> str:
    return f"get_{name.removeprefix('EOS_').replace('OPT_', 'ONLINE_PLATFORM_TYPE_').replace('IPT', 'INTEGRATED_PLATFORM_TYPE_')}"


def convert_to_struct_class(struct_type: str) -> str:
    return decay_eos_type(struct_type).replace("EOS_", "EOS")


_decay_eos_type_cache: dict[str, str] = {}


def decay_eos_type(t: str) -> str:
    if t in _decay_eos_type_cache:
        return _decay_eos_type_cache[t]
    ret: str = t.lstrip("const").lstrip(" ").rstrip("*").rstrip("&").rstrip("*").rstrip("&").lstrip(" ").rstrip(" ")
    _decay_eos_type_cache[t] = ret
    return ret


def convert_to_signal_name(callback_type: str, method_name: str = "") -> str:
    from binding_generator.context import handles

    if len(method_name) <= 0:
        for infos in handles.values():
            methods = infos.methods
            for m in methods:
                for a in methods[m].args:
                    if decay_eos_type(a.type) == callback_type:
                        assert_condition(len(method_name) == 0, f"[naming] 回调 '{callback_type}' 匹配到多个方法名: '{method_name}'")
                        method_name = m

    ret: str = to_snake_case(callback_type.rsplit("_", 1)[1])

    version_match = _VERSION_SUFFIX_PATTERN.search(ret)
    version_suffix = version_match.group(0) if version_match else ""

    if version_suffix:
        ret = ret.removesuffix(version_suffix)

    ret = ret.removesuffix("_callback") + version_suffix

    if not ret.startswith("on_"):
        ret = "on_" + ret

    if "AddNotify" in method_name:
        ret = ret.removeprefix("on_")
    elif callback_type in [
        "EOS_PlayerDataStorage_OnWriteFileCompleteCallback",
        "EOS_PlayerDataStorage_OnReadFileCompleteCallback",
        "EOS_TitleStorage_OnReadFileCompleteCallback",
    ]:
        ret = ret.removeprefix("on_") + "d"

    return ret


def convert_method_name(method_name: str, handle_type: str = "") -> str:
    from binding_generator.context import handles

    if method_name == "EOS_Logging_SetCallback":
        return "set_logging_callback"
    elif method_name == "EOS_Platform_Create":
        return "platform_create"
    else:
        if len(handle_type) <= 0:
            for h in handles:
                for m in handles[h].methods:
                    if m == method_name:
                        handle_type = h
                        break
                if len(handle_type):
                    break
        assert_condition(len(handle_type) != 0, f"[naming] 找不到方法 '{method_name}' 对应的句柄类型")
        candidate_method_name: str = method_name.rsplit("_", 1)[1]
        valid: bool = False
        while not valid:
            valid = True
            for m in handles[handle_type].methods:
                if method_name == m:
                    continue
                if m.endswith(candidate_method_name):
                    splits: list[str] = method_name.rsplit("_", 2)
                    candidate_method_name = "".join([splits[1], splits[2]])
                    valid = False
                    break
        return to_snake_case(candidate_method_name).removeprefix("e_")


def convert_prefix_tab(line: str) -> str:
    return line.replace("\t", "    ")


def convert_result_type(method_name: str) -> str:
    return "EOS" + method_name.split("_", 1)[1] + "Result"

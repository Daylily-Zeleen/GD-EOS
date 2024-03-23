import os

# TODO: 每种接口生成单独头文件
# TODO: 解析废弃成员避免硬编码
# TODO: 为有Callable参数的方法生成强类型的回调版本供cpp使用

sdk_inclide_dir = "thirdparty\eos-sdk\SDK\Include"

enum_types: list[str] = []

enum2file: dict[str, str] = {}


all_structs: dict[str, dict[str, str]] = {}


# 解析结果
struct2additional_method_requirements: dict[str, dict[str, bool]] = {}
expended_as_args_structs: list[str] = []  # 需要被展开为参数形式的结构体

interfaces: dict[str, dict] = {
    "Platform": {
        "EOS_Platform_Create": {
            "return": "EOS_HPlatform",
            "args": {"type": "const EOS_Platform_Options*", "name": "Options"},
        }
    }
}
structs: dict[str, dict[str, str]] = {}
handles: dict[str, dict] = {
    "EOS": {
        "methods": {},
        "callbacks": {},
        "enums": {},
    },
    "EOS_HAntiCheatCommon": {
        "methods": {},
        "callbacks": {},
        "enums": {},
    },
    
}


api_latest_macros: list[str] = []
release_methods: dict[str, dict] = {}

unhandled_methods: dict[str, dict] = {}
unhandled_callbacks: dict[str, dict] = {}
unhandled_enums: dict[str, list[str]] = {}
unhandled_infos: dict[str, dict] = {}

generate_infos: dict = {}

# generate options
# 是否将Options结构展开为输入参数的，除了 ApiVersion 以外的最大字段数量,减少需要注册的类，以减少编译后大小
max_options_fields_count_to_expend = 3
max_callback_fields_count_to_expend = 3


gen_enums_inl_file = "eos_enums.gen.inl"
gen_structs_h_file = "eos_structs.gen.h"
gen_structs_cpp_file = "eos_structs.gen.cpp"
gen_handles_h_file = "eos_handles.gen.h"
gen_handles_cpp_file = "eos_handles.gen.cpp"
gen_forward_declare_h_file = "forward_declare.gen.h"

eos_data_class_h_file = "core/eos_data_class.h"


def main():
    # make dir
    gen_dir = "src/gen/"
    if not os.path.exists(gen_dir):
        os.makedirs(gen_dir)

    print("Parsing...")
    parse_all_file()
    print("Parse finished")

    f = open(os.path.join(gen_dir, gen_forward_declare_h_file), "w")
    f.write(gen_foward_declare_file())
    f.close()

    f = open(os.path.join(gen_dir, gen_enums_inl_file), "w")
    f.write(gen_enums())
    f.close()
    print("Enums finished")

    structs_cpp_lines: list[str] = [f"#include <{eos_data_class_h_file}>"]
    f = open(os.path.join(gen_dir, gen_structs_h_file), "w")
    f.write(gen_structs(structs_cpp_lines))
    f.close()
    print("Structs .inl finished")

    f = open(os.path.join(gen_dir, gen_structs_cpp_file), "w")
    f.write("\n".join(structs_cpp_lines))
    f.close()
    print("Structs .cpp finished")

    handles_cpp_lines: list[str] = [f'#include "{gen_handles_h_file}"']
    handles_cpp_lines.append(f"#include <eos_sdk.h>")
    f = open(os.path.join(gen_dir, gen_handles_h_file), "w")
    f.write(gen_handles(handles_cpp_lines))
    f.close()
    print("Handles .inl finished")

    f = open(os.path.join(gen_dir, gen_handles_cpp_file), "w")
    f.write("\n".join(handles_cpp_lines))
    f.close()
    print("Handles .cpp finished")


def _is_base_handle_type(handle_type: str) -> str:
    return handle_type in ["EOS", "EOS_HAntiCheatCommon"]

def _get_base_class(handle_type:str) -> str:
    if "EOS" ==handle_type:
        return "Object"
    elif "EOS_HAntiCheatCommon" == handle_type:
        return _convert_handle_class_name("EOS")
    elif handle_type.startswith("EOS_HAntiCheat"):
        return _convert_handle_class_name("EOS_HAntiCheatCommon")
    elif handle_type.removeprefix("EOS_H") in interfaces:
        return _convert_handle_class_name("EOS")
    else:
        return "RefCounted"

def _convert_to_interface_lower(file_name: str) -> str:
    splited = file_name.rsplit("\\", 1)
    f: str = splited[len(splited) - 1]
    if f == "eos_types.h":
        return "platform"
    # if f == "eos_logging.h":
    #     return "common"
    return (
        f.removesuffix("_types.h")
        .removesuffix(".h")
        .replace("_sdk", "_platform")
        .removeprefix("eos_")
    )


def _cheat_as_handle_method(method_name: str) -> str:
    map = {
        "EOS_IntegratedPlatform_CreateIntegratedPlatformOptionsContainer": "EOS_HIntegratedPlatform",
        "EOS_EpicAccountId_FromString": "EOS_EpicAccountId",
        "EOS_ProductUserId_FromString": "EOS_ProductUserId",
        # 公用（common）
        "EOS_EResult_ToString": "EOS",
        "EOS_EResult_IsOperationComplete": "EOS",
        "EOS_ByteArray_ToString": "EOS",
        "EOS_Logging_SetCallback": "EOS",
        "EOS_Logging_SetLogLevel": "EOS",
        "EOS_EApplicationStatus_ToString": "EOS",
        "EOS_ENetworkStatus_ToString": "EOS",
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
    }
    return map.get(enum_type, "")


def parse_all_file():
    file_lower2infos: dict[str] = {}
    file_lower2infos[_convert_to_interface_lower("eos_common.h")] = {
        "file": "eos_common",
        "enums": {},
        "methods": {},
        "callbacks": {},
        "structs": {},
        "handles": {},
    }

    for f in os.listdir(sdk_inclide_dir):
        fp = os.path.join(sdk_inclide_dir, f)
        if os.path.isdir(fp):
            continue

        if "deprecated" in f:
            continue

        if f in [
            "eos_base.h",
            "eos_platform_prereqs.h",
            "eos_version.h",
            "eos_init.h",  # 在EOSCommon::init中使用，不再单独处理
            #
            "eos_result.h",
            "eos_ui_keys.h",
            "eos_ui_buttons.h",
        ]:  # 特殊处理
            continue
        interface_lower = _convert_to_interface_lower(f)
        if not interface_lower in file_lower2infos.keys():
            file_lower2infos[_convert_to_interface_lower(f)] = {
                "file": f.removesuffix(".h"),
                "methods": {},  # 最终为空
                "callbacks": {},  # 最终为空
                "enums": {},  # 最终为空
                "structs": {},  # 最终为空
                "handles": {},  # 最终为空
            }
        _parse_file(interface_lower, fp, file_lower2infos)

    _get_EOS_EResult(file_lower2infos)
    _get_EOS_UI_EKeyCombination(file_lower2infos)
    _get_EOS_UI_EInputStateButtonFlags(file_lower2infos)

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
                    splited: list[str] = method_name.split("_")
                    for i in range(len(splited)):
                        if splited[i] in ["EOS", "Platform"]:
                            splited[i] = ""
                        if splited[i].startswith("Get"):
                            splited[i] = splited[i].removeprefix("Get")
                        if splited[i].removesuffix("Interface"):
                            splited[i] = splited[i].removesuffix("Interface")
                    interfaces["".join(splited)] = methods[method_name]
                    to_remove_methods.append(method_name)
                    continue

                # 句柄方法
                for i in range(len(methods[method_name]["args"])):
                    arg: dict[str, str] = methods[method_name]["args"][i]
                    arg_type = _decay_eos_type(arg["type"])
                    if arg_type in _handles.keys() and i == 0:
                        # 移动到对应的handle中
                        if not method_name in to_remove_methods:
                            handle_type = arg_type
                            _handles[handle_type]["methods"][method_name] = methods[
                                method_name
                            ]
                            to_remove_methods.append(method_name)

                    if arg_type.endswith("Callback") or arg_type.endswith("CallbackV2"):
                        # 需要被移动的回调
                        callback_type = arg_type

                # Release 方法
                if method_name.endswith("_Release"):
                    release_methods[method_name] = methods[method_name]
                    to_remove_methods.append(method_name)
                    continue

                # 移动回调类型
                if len(handle_type) and len(callback_type):
                    _handles[handle_type]["callbacks"][callback_type] = infos[
                        "callbacks"
                    ][callback_type]
                    infos["callbacks"].pop(callback_type)

            for m in to_remove_methods:
                infos["methods"].pop(m)

    # 初始化生成信息
    for il in file_lower2infos:
        infos: dict = file_lower2infos[il]
        generate_infos[infos["file"]] = {
            "handles": {},
            "structs": {},
            "enums": {},
            #
            "callbacks": {},
            "methods": {},
        }

    # 移动句柄
    for il in file_lower2infos:
        for h in file_lower2infos[il]["handles"]:
            handles[h] = file_lower2infos[il]["handles"][h]
            generate_infos[file_lower2infos[il]["file"]]["handles"][h] = (
                file_lower2infos[il]["handles"][h]
            )
        file_lower2infos[il].pop("handles")

    # 移动结构体
    for il in file_lower2infos:
        for s in file_lower2infos[il]["structs"]:
            structs[s] = file_lower2infos[il]["structs"][s]
            generate_infos[file_lower2infos[il]["file"]]["structs"][s] = (
                file_lower2infos[il]["structs"][s]
            )
        file_lower2infos[il].pop("structs")

    # 移动枚举
    for il in file_lower2infos:
        interface = _convert_interface_class_name(il).removeprefix("EOS")
        if interface in interfaces:
            handles["EOS_H" + interface]["enums"] = file_lower2infos[il]["enums"]
            for e in file_lower2infos[il]["enums"]:
                generate_infos[file_lower2infos[il]["file"]]["enums"][e] = (
                    file_lower2infos[il]["enums"][e]
                )
            file_lower2infos[il]["enums"].clear()

    # Cheat as handle's method
    for il in file_lower2infos:
        methods = file_lower2infos[il]["methods"]
        to_remove: list[str] = []
        for m in methods:
            cheat_handle_type = _cheat_as_handle_method(m)
            if not len(cheat_handle_type):
                print("WARN: has not owned hanle type:", m)
                continue
            if not cheat_handle_type in handles:
                print(handles.keys())
                print("ERR UNKONWN handle type:", cheat_handle_type)
                exit(1)
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
                print("WARN: has not owned hanle type:", e)
                continue
            if not cheat_handle_type in handles:
                print("ERR UNKONWN handle type:", cheat_handle_type)
                exit(1)
            handles[cheat_handle_type]["enums"][e] = enums[e]
            to_remove.append(e)
        for e in to_remove:
            enums.pop(e)

    # 未处理的方法、回调、枚举
    for il in file_lower2infos:
        for cb in file_lower2infos[il]["callbacks"]:
            unhandled_callbacks[cb] = file_lower2infos[il]["callbacks"][cb]
            generate_infos[file_lower2infos[il]["file"]]["callbacks"][cb] = (
                file_lower2infos[il]["callbacks"][cb]
            )

        for m in file_lower2infos[il]["methods"]:
            unhandled_methods[m] = file_lower2infos[il]["methods"][m]
            generate_infos[file_lower2infos[il]["file"]]["methods"][m] = (
                file_lower2infos[il]["methods"][m]
            )

        for e in file_lower2infos[il]["enums"]:
            unhandled_enums[e] = file_lower2infos[il]["enums"][e]
            generate_infos[file_lower2infos[il]["file"]]["enums"][e] = file_lower2infos[
                il
            ]["enums"][e]

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

        file_lower2infos[il].pop("callbacks")
        file_lower2infos[il].pop("methods")
        file_lower2infos[il].pop("enums")

    classes: list[str] = []
    for k in file_lower2infos.keys():
        classes.append(_convert_interface_class_name(k).removeprefix("EOS"))

    for up in interfaces:
        if not up in classes:
            print("?? :", up)
        else:
            classes.remove(up)

    _make_additional_method_requirements()

    # print(classes)
    # print(interfaces.keys())

    for il in unhandled_infos:
        # print(f'{il}\t\t\tcb:{len(unhandled_infos[il].get("callbacks", {}))}\tmethods:{len(unhandled_infos[il].get("methods",{}))}\tenums:{len(unhandled_infos[il].get("enums",{}))}')
        if il in ["common"]:
            print(il, "  ", unhandled_infos[il]["enums"].keys())
    # exit()


def gen_foward_declare_file() -> str:
    ret: list[str] = []
    ret.append("#pragma once")
    ret.append("")
    ret.append("namespace godot {")
    ret.append("// Structs")
    for struct in structs:
        ret.append(
            f'class {remap_type(struct, "").removeprefix("Ref<").removesuffix(">")};'
        )
    ret.append("")
    ret.append("// Handles")
    for handle in handles:
        ret.append(f"class {_convert_handle_class_name(handle)};")
    ret.append("} // namespace godot")
    return "\n".join(ret)


def gen_handles(r_cpp_lines: list[str]) -> str:
    r_cpp_lines  # TODO 添加头文件
    h_lines: list[str] = [f"#pragma once"]

    h_lines.append(f'#include "{eos_data_class_h_file}"')
    h_lines.append(f"#include <eos_sdk.h>")
    h_lines.append(f"#include <godot_cpp/classes/ref_counted.hpp>")
    h_lines.append(f"")

    h_lines.append(f"namespace godot {{")
    r_cpp_lines.append(f"namespace godot {{")
    for h in handles:
        r_cpp_lines.append(f"// ========= {h} =========")
        h_lines.append(f"// ========= {h} =========")
        # TODO: 生成绑定宏
        h_lines += _gen_handle(h, handles[h], r_cpp_lines, [])

    h_lines.append(f"}} // namespace godot")
    r_cpp_lines.append(f"}} // namespace godot")

    return "\n".join(h_lines)


def _convert_handle_class_name(handle_type: str) -> str:
    return _convert_interface_class_name(
        to_snake_case(handle_type.removeprefix("EOS_H"))
    )


def _is_enum_type(type: str) -> bool:
    for h in handles:
        if type in handles[h]["enums"]:
            return True
    if type in unhandled_enums:
        print("WARN: ", type)
        return True
    return False


def _convert_result_type(method_name: str) -> str:
    return method_name.split("_", 1)[1] + "Result"

def _gen_packed_result_type(
    method_name: str,
    method_info: dict,
    r_define_lines: list[str],
    r_register_lines: list[str],
    r_need_convert_to_return_value: list[bool],
    get_type_name_only: bool = False,
) -> str:
    out_args: list[dict[str, str]] = []
    for i in range(len(method_info["args"])):
        arg_name: str = method_info["args"][i]["name"]
        arg_type: str = method_info["args"][i]["type"]
        if (
            arg_name.startswith("Out") or arg_name.startswith("InOut")
        ) and arg_type.endswith("*"):
            out_args.append(method_info["args"][i])
    if len(out_args) <= 0:
        return ""
    #
    if len(method_info["return"]) <= 0 or method_info["return"] == "void":
        if len(out_args) == 1:
            r_need_convert_to_return_value.append[True]
            return ""
        if len(out_args) == 2:
            if (
                out_args[0]["type"] == "char*"
                and out_args[1]["type"].endswith("int32_t*")
                and out_args[1]["name"].endswith("Length")
            ) or (
                out_args[0]["type"] == "void*"
                and out_args[1]["type"].endswith("int32_t*")
            ):
                r_need_convert_to_return_value.append[True]
                return ""

    typename: str = _convert_result_type(method_name)
    if get_type_name_only:
        return typename

    menbers_lines: list[str] = []
    setget_lines: list[str] = []
    bind_lines: list[str] = []
    i = 0
    while i < len(out_args):
        arg: dict[str, str] = out_args[i]
        arg_type: str = arg["type"]
        arg_name: str = arg["name"]
        decayed_type: str = _decay_eos_type(arg["type"])
        snake_name: str = to_snake_case(
            arg_name.removeprefix("IntOut").removeprefix("Out")
        )
        if _is_handle_type(decayed_type):
            menbers_lines.append(
                f"\tRef<{_convert_handle_class_name(decayed_type)}> {snake_name};"
            )
            setget_lines.append(f"\t_DEFINE_SETGET({snake_name})")
            bind_lines.append(f"\t\t_BIND_PROP({snake_name})")
        elif __is_struct_type(decayed_type):
            menbers_lines.append(
                f"\tRef<{__convert_to_struct_class(decayed_type)}> {snake_name};"
            )
            setget_lines.append(f"\t_DEFINE_SETGET({snake_name})")
            bind_lines.append(f"\t\t_BIND_PROP({snake_name})")
        elif _is_enum_type(decayed_type):
            enum_owner: str = "EOS"
            for h in handles:
                if type in handles[h]["enums"]:
                    enum_owner = _convert_interface_class_name(h)
            menbers_lines.append(f"\t{decayed_type} {snake_name};")
            setget_lines.append(f"\t_DEFINE_SETGET({snake_name})")
            bind_lines.append(
                f"\t\t_BIND_PROP_ENUM({snake_name}, {enum_owner}, {_convert_enum_type( decayed_type)})"
            )
        elif (
            arg_type == "char*"
            and (i + 1) < len(out_args)
            and out_args[i + 1]["type"].endswith("int32_t*")
            and out_args[i + 1]["name"].endswith("Length")
        ):
            # 配合 _MAX_LENGTH 宏的字符串
            menbers_lines.append(f"\tString {snake_name};")
            setget_lines.append(f"\t_DEFINE_SETGET({snake_name})")
            bind_lines.append(f"\t\t_BIND_PROP({snake_name})")
            i += 1
        elif (
            arg_type == "void*"
            and (i + 1) <= len(out_args)
            and out_args[i + 1]["type"].endswith("int32_t*")
        ):
            if out_args[i + 1]["name"] != "OutBytesWritten":
                print("WARN:", method_name)
            menbers_lines.append(f"\tPackedByteArray {snake_name};")
            setget_lines.append(f"\t_DEFINE_SETGET({snake_name})")
            bind_lines.append(f"\t\t_BIND_PROP({snake_name})")
            i += 1
        elif decayed_type == "EOS_Bool":
            print("ERROR UNSUPPORT bool:", method_name, decayed_type)
            exit(1)
        elif _is_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORT arr:", method_name, arg_type)
            exit(1)
        elif _is_internal_struct_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORT struct arr:", method_name, arg_type)
            exit(1)
        else:
            menbers_lines.append(f"\t{remap_type(decayed_type)} {snake_name};")
            setget_lines.append(f"\t_DEFINE_SETGET({snake_name})")
            bind_lines.append(f"\t\t_BIND_PROP({snake_name})")

        i += 1

    r_define_lines.append(f"class {typename}: public EOSPackedResult {{")
    r_define_lines.append(f"\tGDCLASS({typename}, EOSPackedResult)")
    r_define_lines.append(f"public:")
    if method_info["return"] == "EOS_EResult":
        r_define_lines.append(f"\tEOS_EResult result_code;")
    else:
        print("ERROR unsupport to gen packed result:", method_name)
    r_define_lines += menbers_lines
    r_define_lines.append("")
    r_define_lines.append(f"public:")
    if method_info["return"] == "EOS_EResult":
        r_define_lines.append(f"\t_DEFINE_SETGET(result_code);")
    r_define_lines += setget_lines
    r_define_lines.append("")
    r_define_lines.append(f"protected:")
    r_define_lines.append(f"\tstatic void _bind_methods() {{")
    r_define_lines.append(f"\t\t_BIND_BEGIN({typename});")
    if method_info["return"] == "EOS_EResult":
        r_define_lines.append(
            f'\t\t_BIND_PROP_ENUM(result_code, EOS_Common, {_convert_enum_type("EOS_EResult")})'
        )
    r_define_lines += bind_lines
    r_define_lines.append(f"\t\t_BIND_END();")
    r_define_lines.append(f"\t}}")
    r_define_lines.append(f"}};")
    r_define_lines.append(f"")

    r_register_lines.append(f"\tGDREGISTER_ABSTRACT_CLASS({typename});\\")
    return typename


# TODO: 绑定
def _gen_handle(
    handle_name: str,
    infos: dict[str, dict],
    r_cpp_lines: list[str],
    r_register_lines: list[str],
) -> list[str]:
    is_base_handle_type = _is_base_handle_type(handle_name)
    base_class = _get_base_class(handle_name)
    
    method_infos = infos["methods"]
    callback_infos = infos["callbacks"]

    klass = _convert_handle_class_name(handle_name)
    release_method: str = ""

    method_bind_lines: list[str] = []

    for method in method_infos:
        if method.endswith("Release"):
            release_method = method
            break

    ret: list[str] = []
    for method in method_infos:
        if method.endswith("Release"):
            continue
        if _is_need_skip_method(method):
            continue
        _gen_packed_result_type(method, method_infos[method], ret, r_register_lines, [])

    ret.append(f"class {klass} : public {base_class} {{")
    ret.append(f"\tGDCLASS({klass}, {base_class})")
    ret.append(f"")
    if not is_base_handle_type:
        ret.append(f"\t{handle_name} m_handle{{ nullptr }};")
        ret.append(f"")
    ret.append(f"protected:")
    ret.append(f"\tstatic void _bind_methods();")
    ret.append(f"")
    ret.append(f"public:")
    # Destructor
    if len(release_method) and not is_base_handle_type:
        ret.append(f"\t~{klass} {{")
        ret.append(f"\t\tif (m_handle) {{")
        ret.append(f"\t\t\trelease_method(m_handle);")
        ret.append(f"\t\t}}")
        ret.append(f"\t}}")
    # Handle setget
    if not is_base_handle_type:
        ret.append(
            f"\tvoid set_handle({handle_name} p_handle) {{ ERR_FAIL_COND(m_handle); m_handle = p_handle; }}"
        )
        ret.append(f"\t{handle_name} get_handle() const {{ return m_handle; }}")
        ret.append(f"")
    # Methods
    for method in method_infos:
        if method.endswith("Release"):
            continue
        if _is_need_skip_method(method):
            continue

        _gen_method(
            handle_name,
            method,
            method_infos[method],
            ret,
            r_cpp_lines,
            method_bind_lines,
        )
        r_cpp_lines.append("")

    ret.append(f"")

    ret.append(f"}};")
    ret.append(f"")

    # bind
    r_cpp_lines.append(f"void {klass}::_bind_methods() {{")
    r_cpp_lines += method_bind_lines
    for callback in callback_infos:
        if _is_need_skip_callback(method):
            continue
        _gen_callback(callback, r_cpp_lines)
    r_cpp_lines.append(f"}}")

    return ret


def __is_struct_type(type: str) -> bool:
    return type in structs


def __is_callback_type(type: str) -> bool:
    for h in handles:
        if type in handles[h]["callbacks"]:
            return True
    return False


def __is_client_data(type: str, name: str) -> bool:
    return type == "void*" and name == "ClientData"


def __is_api_version_field(type: str, name: str) -> bool:
    return type == "int32_t" and name == "ApiVersion"


def __get_struct_fields(type: str) -> dict[str, str]:
    return structs[_decay_eos_type(type)]


def __get_callback_ret_default_val(callback_return_type: str) -> str:
    return {
        "EOS_EIntegratedPlatformPreLogoutAction": "EOS_IPLA_ProcessLogoutImmediately",
        "EOS_PlayerDataStorage_EReadResult": "EOS_RR_ContinueReading",
        "EOS_PlayerDataStorage_EReadResult": "EOS_RR_ContinueReading",
        "EOS_PlayerDataStorage_EWriteResult": "EOS_WR_ContinueWriting",
        "EOS_TitleStorage_EReadResult": "EOS_TS_RR_ContinueReading",
    }[callback_return_type]


def __convert_to_signal_name(callback_type: str) -> str:
    return to_snake_case(callback_type.split("_", 1)[1])


def __convert_to_struct_class(strcut_type: str) -> str:
    # TODO
    return _decay_eos_type(strcut_type).replace("EOS_", "EOS")


def __get_release_method(struct_type: str) -> str:
    expected_release_method = struct_type + "_Release"
    for method in release_methods:
        if method == expected_release_method:
            return method
    print("ERROR: Can' find release method for ", struct_type)
    exit()


# TODO: EOS_IntegratedPlatform_OnUserPreLogoutCallback 需要配合 方法生成 特殊处理
# 在    EOS_IntegratedPlatform_SetUserPreLogoutCallback 中将 _CallbackClientData 作为静态变量
# TODO: 生成信号绑定
def _gen_callback(callback_type: str, r_bind_signal_lines: list[str]) -> str:
    infos: dict
    for handle_infos in handles.values():
        for callback_type in handle_infos["callbacks"]:
            if callback_type == _decay_eos_type(callback_type):
                infos = handle_infos["callbacks"][callback_type]
    if not len(infos["args"]) == 1:
        print("ERROR:", callback_type)
        exit()
    arg: dict[str, str] = infos["args"][0]
    arg_type: str = arg["type"]
    arg_name: str = arg["name"]
    return_type: str = infos["return"]

    signal_name = __convert_to_signal_name(callback_type)
    if not _is_expended_struct(_decay_eos_type(arg_type)):
        r_bind_signal_lines.append(
            f'\tADD_SIGNAL(MethodInfo("{signal_name}", _MAKE_PROP_INFO({remap_type(_decay_eos_type(arg_type), arg_name)}, {to_snake_case(arg_name)})));'
        )
        if len(return_type):
            # TODO: 有返回值的回调的信号发射对象需要特殊处理
            return f'_EOS_METHOD_CALLBACK_RET({return_type}, {__get_callback_ret_default_val(return_type)}, {arg_type}, data, "{signal_name}", {remap_type(_decay_eos_type(arg_type), arg_name)})'
        else:
            return f'_EOS_METHOD_CALLBACK({arg_type}, data, "{signal_name}", {remap_type(_decay_eos_type(arg_type), arg_name)})'
    else:
        fields: dict[str, str] = __get_struct_fields(_decay_eos_type(arg_type))
        ## 检出不需要成为参数的字段
        count_fields: list[str] = []
        variant_union_type_fileds: list[str] = []
        for field in fields.keys():
            if is_deprecated_field(field):
                continue

            field_type = fields[field]
            # 检出count字段
            if _is_arr_field(field_type, field) or _is_internal_struct_arr_field(
                field_type, field
            ):
                count_fields.append(_find_count_field(field, fields.keys()))

            # 检出Variant式的联合体类型字段
            if _is_variant_union_type(field_type, field):
                for f in fields.keys():
                    if f == field + "Type":
                        variant_union_type_fileds.append(f)
        ##
        ret: str = ""
        signal_bind_args: str = ""

        if len(return_type):
            # TODO: 有返回值的回调的信号发射对象需要特殊处理
            ret = f'_EOS_METHOD_CALLBACK_EXPANDED_RET({return_type}, {__get_callback_ret_default_val(return_type)}, {arg_type}, data, "{signal_name}"'
        else:
            ret = f'_EOS_METHOD_CALLBACK_EXPANDED({arg_type}, data, "{signal_name}"'

        for field in fields:
            field_type: str = fields[field]
            if __is_api_version_field(field_type, field):
                continue

            if (
                is_deprecated_field(field)
                or field in count_fields
                or field in variant_union_type_fileds
            ):
                continue

            if not ret.endswith(", "):
                ret += ",\n\t"
                signal_bind_args += ", "

            snake_case_field = to_snake_case(field)
            if _is_anticheat_client_handle_type(field_type):
                ret += f"_EXPAND_TO_GODOT_VAL_ANTICHEAT_CLIENT_HANDLE({remap_type(field_type)}, data->{field})"
                signal_bind_args += (
                    f"_MAKE_PROP_INFO({remap_type(field_type)}, {snake_case_field})"
                )
            elif _is_requested_channel_ptr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_REQUESTED_CHANNEL({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::INT, "{snake_case_field}")'
            elif field_type.startswith("Union"):
                ret += f"_EXPAND_TO_GODOT_VAL_UNION({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::NIL, "{snake_case_field}")'
            elif _is_handle_type(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_HANDLER({remap_type(_decay_eos_type(field_type))}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({remap_type(_decay_eos_type(field_type))}, {snake_case_field})"
            elif _is_client_data_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_CLIENT_DATA({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant::NIL, "{snake_case_field}")'
            elif _is_internal_struct_arr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_STRUCT_ARR({remap_type(_decay_eos_type(field_type))}, data->{field}, {_find_count_field(field, fields.keys())})"
                signal_bind_args += f'PropertyInfo(Variant::ARRAY, "{snake_case_field}", PROPERTY_HINT_ARRAY_TYPE, "{remap_type(_decay_eos_type(field_type))}")'
            elif _is_internal_struct_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_STRUCT({remap_type(_decay_eos_type(field_type))}, data->{field})"
                signal_bind_args += f"_MAKE_PROP_INFO({remap_type(_decay_eos_type(field_type))}, {snake_case_field})"
            elif _is_arr_field(field_type, field):
                ret += f"_EXPAND_TO_GODOT_VAL_ARR({remap_type(field_type)}, data->{field}, {_find_count_field(field, fields.keys())})"
                signal_bind_args += f'PropertyInfo(Variant({remap_type(field_type)}()).get_type(), "{snake_case_field}")'
            else:
                ret += f"_EXPAND_TO_GODOT_VAL({remap_type(field_type)}, data->{field})"
                signal_bind_args += f'PropertyInfo(Variant({remap_type(field_type)}()).get_type(), "{snake_case_field}")'
        ret += ")"

        if len(signal_bind_args):
            signal_bind_args = ", " + signal_bind_args
        r_bind_signal_lines.append(
            f'\tADD_SIGNAL(MethodInfo("{signal_name}"{signal_bind_args}));'
        )
        return ret


def __get_api_latest_macro(struct_type: str) -> str:
    #
    if (struct_type.upper() + "_API_LATEST") in api_latest_macros:
        return struct_type.upper() + "_API_LATEST"
    #
    if (
        struct_type.removesuffix("Options").upper() + "_API_LATEST"
    ) in api_latest_macros:
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


def __expend_input_struct(
    arg_type: str,
    arg_name: str,
    r_declare_args: list[str],
    r_call_args: list[str],
    r_bind_args: list[str],
    r_prepare_lines: list[str],
    r_after_call_lines: list[str],
):
    decayed_type = _decay_eos_type(arg_type)

    r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
    r_call_args.append(f"&{arg_name}")

    fields: dict[str, str] = __get_struct_fields(decayed_type)

    ## 检出不需要成为参数的字段
    count_fields: list[str] = []
    variant_union_type_fileds: list[str] = []
    for field in fields.keys():
        if is_deprecated_field(field):
            continue

        field_type = fields[field]
        # 检出count字段
        if _is_arr_field(field_type, field) or _is_internal_struct_arr_field(
            field_type, field
        ):
            count_fields.append(_find_count_field(field, fields.keys()))

        # 检出Variant式的联合体类型字段
        if _is_variant_union_type(field_type, field):
            for f in fields.keys():
                if f == field + "Type":
                    variant_union_type_fileds.append(f)
    ##
    for field in fields:
        field_type: str = fields[field]
        decay_field_type: str = _decay_eos_type(field_type)
        snake_field: str = to_snake_case(field)

        if __is_api_version_field(field_type, field):
            # 不需要 ApiVersion 作为参数
            macro = __get_api_latest_macro(decayed_type)
            r_prepare_lines.append(f"\t{arg_name}.ApiVersion = {macro};")
            continue
        elif (
            is_deprecated_field(field)
            or field in count_fields
            or field in variant_union_type_fileds
        ):
            # 需要跳过的字段
            continue

        r_bind_args.append(f'"{snake_field}"')

        option_field = f"{arg_name}.{field}"
        if _is_anticheat_client_handle_type(field_type):
            r_declare_args.append(f"{remap_type(field_type, field)} p_{snake_field}")
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE({option_field}, p_{snake_field});"
            )
        elif _is_requested_channel_ptr_field(field_type, field):
            r_declare_args.append(f"{remap_type(field_type, field)} p_{snake_field}")
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_REQUESTED_CHANNEL({option_field}, p_{snake_field});"
            )
        elif field_type.startswith("Union"):
            r_declare_args.append(
                f"const {remap_type(_decay_eos_type(field_type), field)} &p_{snake_field}"
            )
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_UNION({option_field}, p_{snake_field});"
            )
        elif _is_handle_type(field_type, field):
            r_declare_args.append(
                f"const {remap_type(_decay_eos_type(field_type), field)} &p_{snake_field}"
            )
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_HANDLER({option_field}, p_{snake_field});"
            )
        elif _is_client_data_field(field_type, field):
            r_declare_args.append(f"const Variant &p_{snake_field}")
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_CLIENT_DATA({option_field}, p_{snake_field});"
            )
        elif _is_internal_struct_arr_field(field_type, field):
            r_declare_args.append(
                f"const {remap_type(_decay_eos_type(field_type), field)} &p_{snake_field}"
            )
            option_count_field = f"{arg_name}.{_find_count_field(field, fields.keys())}"
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_STRUCT_ARR({__convert_to_struct_class(decay_field_type)}, {option_field}, p_{snake_field}, {option_count_field});"
            )
        elif _is_internal_struct_field(field_type, field):
            r_declare_args.append(
                f"const {remap_type(_decay_eos_type(field_type), field)} &p_{snake_field}"
            )
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_STRUCT({option_field}, p_{snake_field});"
            )
        elif _is_arr_field(field_type, field):
            r_declare_args.append(
                f"const {remap_type(field_type, field)} &p_{snake_field}"
            )
            option_count_field = f"{arg_name}.{_find_count_field(field, fields.keys())}"
            r_prepare_lines.append(
                f"\t_TO_EOS_FIELD_ARR({option_field}, p_{snake_field}, {option_count_field});"
            )
        else:
            r_declare_args.append(
                f"gd_arg_t<{remap_type(field_type, field)}> p_{snake_field}"
            )
            r_prepare_lines.append(f"\t_TO_EOS_FIELD({option_field}, p_{snake_field});")


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
        r_after_call_lines.append(
            f"\tRef<{packed_result_type}> ret; ret.instantiate();"
        )
        if has_result_code:
            r_after_call_lines.append(f"\tret->result_code = result_code;")
            r_after_call_lines.append(
                f"\tif (result_code == EOS_EResult::EOS_Success) {{"
            )
    acl_indents = "\t\t" if has_result_code else "\t"
    i = begin_idx
    while i < len(args):
        arg_name: str = args[i]["name"]
        arg_type: str = args[i]["type"]
        decayed_type: str = _decay_eos_type(arg_type)
        snake_name: str = to_snake_case(
            arg_name.removeprefix("InOut").removeprefix("Out")
        )
        if _is_handle_type(decayed_type):
            r_prepare_lines.append(f"\t{decayed_type} {arg_name}{{ nullptr }};")
            r_call_args.append(f"&{arg_name}")
            if pack_result:
                r_after_call_lines.append(
                    f"{acl_indents}ret->{snake_name}.instantiate(); ret->{snake_name}->set_handle({arg_name});"
                )
            else:
                r_return_type_if_convert_to_return.append(
                    f"Ret<{remap_type(decayed_type, arg_name)}>"
                )
                r_after_call_lines.append(
                    f"{acl_indents}Ret<{remap_type(decayed_type, arg_name)}> ret; ret.instantiate(); ret->set_handle({arg_name});"
                )
        elif __is_struct_type(decayed_type):
            r_prepare_lines.append(f"\t{decayed_type} {arg_name};")
            r_call_args.append(f"&{arg_name}")
            if pack_result:
                r_after_call_lines.append(
                    f"{acl_indents}ret->{snake_name}.instantiate(); ret->{snake_name}->set_from_eos({arg_name});"
                )
            else:
                r_return_type_if_convert_to_return.append(
                    f"Ret<{remap_type(decayed_type, arg_name)}>"
                )
                r_after_call_lines.append(
                    f"{acl_indents}Ret<{remap_type(decayed_type, arg_name)}> ret; ret.instantiate(); ret->set_from_eos({arg_name});"
                )

        elif _is_enum_type(decayed_type):
            r_prepare_lines.append(f"\t{_convert_enum_type(decayed_type)} {arg_name};")
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                r_after_call_lines.append(
                    f"{acl_indents}ret->{snake_name} = {arg_name};"
                )
            else:
                r_return_type_if_convert_to_return.append(
                    f"{remap_type(decayed_type, arg_name)}"
                )
                r_after_call_lines.append(
                    f"{acl_indents}{remap_type(decayed_type, arg_name)} ret = {arg_name};;"
                )
        elif (
            arg_type == "char*"
            and (i + 1) < len(args)
            and args[i + 1]["type"].endswith("int32_t*")
            and args[i + 1]["name"].endswith("Length")
        ):
            r_prepare_lines.append(
                f"\tchar {arg_name} [{__get_str_result_max_length_macro(method_name)} + 1] {{}};"
            )
            r_prepare_lines.append(
                f'\t{_decay_eos_type(args[i+1]["type"])} {args[i+1]["name"]} = 0;'
            )

            r_call_args.append(f"&{arg_name}[0]")
            r_call_args.append(f'&{args[i+1]["name"]}')

            if pack_result:
                r_after_call_lines.append(
                    f"{acl_indents}ret->{snake_name} = &{arg_name}[0];"
                )
            else:
                r_return_type_if_convert_to_return.append(f"String")
                r_after_call_lines.append(f"{acl_indents}String ret = &{arg_name}[0];")
            i += 1
        elif (
            arg_type == "void*"
            and (i + 1) <= len(args)
            and args[i + 1]["type"].endswith("int32_t*")
        ):
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
                exit(1)
            #

            r_prepare_lines.append(f"\tPackedByteArray {arg_name};")
            r_prepare_lines.append(f"\t{arg_name}.resize({length_variable});")
            r_prepare_lines.append(
                f'\t{_decay_eos_type(args[i+1]["type"])} {args[i+1]["name"]} = {length_variable};'
            )

            r_call_args.append(f"{arg_name}.ptrw()")
            r_call_args.append(f'&{args[i+1]["name"]}')

            r_after_call_lines.append(
                f'{acl_indents}{arg_name}.resize({args[i+1]["name"]});'
            )

            if pack_result:
                r_after_call_lines.append(
                    f"{acl_indents}ret->{snake_name} = {arg_name};"
                )
            else:
                r_return_type_if_convert_to_return.append(f"PackedByteArray")
                r_after_call_lines.append(
                    f"{acl_indents}PackedByteArray ret = {arg_name};"
                )

            i += 1
        elif decayed_type == "EOS_Bool":
            print("ERROR UNSUPPORT bool:", method_name, decayed_type)
            exit(1)
        elif _is_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORT arr:", method_name, arg_type)
            exit(1)
        elif _is_internal_struct_arr_field(arg_type, arg_name):
            print("ERROR UNSUPPORT struct arr:", method_name, arg_type)
            exit(1)
        else:
            if not arg_type.endswith("*"):
                print("ERROR UNSUPPORT out: ", arg_type, arg_name)
                exit(1)

            r_prepare_lines.append(f'\t{arg_type.removesuffix("*")} {arg_name};')
            r_call_args.append(f"&{arg_name}")

            if pack_result:
                r_after_call_lines.append(
                    f"{acl_indents}_FROM_EOS_FIELD(ret->{snake_name}, {arg_name});"
                )
            else:
                r_return_type_if_convert_to_return.append(
                    f"{remap_type(decayed_type, arg_name)}"
                )
                r_after_call_lines.append(
                    f"{acl_indents}{remap_type(decayed_type, arg_name)} ret; _FROM_EOS_FIELD(ret, {arg_name});"
                )

        i += 1

    if has_result_code:
        r_after_call_lines.append(f"\t}}")


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
    need_callable_arg = False

    out_to_ret: list[bool] = []
    packed_result_type = _gen_packed_result_type(
        method_name, info, [], [], out_to_ret, True
    )
    need_out_to_ret: bool = False if len(out_to_ret) <= 0 else out_to_ret[0]

    # 是否回调
    for a in info["args"]:
        if __is_callback_type(_decay_eos_type(a["type"])):
            if info["return"] == "void":
                return_type = "Signal"
                callback_signal = __convert_to_signal_name(_decay_eos_type(a["type"]))
            else:
                need_callable_arg = True
            break

    if (need_callable_arg or return_type == "Signal") and len(packed_result_type):
        print("ERROR 回调与打包返回冲突:", method_name)
        exit(1)

    if len(packed_result_type):
        return_type = f"Ref<{packed_result_type}>"
    elif return_type == "" and info["return"] != "void":
        return_type = remap_type(info["return"], "")
    else:
        return_type = "void"

    declare_args: list[str] = []
    call_args: list[str] = []
    bind_args: list[str] = []

    prepare_lines: list[str] = []
    after_call_lines: list[str] = []

    options_type: str = ""  # 用于获取里边的buffer size 字段

    static: bool = True
    i: int = 0
    while i < len(info["args"]):
        type: str = info["args"][i]["type"]
        name: str = info["args"][i]["name"]
        decayed_type: str = _decay_eos_type(type)
        snake_name: str = to_snake_case(name)

        if decayed_type == handle_type:
            # 句柄参数
            call_args.append("m_handle")
            static = False
        elif __is_callback_type(decayed_type):
            # 回调参数
            if need_callable_arg:
                declare_args.append(f"const Callable& p_{snake_name}")
                bind_args.append(f'"completion_callback"')

            call_args.append(f"{_gen_callback(decayed_type, [])}")
        elif __is_client_data(type, name):
            # Client Data, 必定配合回调使用
            declare_args.append("const Variant& p_client_data")
            bind_args.append('"client_data"')
            if need_callable_arg:
                call_args.append(
                    f"_MAKE_CALLBACK_CLIENT_DATA(p_client_data, p_{snake_name})"
                )
            else:
                call_args.append("_MAKE_CALLBACK_CLIENT_DATA(p_client_data)")
        elif __is_method_input_only_struct(decayed_type) and not _is_expended_struct(
            decayed_type
        ):
            if name == "Options":
                options_type = decayed_type
            # 未被展开的输入结构体（Options）
            declare_args.append(
                f"const {remap_type(decayed_type, name)}& p_{snake_name}"
            )
            prepare_lines.append(f"\tauto &Options = p_{snake_name}->to_eos();")
            bind_args.append(f'"{snake_name}"')
            call_args.append(f"&Options")
        elif __is_method_input_only_struct(decayed_type) and _is_expended_struct(
            decayed_type
        ):
            if name == "Options":
                options_type = decayed_type
            # 被展开的输入结构体（Options）
            __expend_input_struct(
                type,
                name,
                declare_args,
                call_args,
                bind_args,
                prepare_lines,
                after_call_lines,
            )
        elif name.startswith("Out") or name.startswith("InOut"):
            # Out 参数
            converted_return_type: list[str] = []
            __make_packed_result(
                packed_result_type,
                method_name,
                info["return"] == "EOS_EResult",
                "Options",
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
                    exit(1)
                if return_type != "void":
                    print("ERROR : ?")
                    exit(1)
                return_type = converted_return_type[1]

            # Out 参数在最后，直接跳出
            break
        else:
            # 普通参数
            declare_args.append(f"gd_arg_t<{remap_type(type, name)}> p_{snake_name}")
            bind_args.append(f'"{snake_name}"')
            call_args.append(
                f"to_eos_type<gd_arg_t<{remap_type(type, name)}>, {type}>(p_{snake_name})"
            )
        i += 1

    # 避免同类内方法重名
    candidate_method_name = method_name.rsplit("_", 1)[1]
    valid = False
    while not valid:
        valid = True
        for m in handles[handle_type]["methods"]:
            if m.endswith(candidate_method_name):
                splited = method_name.rsplit("_", 2)
                candidate_method_name = "".join([splited[1], splited[2]])
                valid = False
                break
    snake_method_name = to_snake_case(candidate_method_name).removeprefix(
        "e_"
    )  # Hack, 去除枚举前缀

    # ======= 声明 ===============
    r_declare_lines.append(
        f'\t{"static " if static else ""}{return_type} {snake_method_name}({", ".join(declare_args)});'
    )
    # ======= 定义 ===============
    r_define_lines.append(
        f'{return_type} {handle_klass}::{snake_method_name}({", ".join(declare_args)}) {{'
    )
    r_define_lines += prepare_lines
    # 调用
    if _is_handle_type(_decay_eos_type(info["return"])):
        r_define_lines.append(
            f'\tauto return_handle = {method_name}({", ".join(call_args)});'
        )
    elif info["return"] == "EOS_EResult":
        r_define_lines.append(
            f'\tEOS_EResult result_code = {method_name}({", ".join(call_args)});'
        )
    elif return_type == "void" or return_type == "Signal" or need_out_to_ret:
        r_define_lines.append(f'\t{method_name}({", ".join(call_args)});')
    else:
        r_define_lines.append(f'\tauto ret = {method_name}({", ".join(call_args)});')
    # 后处理
    r_define_lines += after_call_lines
    # 返回
    if _is_handle_type(_decay_eos_type(info["return"])):
        r_define_lines.append(
            f"\t{return_type} ret; ret.instantiate(); ret->set_handle(return_handle);"
        )
        r_define_lines.append(f"\treturn ret;")
    elif len(packed_result_type):
        if info["return"] == "EOS_EResult":
            r_define_lines.append(f"\tret->result_code = result_code;")
        r_define_lines.append(f"\treturn ret;")
    elif return_type == "EOS_EResult":
        r_define_lines.append(f"\treturn result_code;")
    elif return_type == "Signal":
        r_define_lines.append(f"\treturn Signal(this, {callback_signal});")
    elif return_type != "void":
        r_define_lines.append(f"\treturn _EXPAND_TO_GODOT_VAL({return_type}, ret);")

    r_define_lines.append("}")
    # ======= 绑定 ===============
    bind_args_text: str = ", ".join(bind_args)
    if len(bind_args_text):
        bind_args_text = ", " + bind_args_text
    default_val_arg = ""
    if need_callable_arg:
        default_val_arg = ", DEVAL(Callable())"
    
    bind_prefix:str = "ClassDB::bind_static_method(get_class_static(), " if static else "ClassDB::bind_method("
    r_bind_lines.append(
        f'\t{bind_prefix}D_METHOD("{snake_method_name}"{bind_args_text}), &{handle_klass}::{snake_method_name}{default_val_arg});'
    )


def _get_EOS_EResult(r_file_lower2infos: list[str]):
    f = open("thirdparty\eos-sdk\SDK\Include\eos_result.h", "r")

    r_file_lower2infos[_convert_to_interface_lower("eos_common.h")]["enums"][
        "EOS_EResult"
    ] = []

    for line in f.readlines():
        if not line.startswith("EOS_RESULT_VALUE"):
            continue
        r_file_lower2infos[_convert_to_interface_lower("eos_common.h")]["enums"][
            "EOS_EResult"
        ].append(line.split("(", 1)[1].split(", ", 1)[0])

    f.close()


def _get_EOS_UI_EKeyCombination(r_file_lower2infos: list[str]):
    f = open("thirdparty\eos-sdk\SDK\Include\eos_ui_keys.h", "r")

    r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"][
        "EOS_UI_EKeyCombination"
    ] = []
    for line in f.readlines():
        if not line.startswith("EOS_UI_KEY_"):
            continue

        splited = line.split("(", 1)[1].rsplit(")")[0].split(", ")
        r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"][
            "EOS_UI_EKeyCombination"
        ].append(splited[0] + splited[1])

    f.close()


def _get_EOS_UI_EInputStateButtonFlags(r_file_lower2infos: list[str]):
    f = open("thirdparty\eos-sdk\SDK\Include\eos_ui_buttons.h", "r")

    r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"][
        "EOS_UI_EInputStateButtonFlags"
    ] = []
    for line in f.readlines():
        if not line.startswith("EOS_UI_KEY_"):
            continue

        splited = line.split("(", 1)[1].rsplit(")")[0].split(", ")
        r_file_lower2infos[_convert_to_interface_lower("eos_ui_types.h")]["enums"][
            "EOS_UI_EInputStateButtonFlags"
        ].append(splited[0] + splited[1])

    f.close()


def gen_enums() -> str:
    lines = ["#pragma once"]
    lines.append("")

    # include files
    for f in os.listdir(sdk_inclide_dir):
        if not f.endswith("_types.h"):
            continue
        lines.append(f"#include <{f}>")

    lines.append(f"#include <eos_ui_types.h>")
    lines.append(f"#include <eos_common.h>")
    lines.append("")
    lines.append("namespace godot {")
    lines.append("")

    for h in handles:
        if len(handles[h]) <= 0:
            continue
        lines.append(f"// ==== {h} ====")
        interface_class_name = _convert_interface_class_name(h)
        interface_enums: dict[str, list[str]] = handles[h]["enums"]

        # Bind enum value macro
        for enum_type in interface_enums:
            if _is_need_skip_enum_type(enum_type):
                continue
            lines.append(f"#define _BIND_ENUM_{enum_type}()\\")
            for e in interface_enums[enum_type]:
                if _is_need_skip_enum_value(enum_type, e):
                    continue
                lines.append(
                    f'\t_BIND_ENUM_CONSTANT({enum_type}, {e}, "{_convert_enum_value(e)}");\\'
                )
            lines.append("")

        # Bind macro
        lines.append(f"#define _BIND_ENUMS_{interface_class_name}()\\")
        for enum_type in interface_enums:
            if _is_need_skip_enum_type(enum_type):
                continue
            lines.append(f"\t_BIND_ENUM_{enum_type}()\\")
        lines.append("")

        # Using macro
        lines.append(f"#define _USING_ENUMS_{_convert_interface_class_name(h)}()\\")
        for enum_type in interface_enums:
            if _is_need_skip_enum_type(enum_type):
                continue
            lines.append(f"\tusing {_convert_enum_type(enum_type)} = {enum_type};\\")
        lines.append("")

        # Variant cast macro
        lines.append(f"#define _CAST_ENUMS_{_convert_interface_class_name(h)}()\\")
        for enum_type in interface_enums:
            if _is_need_skip_enum_type(enum_type):
                continue
            lines.append(
                f"\tVARIANT_ENUM_CAST(godot::{_convert_interface_class_name(h)}::{_convert_enum_type(enum_type)});\\"
            )
        lines.append("")

    lines.append("} // namespace godot")
    lines.append("")

    return "\n".join(lines)


def _convert_enum_type(ori: str) -> str:
    if ori.startswith("EOS_E"):
        return ori.replace("EOS_E", "")
    elif "_E" in ori:
        splited = ori.split("_")
        splited[2] = splited[2].removeprefix("E")
        splited.pop(0)
        return "_".join(splited)
    else:
        print("ERROR: Unsupport:", ori)
        return ori


def _convert_enum_value(ori: str) -> str:
    return ori.removeprefix("EOS_")


def _is_need_skip_struct(struct_type: str) -> bool:
    return struct_type in [
        "EOS_AntiCheatCommon_Quat",
        "EOS_AntiCheatCommon_Vec3f",
    ]


def _is_need_skip_callback(callback_type: str) -> bool:
    return callback_type in ["EOS_IntegratedPlatform_OnUserPreLogoutCallback"]


def _is_need_skip_method(method_name: str) -> bool:
    # TODO: Create , Release, GetInterface 均不需要
    return method_name.startswith("EOS_Logging_") or method_name in [
        "EOS_IntegratedPlatform_SetUserPreLogoutCallback",  # 特殊处理
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
        # 废弃 NODT: This api is deprecated.
        "EOS_AntiCheatClient_PollStatus",
    ]


def _is_need_skip_enum_type(ori_enum_type: str) -> bool:
    # if "AntiCheat" in ori_enum_type:
    #     # TODO 目前未实现反作弊相关接口
    #     return True
    return ori_enum_type in [
        "EOS_EAttributeType",
        "EOS_EComparisonOp",
    ]


def _is_need_skip_enum_value(ori_enum_type: str, enum_value: str) -> bool:
    map = {
        "EOS_EExternalCredentialType": [
            # DEPRECATED
            "EOS_ECT_STEAM_APP_TICKET"
        ],
    }
    return ori_enum_type in map and enum_value in map[ori_enum_type]


def _get_enum_owned_interface(ori_filename: str, ori_enum_type: str) -> str:
    lower = ""

    # Hack
    if ori_filename == "eos_types.h":
        map = {
            "EOS_ERTCBackgroundMode": "platform",
            "EOS_EApplicationStatus": "platform",
            "EOS_ENetworkStatus": "platform",
            "EOS_EDesktopCrossplayStatus": "platform",
        }
        lower = map[ori_enum_type]
    elif ori_filename.endswith("_types.h"):
        lower = ori_filename.split("_")[1]
    else:
        # eos_common
        map = {
            "EOS_UI_EKeyCombination": "ui",
            "EOS_UI_EInputStateButtonFlags": "ui",
            "EOS_EResult": "",  # ALL
            "EOS_ELoginStatus": "",  # auth connect
            "EOS_EExternalAccountType": "",  # connect user_info
            "EOS_EExternalCredentialType": "",  # auth connect
            "EOS_EAttributeType": "",  # session lobby 因为内部由 Variant 进行转换，该枚举也许不需要
            "EOS_EComparisonOp": "",  # session lobby 因为内部由转换，该枚举也许不需要
        }
        lower = map[ori_enum_type]

    map = {
        "anticheatclient": "anticheat_client",
        "anticheatserver": "anticheat_server",
        "custominvites": "custom_invites",
        "integratedplatform": "integrated_platform",
        "playerdatastorage": "player_data_storage",
        "progressionsnapshot": "progression_snapshot",  #
        "titlestorage": "title_storage",
        "userinfo": "user_info",
    }
    if lower in map.keys():
        lower = map[lower]

    return _convert_interface_class_name(lower) if len(lower) else ""


def is_deprecated_field(field: str) -> bool:
    return (
        field.endswith("_DEPRECATED")
        # Hack
        or field == "Reserved"  # SDK要求保留
        or field
        in [
            # 以下回调字段由对应的接口返回值对象信号承担
            "ReadFileDataCallback",
            "FileTransferProgressCallback",
            "WriteFileDataCallback",
        ]
        #
        or field == "PlatformSpecificOptions"  # 暂不支持的字段
        or field == "SystemSpecificOptions"  # 暂不支持的字段
        or field == "InitOptions"  # 暂不支持的字段
        or field == "IntegratedPlatformOptionsContainerHandle"  # 暂不支持的字段
        or field == "SystemMemoryMonitorReport"  # 暂不支持的字段
    )


def remap_type(type: str, field: str = "") -> str:
    if type in enum_types:
        # 枚举类型原样返回
        return type
    if __is_struct_type(type):
        return f"Ref<{__convert_to_struct_class(type)}>"
    if _is_handle_type(type, field):
        return f"Ref<{_convert_handle_class_name(type)}>"
    if _is_internal_struct_arr_field(type, field):
        return f"TypedArray<{__convert_to_struct_class(_decay_eos_type(type))}>"

    if type.startswith("Union"):
        uion_field_map = {
            "ParamValue": "Variant",
            "Value": "Variant",
            "AccountId": "String",
        }
        return uion_field_map[field]

    todo_types = {
        #
        "EOS_PlayerDataStorage_OnReadFileDataCallback": ["ReadFileDataCallback"],
        "EOS_PlayerDataStorage_OnFileTransferProgressCallback": [
            "FileTransferProgressCallback"
        ],
        "EOS_PlayerDataStorage_OnWriteFileDataCallback": ["WriteFileDataCallback"],
        "EOS_TitleStorage_OnReadFileDataCallback": ["ReadFileDataCallback"],
        "EOS_TitleStorage_OnFileTransferProgressCallback": [
            "FileTransferProgressCallback"
        ],
        #
        "const EOS_Lobby_AttributeData*": ["Attribute", "Parameter"],
        "const EOS_Sessions_AttributeData*": ["SessionAttribute", "Parameter"],
        #
        "EOS_AntiCheatCommon_LogPlayerUseWeaponData*": [
            "UseWeaponData",
            "PlayerUseWeaponData",
        ],
        "const EOS_Auth_Credentials*": ["Credentials"],
        "const EOS_Auth_Token*": ["AuthToken"],
        "const EOS_Auth_IdToken*": ["IdToken"],
        "const EOS_Connect_Credentials*": ["Credentials"],
        "const EOS_Connect_IdToken*": ["IdToken"],
        "const EOS_Connect_UserLoginInfo*": ["UserLoginInfo"],
        "const EOS_P2P_SocketId*": ["SocketId"],
        #
        "const EOS_Lobby_LocalRTCOptions*": ["LocalRTCOptions"],
        "const EOS_IntegratedPlatform_Options*": ["Options"],
        "const EOS_Platform_RTCOptions*": ["RTCOptions"],
        #
        "EOS_Platform_ClientCredentials": ["ClientCredentials"],
        "const EOS_Auth_PinGrantInfo*": ["PinGrantInfo"],
        "const EOS_Ecom_ItemOwnership*": ["ItemOwnership"],
        "const EOS_Ecom_SandboxIdItemOwnership*": ["SandboxIdItemOwnerships"],
        "const EOS_Mod_Identifier*": ["Mod"],
        "EOS_RTCAudio_AudioBuffer*": ["Buffer"],
        "const EOS_RTC_Option*": ["RoomOptions"],
        "const EOS_RTC_ParticipantMetadata*": ["ParticipantMetadata"],
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
        "EOS_ProductUserId": "String",
        "EOS_EpicAccountId": "String",
        "EOS_LobbyId": "String",
        "const char*": "String",
        "EOS_Ecom_SandboxId": "String",
        "const EOS_Ecom_CatalogItemId*": "PackedStringArray",
        "int16_t*": "PackedInt32Array",
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
        "EOS_ProductUserId*": "PackedStringArray",
        "const EOS_ProductUserId*": "PackedStringArray",
        "EOS_Ecom_SandboxId*": "PackedStringArray",
        "const char* const*": "PackedStringArray",
        "EOS_Ecom_EntitlementName*": "PackedStringArray",
        "EOS_OnlinePlatformType": "uint32_t",
        "const uint32_t*": "PackedInt64Array",
        "EOS_IntegratedPlatformType": "String",
        "Union{EOS_AntiCheatCommon_ClientHandle : ClientHandle, const char* : String, uint32_t : UInt32, in, EOS_AntiCheatCommon_Vec3f : Vec3f, EOS_AntiCheatCommon_Quat : Quat}": "Variant",
        "Union{int64_t : AsInt64, double : AsDouble, EOS_Bool : AsBool, const char* : AsUtf8}": "Vaiant",
        "Union{EOS_EpicAccountId : Epic, const char* : External}": "String",
        #
        # "EOS_ContinuanceToken": "Ref<EOSGContinuanceToken>",
        # "EOS_HLobbyDetails": "Ref<EOSGLobbyDetails>",
        # "EOS_HLobbyModification": "Ref<EOSGLobbyModification>",
        # "EOS_HPresenceModification": "Ref<EOSGPresenceModification>",
        # "EOS_HSessionModification": "Ref<EOSGSessionModification>",
        # "EOS_HSessionDetails": "Ref<EOSGSessionDetails>",
        # "EOS_HIntegratedPlatformOptionsContainer": "Ref<EOSGIntegratedPlatformOptionsContainer>",  # TODO
        #
        "EOS_AntiCheatCommon_ClientHandle": "EOSAntiCheatCommon_Client *",
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
            "InitOptions": "Variant",  # 暂不支持
            "SystemMemoryMonitorReport": "Variant",  # 暂不支持
        },
        "char": {
            "SocketName[EOS_P2P_SOCKETID_SOCKETNAME_SIZE]": "String",
        },
        "const uint8_t*": {
            "RequestedChannel": "int16_t",  # 可选字段，-1 将转为空指针
        },
        # 弃用的
        "const EOS_Auth_AccountFeatureRestrictedInfo*": {
            "AccountFeatureRestrictedInfo_DEPRECATED": "Dictionary",
        },
    }

    if type in condition_remap.keys():
        return condition_remap[type].get(field, "Variant")

    return simple_remap.get(type, type)


def _is_expended_struct(struct_type: str) -> bool:
    return _decay_eos_type(struct_type) in expended_as_args_structs


def gen_structs(r_cpp_lines: list[str]) -> str:
    r_cpp_lines.append("")

    lines: list[str] = []
    lines.append("#pragma once")
    lines.append("")

    lines.append(f"#include <eos_sdk.h>")
    lines.append(f"#include <godot_cpp/classes/ref_counted.hpp>")
    lines.append("")
    lines.append(f"#include <{eos_data_class_h_file}>")
    lines.append(f'#include "eos_anticheatcommon_client.h"')
    lines.append("")

    lines.append("namespace godot {")
    for struct_type in structs:
        if _is_expended_struct(struct_type):
            continue
        if _is_need_skip_struct(struct_type):
            continue

        lines += _gen_struct(struct_type, structs[struct_type], r_cpp_lines)
    lines.append(f"")
    r_cpp_lines.append(f"")

    lines.append("} // namespace godot")
    lines.append("")

    # 生成绑定宏
    lines.append("// ====================")
    lines.append("#define REGISTER_DATA_CLASSES()\\")
    for st in all_structs.keys():
        if _is_expended_struct(struct_type):
            continue
        if _is_need_skip_struct(struct_type):
            continue

        lines.append(
            f"\tGDREGISTER_ABSTRACT_CLASS(godot::{__convert_to_struct_class(st)});\\"
        )
    lines.append("")
    return "\n".join(lines)


def to_snake_case(text: str) -> str:
    # TODO: 分离
    # SPECIAL: char SocketName[EOS_P2P_SOCKETID_SOCKETNAME_SIZE];
    text = text.split("[", 1)[0]
    #
    snake_str = "".join(
        ["_" + char.lower() if char.isupper() else char for char in text]
    )
    return (
        snake_str.lstrip("_")
        .replace("u_r_i", "uri")
        .replace("b_is", "is")
        .replace("r_t_c", "rtc")
        .replace("u_i_", "ui_")
        .replace("k_w_s", "kws")
        .replace("p2_p_", "p2p_")
        .replace("n_a_t", "nat")
    )


def __is_arg_out_struct(struct_type: str) -> bool:
    for infos in handles.values():
        for method_info in infos["methods"].values():
            for arg in method_info["args"]:
                if _decay_eos_type(arg["type"]) == struct_type and arg[
                    "name"
                ].startswith("Out"):
                    return True

    for method_info in unhandled_methods.values():
        for arg in method_info["args"]:
            if _decay_eos_type(arg["type"]) == struct_type and arg["name"].startswith(
                "Out"
            ):
                print(f"Warning: ", struct_type)
                return True
    return False


def __is_input_struct(struct_type: str) -> bool:
    for infos in handles.values():
        for method_name in infos["methods"]:
            if method_name.endswith("Release"):
                # 不检查释放方法
                continue

            method_info = infos["methods"][method_name]
            for arg in method_info["args"]:
                if _decay_eos_type(arg["type"]) == struct_type and not arg[
                    "name"
                ].startswith("Out"):
                    return True

    for method_name in unhandled_methods:
        if method_name.endswith("Release"):
            # 不检查释放方法
            continue

        method_info = unhandled_methods[method_name]
        for arg in method_info["args"]:
            if _decay_eos_type(arg["type"]) == struct_type and not arg[
                "name"
            ].startswith("Out"):
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
    r_owned_structs.clear()
    for struct_name in structs:
        for field in structs[struct_name]:
            field_type = structs[struct_name][field]
            if (
                not struct_name in r_owned_structs
                and not _is_internal_struct_arr_field(field_type, field)
                and _decay_eos_type(field_type) == struct_type
            ):
                r_owned_structs.append(struct_name)
    return len(r_owned_structs) > 0


def __is_internal_struct_of_arr(struct_type: str, r_owned_structs: list[str]) -> bool:
    r_owned_structs.clear()
    if not _decay_eos_type(struct_type) in structs:
        return False
    for struct_name in structs:
        for field in structs[struct_name]:
            field_type = structs[struct_name][field]
            if (
                not struct_name in r_owned_structs
                and _is_internal_struct_arr_field(field_type, field)
                and _decay_eos_type(field_type) == struct_type
            ):
                r_owned_structs.append(struct_name)
    return len(r_owned_structs) > 0


def __is_method_input_only_struct(struct_type: str) -> bool:
    if not _decay_eos_type(struct_type) in structs:
        return False
    if __is_internal_struct_of_arr(struct_type, []) or __is_internal_struct_of_arr(
        struct_type, []
    ):
        return False
    if __is_arg_out_struct(struct_type) or __is_output_struct(struct_type):
        return False
    return True


def __is_callback_output_only_struct(struct_type: str) -> bool:
    if __is_internal_struct_of_arr(struct_type, []) or __is_internal_struct_of_arr(
        struct_type, []
    ):
        return False
    if __is_arg_out_struct(struct_type) or __is_input_struct(struct_type):
        return False
    return True


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
                    struct2additional_method_requirements[struct_name][
                        "set_to"
                    ] = True  # 不需要 to 附带的实例字段
                if __is_output_struct(s) or __is_arg_out_struct(s):
                    struct2additional_method_requirements[struct_name][
                        "set_from"
                    ] = True
                    struct2additional_method_requirements[struct_name]["from"] = True

    # 检出应该被展开为参数的结构体
    for struct_type in structs:
        field_count = len(structs[struct_type])
        if (
            max_options_fields_count_to_expend > 0
            and field_count <= max_options_fields_count_to_expend
            and __is_method_input_only_struct(struct_type)
        ):
            expended_as_args_structs.append(struct_type)
        if (
            max_callback_fields_count_to_expend > 0
            and field_count <= max_callback_fields_count_to_expend
            and __is_callback_output_only_struct(struct_type)
        ):
            expended_as_args_structs.append(struct_type)


def _parse_file(interface_lower: str, fp: str, r_file_lower2infos: dict[str, dict]):
    f = open(fp, "r")
    lines = f.readlines()
    f.close()

    i = 0
    while i < len(lines):
        line = lines[i]

        # 句柄类型 ApiVersion 宏
        if line.startswith("#define EOS_") and "_API_LATEST" in line:
            macro = line.split(" ", 2)[1]
            api_latest_macros.append(macro)
            i += 1
            continue

        # 句柄类型
        if "typedef struct " in line:  #  and "Handle*" in line
            handle_type = line.split("* ", 1)[1].split(";", 1)[0]
            r_file_lower2infos[interface_lower]["handles"][handle_type] = {
                "methods": {},
                "callbacks": {},
                "enums": {},
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

            r_file_lower2infos[interface_lower]["enums"][enum_type] = []

            i += 1
            while not lines[i].startswith(");"):
                line = lines[i].lstrip("\t").rstrip("\n").rstrip(",")
                if line.startswith(" ") or line.startswith("/"):
                    i += 1
                    continue

                splited = line.split(" = ")
                r_file_lower2infos[interface_lower]["enums"][enum_type].append(
                    splited[0]
                )
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
                "return": line.split("(", 1)[1].split(")")[0],
                "args": [],
            }
            args = line.split(" ", 1)[1].split("(", 1)[1].rsplit(")", 1)[0].split(", ")
            for a in args:
                if len(a) <= 0:
                    continue
                splited = a.rsplit(" ", 1)
                if splited[0] == "void":
                    continue
                method_info["args"].append(
                    {
                        "type": splited[0],
                        "name": splited[1],
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
                "return": args[0] if has_return else "",
                "args": [
                    {
                        "type": args[len(args) - 1].rsplit(" ", 1)[0],
                        "name": args[len(args) - 1].rsplit(" ", 1)[1],
                    }
                ],
            }

            i += 1
            continue

        # 结构体
        elif line.startswith("EOS_STRUCT"):
            i += 1

            struct_name = (
                line.lstrip("EOS_STRUCT").lstrip("(").rstrip("\n").rstrip(", (")
            )
            r_file_lower2infos[interface_lower]["structs"][struct_name] = {}

            while not lines[i].startswith("));"):
                line = lines[i].lstrip("\t").rstrip("\n")
                if (
                    line.startswith("/")
                    or line.startswith("*")
                    or line.startswith(" ")
                    or len(line) == 0
                ):
                    i += 1
                    continue

                line = line.rsplit(";")[0]
                if line.startswith("union"):
                    # Union
                    union_fileds = {}
                    i += 2
                    while not lines[i].lstrip("\t").startswith("}"):
                        line = lines[i].lstrip("\t").rstrip("\n")
                        if (
                            line.startswith("/")
                            or line.startswith("*")
                            or line.startswith(" ")
                            or len(line) == 0
                        ):
                            i += 1
                            continue
                        line = line.rsplit(";")[0]
                        splited = line.rsplit(" ", 1)
                        if len(splited) != 2:
                            print(f"-ERROR: {fp}:{i}\n")
                            print(f"{lines[i]}")
                        else:
                            union_fileds[splited[1]] = splited[0]
                        i += 1

                    union_type = "Union{"
                    for union_f in union_fileds.keys():
                        union_type += f"{union_fileds[union_f]} : {union_f}, "
                    union_type = union_type.rstrip(" ").rstrip(",") + "}"

                    field = (
                        lines[i]
                        .lstrip("\t")
                        .lstrip("}")
                        .lstrip(" ")
                        .rstrip("\n")
                        .rstrip(";")
                    )
                    r_file_lower2infos[interface_lower]["structs"][struct_name][
                        field
                    ] = union_type
                else:
                    # Regular
                    splited = line.rsplit(" ", 1)
                    if len(splited) != 2:
                        print(f"ERROR: {fp}:{i}\n")
                        print(f"{lines[i]}")
                    else:
                        r_file_lower2infos[interface_lower]["structs"][struct_name][
                            splited[1]
                        ] = splited[0]

                i += 1

            i += 1
            continue

        else:
            i += 1
            continue


def gen_interface_singletons() -> str:
    interface_lower2method_line: dict[str, list[str]] = {}

    f = open("src\ieos.h", "r")
    for l in f.readlines():
        line = l.lstrip(" ")
        if not "_interface_" in line:
            continue

        interface_lower = line.split(" ", 1)[1].split("_interface_")[0]

        if not interface_lower in interface_lower2method_line.keys():
            interface_lower2method_line[interface_lower] = []

        interface_lower2method_line[interface_lower].append(line.rstrip("\n"))
    f.close()

    lines: list[str] = ["#pragma once"]
    lines.append("")

    interfaces_lower = interface_lower2method_line.keys()

    for il in interfaces_lower:
        lines += _gen_interface(il, interface_lower2method_line[il])
    lines.append("")

    lines.append("// ========")
    lines.append("#define REGISTER_INTERFACE_SINGLETONS()\\")
    for il in interfaces_lower:
        klass = _convert_interface_class_name(il)
        lines.append(f"\tREGISTER_AND_ADD_SINGLETON(godot::{klass});\\")
    lines.append("")

    lines.append("// ========")
    lines.append("#define UNREGISTER_INTERFACE_SINGLETONS()\\")
    for il in interfaces_lower:
        klass = _convert_interface_class_name(il)
        lines.append(f"\tUNREGISTER_AND_DELETE_SINGLETON(godot::{klass});\\")
    lines.append("")

    lines.append("// ========")
    lines.append("#define DEFINE_INTERFACE_SINGLETONS()\\")
    for il in interfaces_lower:
        klass = _convert_interface_class_name(il)
        lines.append(f"\tgodot::{klass} *godot::{klass}::singleton = nullptr;\\")
    lines.append("")

    return "\n".join(lines)


def _convert_interface_class_name(interface_name_lower: str) -> str:
    splited_name = interface_name_lower.removeprefix("eos_").split("_")
    for i in range(len(splited_name)):
        if splited_name[i] in ["rtc", "p2p", "ui"]:
            splited_name[i] = splited_name[i].upper()
        elif splited_name[i] == "playerdatastorage":
            splited_name[i] = "PlayerDataStorage"
        elif splited_name[i] == "p2p":
            splited_name[i] = "P2P"
        elif splited_name[i] == "sdk":
            splited_name[i] = "Platform"
        elif splited_name[i] == "userinfo":
            splited_name[i] = "UserInfo"
        elif splited_name[i] == "titlestorage":
            splited_name[i] = "TitleStorage"
        elif splited_name[i] == "anticheatserver":
            splited_name[i] = "AntiCheatServer"
        elif splited_name[i] == "anticheatclient":
            splited_name[i] = "AntiCheatClient"
        elif splited_name[i] == "progressionsnapshot":
            splited_name[i] = "ProgressionSnapshot"
        elif splited_name[i] == "kws":
            splited_name[i] = "KWS"
        elif splited_name[i] == "custominvites":
            splited_name[i] = "CustomInvites"
        elif splited_name[i] == "integratedplatform":
            splited_name[i] = "IntegratedPlatform"
        else:
            splited_name[i] = splited_name[i].capitalize()

    return "EOS" + "".join(splited_name)


def _gen_interface(interface_name: str, method_lines: list[str]) -> list[str]:
    signals: list[str] = []
    methods: dict[str, list[str]] = {}

    klass = _convert_interface_class_name(interface_name)

    ret: list[str] = ["namespace godot {"]
    ret.append(f"class {klass} : public Object {{")
    ret.append(f"\tGDCLASS({klass}, Object)")
    ret.append("")
    ret.append(f"\tstatic {klass} *singleton;")
    ret.append("")
    ret.append("public:")
    ret.append(f"\tstatic {klass} *get_singleton() {{ return singleton; }}")
    ret.append("")

    # using enums
    has_enum = False
    for e in enum_types:
        if _is_need_skip_enum_type(e):
            continue
        if _get_enum_owned_interface(enum2file[e], e) != klass:
            continue
        ret.append(f"\tusing {_convert_enum_type(e)} = {e};")
        has_enum = True
    if has_enum:
        ret.append("")

    # methods
    for line in method_lines:
        method_declare = line.replace(f"{interface_name}_interface_", "").rstrip(";")
        origin_method = line.split(" ", 1)[1].split("(")[0]

        method_name = method_declare.split(" ", 1)[1].split("(")[0]

        args_declare = (
            method_declare.split(
                "(",
                1,
            )[1]
            .rstrip(")")
            .split(", ")
        )
        args_text = ""
        args: list[str] = []
        for ad in args_declare:
            if len(ad) <= 0:
                continue
            a = ad.rsplit(" ", 1)[1].lstrip("&").lstrip("*")
            args_text += a
            args_text += ", "
            args.append(f'"{a.lstrip("p").lstrip("_")}"')

        args_text = args_text.rstrip(", ")

        methods[method_name] = args

        if line.startswith("Signal") or "Callable" in method_declare:
            signal = method_name
            # 特殊处理
            remap: dict[str, str] = {
                "add_notify_audio_before_render": "audio_before_render",
                "add_notify_audio_before_send": "audio_before_send",
                "add_notify_audio_input_state": "audio_input_state",
                "add_notify_audio_output_state": "audio_output_state",
                "add_notify_participant_updated": "participant_updated",
                #
                "add_notify_disconnected": "disconnected",
                "add_notify_participant_status_changed": "participant_status_changed",
                "add_notify_room_statistics_updated": "room_statistics_updated",
            }

            if signal in remap.keys():
                signal = remap[signal]
            signals.append(signal + "_callback")

        ret.append(
            f'\t{method_declare.replace(" create(", " create_platform(")} {{ return IEOS::get_singleton()->{origin_method}({args_text}); }}'
        )
    ret.append("")

    # signal callbacks
    if len(signals):
        ret.append("private:")
        for signal_name in signals:
            ret.append(
                f'\tvoid {signal_name}(const Ref<EOSDataClass> &p_callback_data) {{ emit_signal(SNAME("{signal_name}"), p_callback_data); }}'
            )
        ret.append("")

    # bind methods
    ret.append("protected:")
    ret.append("\tstatic void _bind_methods() {")
    # - bind methods
    for method_name in methods.keys():
        args = ", ".join(methods[method_name])
        if len(args) > 0:
            args = ", " + args
        ret.append(
            f'\t\t_INTERFACE_BIND_METHOD({klass}, {method_name if method_name != "create" else "create_platform"}{args});'
        )

    # - bine signals
    if len(signals):
        ret.append("")
        for signal_name in signals:
            ret.append(
                f"\t\t_INTERFACE_BIND_SIGNAL({interface_name + '_interface_'}, {signal_name});"
            )
    # - bind enums
    has_enum = False
    for e in enum_types:
        if _is_need_skip_enum_type(e):
            continue
        if _get_enum_owned_interface(enum2file[e], e) != klass:
            continue
        if not has_enum:
            ret.append("")
            has_enum = True
        ret.append(f"\t\t_BIND_ENUM_{e}()")

    ret.append("\t}")
    ret.append("")

    if len(signals):
        ret.append("\tvoid _notification(int p_what) {")
        for signal_name in signals:
            ret.append(
                f"\t\t_CONNECT_INTERFACE_SIGNAL({interface_name + '_interface_'}, {signal_name}, {klass});"
            )
        ret.append("\t}")
        ret.append("")

    # ctor/dector
    ret.append("public:")
    ret.append(f"\t{klass}() {{")
    ret.append("\t\tERR_FAIL_COND(singleton != nullptr);")
    ret.append("\t\tsingleton = this;")
    ret.append("\t}")
    ret.append("")

    ret.append(f"\t~{klass}() {{")
    ret.append("\t\tERR_FAIL_COND(singleton != this);")
    ret.append("\t\tsingleton = nullptr;")
    ret.append("\t}")
    ret.append("};")
    ret.append("} // namesapce godot")
    ret.append("")

    has_enum = False
    for e in enum_types:
        if _is_need_skip_enum_type(e):
            continue
        if _get_enum_owned_interface(enum2file[e], e) != klass:
            continue
        ret.append(f"VARIANT_ENUM_CAST(godot::{klass}::{_convert_enum_type(e)});")
        has_enum = True
    if has_enum:
        ret.append("")

    return ret


def _decay_eos_type(t: str) -> str:
    ret = (
        t.lstrip("const")
        .lstrip(" ")
        .rstrip("*")
        .rstrip("&")
        .rstrip("*")
        .rstrip("&")
        .lstrip(" ")
        .rstrip(" ")
    )
    return ret


def _is_unused_struct(name: str) -> bool:
    return name in ["EOS_UI_Rect"]


def _is_client_data_field(type: str, field: str) -> bool:
    return type == "void*" and field == "ClientData"


def _is_internal_struct_field(type: str, field: str) -> bool:
    decayed = _decay_eos_type(type)
    if decayed in structs:
        return True
    return False


def _is_anticheat_client_handle_type(type: str) -> bool:
    return type == "EOS_AntiCheatCommon_ClientHandle"


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
    if type in [
        "const char*",
        "void*",
    ]:
        return False
    if type == "const void*":
        if field_or_arg in ["PlatformSpecificData", "SystemMemoryMonitorReport"]:
            return False

    if field_or_arg.startswith("Out") or field_or_arg.startswith("InOut"):
        if type.endswith("**") or type.endswith("*"):
            return False  # 目前未发现有数组类型的Out参数
    return type.endswith("*")


def _is_handle_type(type: str, filed: str = "") -> bool:
    # 有些为struct指针
    return type.startswith("EOS_H") or type in ["EOS_ContinuanceToken"]


def _find_count_field(field: str, fields: list[str]) -> str:
    splited = to_snake_case(field).split("_")
    similars_fileds: list[str] = []
    for f in fields:
        if f == fields:
            continue
        if (
            f.endswith("Count")
            or f.endswith("Size")
            or f.endswith("Length")
            or f.endswith("LengthBytes")
            or f.endswith("SizeBytes")
        ):
            fsplited = to_snake_case(f).split("_")
            similar = 0
            for i in range(min(2, len(fsplited), len(splited))):
                if fsplited[i].removesuffix("s").removesuffix("y") == splited[
                    i
                ].removesuffix("ies").removesuffix("s"):
                    similar += 1
                else:
                    break
            if similar >= min(2, len(fsplited), len(splited)):
                return f
            else:
                if similar > 0:
                    similars_fileds.append(f)
    if len(similars_fileds) == 1:
        return similars_fileds[0]

    print("== error:", field, similars_fileds)
    print(field, fields)
    # exit()


def _gen_struct(
    struct_type: str,
    fields: dict[str, str],
    r_structs_cpp: list[str],
) -> list[str]:
    lines: list[str] = [""]

    typename = __convert_to_struct_class(struct_type)

    lines.append(f"class {typename}: public EOSDataClass {{")
    lines.append(f"\tGDCLASS({typename}, EOSDataClass)")
    lines.append("")

    count_fields: list[str] = []
    variant_union_type_fileds: list[str] = []
    for field in fields.keys():
        if is_deprecated_field(field):
            continue

        field_type = fields[field]
        # 检出count字段，Godot不需要及将其作为成员
        if _is_arr_field(field_type, field) or _is_internal_struct_arr_field(
            field_type, field
        ):
            count_fields.append(_find_count_field(field, fields.keys()))

        # 检出Variant式的联合体类型字段，Godot不需要及将其作为成员
        if _is_variant_union_type(field_type, field):
            for f in fields.keys():
                if f == field + "Type":
                    variant_union_type_fileds.append(f)

    addtional_methods_requirements = struct2additional_method_requirements[struct_type]

    # 成员
    for field in fields.keys():
        if is_deprecated_field(field):
            continue
        if field in count_fields:
            continue

        type: str = remap_type(fields[field], field)
        initialize_expression = ""
        if type.startswith("Ref"):
            initialize_expression = f"{{ memnew({fields[field]}) }}"
        elif type == "int32_t" and field == "ApiVersion":
            api_verision_macro = __get_api_latest_macro(struct_type)
            initialize_expression = f"{{ {api_verision_macro} }}"

        lines.append(f"\t{type} {to_snake_case(field)}{initialize_expression};")

    if addtional_methods_requirements["to"]:
        lines.append("")
        lines.append(f"\t{struct_type} m_eos_data;")
    lines.append("")

    # setget
    lines.append("public:")
    for field in fields.keys():
        if is_deprecated_field(field):
            continue
        if field in count_fields:
            continue
        if field in variant_union_type_fileds:
            continue

        type: str = remap_type(fields[field], field)
        if type == "bool":
            lines.append(f"\t_DEFINE_SETGET_BOOL({to_snake_case(field)})")
        else:
            lines.append(f"\t_DEFINE_SETGET({to_snake_case(field)})")
    lines.append("")

    if addtional_methods_requirements["set_from"]:
        lines.append(f"\tvoid set_from_eos({struct_type} &p_origin);")
    if addtional_methods_requirements["from"]:
        lines.append(f"\tstatic Ref<{typename}> from_eos({struct_type} &p_origin);")
    if addtional_methods_requirements["set_to"]:
        lines.append(f"\tvoid set_to_eos({struct_type} &p_origin);")
    if addtional_methods_requirements["to"]:
        lines.append(
            f"\t{struct_type} &to_eos() {{set_to_eos(m_eos_data); return m_eos_data;}}"
        )

    # bind
    lines.append("protected:")
    lines.append("\tstatic void _bind_methods();")

    lines.append("};")
    lines.append("")

    # cpp bind methods
    r_structs_cpp.append(f"void godot::{typename}::_bind_methods() {{")
    r_structs_cpp.append(f"\tusing namespace godot;")
    r_structs_cpp.append(f"\t_BIND_BEGIN({typename})")
    for field in fields.keys():
        if is_deprecated_field(field):
            continue
        if field in count_fields:
            continue
        if field in variant_union_type_fileds:
            continue

        type: str = remap_type(fields[field], field)
        if type == "bool":
            r_structs_cpp.append(f"\t_BIND_PROP_BOOL({to_snake_case(field)})")
        else:
            r_structs_cpp.append(f"\t_BIND_PROP({to_snake_case(field)})")
    r_structs_cpp.append(f"\t_BIND_END()")
    r_structs_cpp.append("}")
    r_structs_cpp.append("")

    # ===
    if addtional_methods_requirements["from"]:
        r_structs_cpp.append(
            f"Ref<{typename}> godot::{typename}::from_eos({struct_type} &p_origin) {{"
        )
        r_structs_cpp.append(f"\tusing namespace godot;")
        r_structs_cpp.append(f"\tRef<{typename}> ret;")
        r_structs_cpp.append(f"\tret.instantiate();")
        r_structs_cpp.append(f"\tret->set_from_eos(p_origin);")
        r_structs_cpp.append(f"\treturn ret;")
        r_structs_cpp.append("}")

    if addtional_methods_requirements["set_from"]:
        r_structs_cpp.append(
            f"void godot::{typename}::set_from_eos({struct_type} &p_origin) {{"
        )
        r_structs_cpp.append(f"\tusing namespace godot;")
        for field in fields.keys():
            if is_deprecated_field(field):
                continue
            if field in count_fields:
                continue
            if field in variant_union_type_fileds:
                continue

            field_type = fields[field]
            if _is_anticheat_client_handle_type(field_type):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE({to_snake_case(field)}, p_origin.{field});"
                )
            elif _is_requested_channel_ptr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_REQUESTED_CHANNEL({to_snake_case(field)}, p_origin.{field});"
                )
            elif field_type.startswith("Union"):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_UNION({to_snake_case(field)}, p_origin.{field});"
                )
            elif _is_handle_type(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_HANDLER({to_snake_case(field)}, p_origin.{field});"
                )
            elif _is_client_data_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_CLIENT_DATA({to_snake_case(field)}, p_origin.{field});"
                )
            elif _is_internal_struct_arr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_STRUCT_ARR({__convert_to_struct_class(field_type)}, {to_snake_case(field)}, p_origin.{field}, p_origin.{_find_count_field(field, fields.keys())});"
                )
            elif _is_internal_struct_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_STRUCT({to_snake_case(field)}, p_origin.{field});"
                )
            if _is_arr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD_ARR({to_snake_case(field)}, p_origin.{field}, p_origin.{_find_count_field(field, fields.keys())});"
                )
            else:
                r_structs_cpp.append(
                    f"\t_FROM_EOS_FIELD({to_snake_case(field)}, p_origin.{field});"
                )
        r_structs_cpp.append("}")
    if addtional_methods_requirements["set_to"]:
        r_structs_cpp.append(
            f"void godot::{typename}::set_to_eos({struct_type} &p_data) {{"
        )
        # r_structs_cpp.append(f"\tmemset(&m_eos_data, 0, sizeof({struct_type}));")
        for field in fields.keys():
            if is_deprecated_field(field):
                continue
            if field in count_fields:
                continue
            if field in variant_union_type_fileds:
                continue

            field_type = fields[field]
            if _is_anticheat_client_handle_type(field_type):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE(p_data.{field}, {to_snake_case(field)});"
                )
            elif _is_requested_channel_ptr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_REQUESTED_CHANNEL(p_data.{field}, {to_snake_case(field)});"
                )
            elif field_type.startswith("Union"):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_UNION(p_data.{field}, {to_snake_case(field)});"
                )
            elif _is_handle_type(field_type, field):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_HANDLER(p_data.{field}, {to_snake_case(field)});"
                )
            elif _is_client_data_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_CLIENT_DATA(p_data.{field}, {to_snake_case(field)});"
                )
            elif _is_internal_struct_arr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_STRUCT_ARR({__convert_to_struct_class(field_type)}, p_data.{field}, {to_snake_case(field)}, p_data.{_find_count_field(field, fields.keys())});"
                )
            elif _is_internal_struct_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_STRUCT(p_data.{field}, {to_snake_case(field)});"
                )
            elif _is_arr_field(field_type, field):
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD_ARR(p_data.{field}, {to_snake_case(field)}, p_data.{_find_count_field(field, fields.keys())});"
                )
            else:
                r_structs_cpp.append(
                    f"\t_TO_EOS_FIELD(p_data.{field}, {to_snake_case(field)});"
                )
        r_structs_cpp.append("}")

    return lines


if __name__ == "__main__":
    main()

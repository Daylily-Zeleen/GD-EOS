# 类型判断与转换工具

import re

from binding_generator.config import generate_config
from binding_generator.context import (
    api_latest_macros,
    expanded_as_args_structs,
    generate_infos,
    handles,
    interfaces,
    struct2additional_method_requirements,
    structs,
    unhandled_callbacks,
    unhandled_constants,
    unhandled_enums,
    unhandled_methods,
)
from binding_generator.models import Arg, Callback, Method, StructField
from binding_generator.utils.naming import (
    convert_handle_class_name,
    convert_to_struct_class,
    decay_eos_type,
    is_out_param_name,
    to_snake_case,
)


def is_enum_type(type: str) -> bool:
    for h in handles:
        if type in handles[h].enums:
            return True
    if type in unhandled_enums:
        print(f"[type] 警告: 枚举类型 '{type}' 未被处理")
        return True
    return False


def is_handle_type(type: str, field: str = "") -> bool:
    return type in handles or (type.startswith("EOS") and "_H" in type) or type in ["EOS_ContinuanceToken"]


def is_handle_arr_type(type: str, name: str) -> bool:
    suffix: str = "**" if is_out_param_name(name) else "*"
    if not type.endswith(suffix):
        return False
    return is_handle_type(decay_eos_type(type))


_SPECIAL_BUILTIN_TYPES = frozenset(("EOS_AntiCheatCommon_Vec3f", "EOS_AntiCheatCommon_Quat"))


def is_special_builtin_type(type: str) -> bool:
    return type in _SPECIAL_BUILTIN_TYPES


def is_struct_type(type: str) -> bool:
    if is_socket_id_type(decay_eos_type(type), ""):
        return False
    if is_special_builtin_type(type):
        return False
    return type in structs


_callback_type_name_pattern = re.compile(r"Callback(?:V\d+)?$")


def is_callback_type_name(type_name: str) -> bool:
    return _callback_type_name_pattern.search(type_name) is not None


_callback_types_cache: set[str] | None = None


def is_callback_type(type: str) -> bool:
    global _callback_types_cache
    if _callback_types_cache is None:
        _callback_types_cache = set()
        for h in handles:
            _callback_types_cache.update(handles[h].callbacks.keys())
        _callback_types_cache.update(unhandled_callbacks.keys())
    return type in _callback_types_cache


def is_client_data(type: str, name: str) -> bool:
    return type == "void*" and name == "ClientData"


def is_api_version_field(type: str, name: str) -> bool:
    return type == "int32_t" and name == "ApiVersion"


def get_struct_fields(type: str) -> dict[str, StructField]:
    return structs[decay_eos_type(type)].fields


def is_expanded_struct(struct_type: str) -> bool:
    if struct_type in [
        "EOS_PlayerDataStorage_ReadFileDataCallbackInfo",
        "EOS_PlayerDataStorage_WriteFileDataCallbackInfo",
        "EOS_PlayerDataStorage_FileTransferProgressCallbackInfo",
        "EOS_PlayerDataStorage_WriteFileCallbackInfo",
        "EOS_PlayerDataStorage_ReadFileCallbackInfo",
        "EOS_IntegratedPlatform_UserPreLogoutCallbackInfo",
        "EOS_PlayerDataStorage_WriteFileOptions",
        "EOS_PlayerDataStorage_ReadFileOptions",
        "EOS_TitleStorage_ReadFileOptions",
        "EOS_Connect_LoginCallbackInfo",
        "EOS_Connect_LoginStatusChangedCallbackInfo",
        "EOS_Auth_LoginCallbackInfo",
    ]:
        return False
    if struct_type in ["EOS_LogMessage"]:
        return True
    return decay_eos_type(struct_type) in expanded_as_args_structs


_arg_out_struct_cache: set[str] = set()
_input_struct_ptr_cache: set[str] = set()
_input_struct_non_ptr_cache: set[str] = set()
_output_struct_cache: set[str] = set()


def _compute_struct_type_caches():
    global _arg_out_struct_cache, _input_struct_ptr_cache, _input_struct_non_ptr_cache, _output_struct_cache
    _arg_out_struct_cache.clear()
    _input_struct_ptr_cache.clear()
    _input_struct_non_ptr_cache.clear()
    _output_struct_cache.clear()

    for infos in handles.values():
        for method_info in infos.methods.values():
            for arg in method_info.args:
                decayed = decay_eos_type(arg.type)
                if arg.name.startswith("Out"):
                    _arg_out_struct_cache.add(decayed)
                else:
                    if arg.type.endswith("*"):
                        _input_struct_ptr_cache.add(decayed)
                    else:
                        _input_struct_non_ptr_cache.add(decayed)
            decayed_ret = decay_eos_type(method_info.return_type)
            _output_struct_cache.add(decayed_ret)
        for callback_info in infos.callbacks.values():
            for arg in callback_info.args:
                _output_struct_cache.add(decay_eos_type(arg.type))

    for method_info in unhandled_methods.values():
        for arg in method_info.args:
            decayed = decay_eos_type(arg.type)
            if arg.name.startswith("Out"):
                _arg_out_struct_cache.add(decayed)
            else:
                if arg.type.endswith("*"):
                    _input_struct_ptr_cache.add(decayed)
                else:
                    _input_struct_non_ptr_cache.add(decayed)
        _output_struct_cache.add(decay_eos_type(method_info.return_type))

    for callback_info in unhandled_callbacks.values():
        for arg in callback_info.args:
            _output_struct_cache.add(decay_eos_type(arg.type))


def _is_arg_out_struct(struct_type: str) -> bool:
    return struct_type in _arg_out_struct_cache


def _is_input_struct(struct_type: str) -> bool:
    if is_integrated_platform_init_option_type(struct_type):
        return True
    return struct_type in _input_struct_ptr_cache or struct_type in _input_struct_non_ptr_cache


def _is_input_struct_ptr(struct_type: str) -> bool:
    if is_integrated_platform_init_option_type(struct_type):
        return True
    return struct_type in _input_struct_ptr_cache


def _is_input_struct_non_ptr(struct_type: str) -> bool:
    return struct_type in _input_struct_non_ptr_cache


def _is_output_struct(struct_type: str) -> bool:
    return struct_type in _output_struct_cache


_internal_struct_cache: dict[str, list[str]] = {}
_internal_struct_of_arr_cache: dict[str, list[str]] = {}


def _compute_internal_structs():
    _internal_struct_cache.clear()
    _internal_struct_of_arr_cache.clear()

    for struct_type in structs:
        owned: list[str] = []
        if is_integrated_platform_init_option_type(struct_type):
            _internal_struct_cache[struct_type] = []
            continue
        for struct_name in structs:
            fields: dict = get_struct_fields(struct_name)
            for field in fields:
                field_type: str = fields[field].type
                if struct_name not in owned and not is_internal_struct_arr_field(field_type, field, struct_name) and decay_eos_type(field_type) == struct_type:
                    owned.append(struct_name)
        _internal_struct_cache[struct_type] = owned.copy()

    for struct_type in structs:
        owned: list[str] = []
        if decay_eos_type(struct_type) not in structs:
            _internal_struct_of_arr_cache[struct_type] = []
            continue
        for struct_name in structs:
            fields = get_struct_fields(struct_name)
            for field in fields:
                field_type = fields[field].type
                if struct_name not in owned and is_internal_struct_arr_field(field_type, field, struct_name) and decay_eos_type(field_type) == struct_type:
                    owned.append(struct_name)
        _internal_struct_of_arr_cache[struct_type] = owned.copy()


def _is_internal_struct(struct_type: str, r_owned_structs: list[str]) -> bool:
    if struct_type in _internal_struct_cache:
        r_owned_structs.clear()
        r_owned_structs.extend(_internal_struct_cache[struct_type])
        return len(r_owned_structs) > 0
    if is_integrated_platform_init_option_type(struct_type):
        return False
    r_owned_structs.clear()
    for struct_name in structs:
        fields: dict = get_struct_fields(struct_name)
        for field in fields:
            field_type: str = fields[field].type
            if struct_name not in r_owned_structs and not is_internal_struct_arr_field(field_type, field, struct_name) and decay_eos_type(field_type) == struct_type:
                r_owned_structs.append(struct_name)
    return len(r_owned_structs) > 0


def _is_internal_struct_of_arr(struct_type: str, r_owned_structs: list[str]) -> bool:
    if struct_type in _internal_struct_of_arr_cache:
        r_owned_structs.clear()
        r_owned_structs.extend(_internal_struct_of_arr_cache[struct_type])
        return len(r_owned_structs) > 0
    r_owned_structs.clear()
    if decay_eos_type(struct_type) not in structs:
        return False
    for struct_name in structs:
        fields = get_struct_fields(struct_name)
        for field in fields:
            field_type = fields[field].type
            if struct_name not in r_owned_structs and is_internal_struct_arr_field(field_type, field, struct_name) and decay_eos_type(field_type) == struct_type:
                r_owned_structs.append(struct_name)
    return len(r_owned_structs) > 0


def is_method_input_only_struct(struct_type: str) -> bool:
    if decay_eos_type(struct_type) not in structs:
        return False
    if _is_internal_struct(struct_type, []) or _is_internal_struct_of_arr(struct_type, []):
        return False
    if _is_arg_out_struct(struct_type) or _is_output_struct(struct_type):
        return False
    for infos in generate_infos.values():
        for m_info in infos.methods.values():
            for arg in m_info.args:
                if struct_type == decay_eos_type(arg.type):
                    return True
        for h_info in infos.handles.values():
            methods = h_info.methods
            for m_info in methods.values():
                for arg in m_info.args:
                    if struct_type == decay_eos_type(arg.type):
                        return True
    return False


def _is_callback_output_only_struct(struct_type: str) -> bool:
    if _is_internal_struct_of_arr(struct_type, []) or _is_internal_struct_of_arr(struct_type, []):
        return False
    if _is_arg_out_struct(struct_type) or _is_input_struct(struct_type):
        return False
    for infos in generate_infos.values():
        for cb_info in infos.callbacks.values():
            for arg in cb_info.args:
                if struct_type == decay_eos_type(arg.type):
                    return True
        for h_info in infos.handles.values():
            for cb_info in h_info.callbacks.values():
                for arg in cb_info.args:
                    if struct_type == decay_eos_type(arg.type):
                        return True
    return False


def make_additional_method_requirements():
    _compute_struct_type_caches()
    _compute_internal_structs()

    for struct_name in structs:
        struct2additional_method_requirements[struct_name] = {
            "set_from": False,
            "from": False,
            "set_to": False,
            "to": False,
        }
        if _is_input_struct_ptr(struct_name):
            struct2additional_method_requirements[struct_name]["to"] = True
            struct2additional_method_requirements[struct_name]["set_to"] = True
        if _is_input_struct_non_ptr(struct_name):
            struct2additional_method_requirements[struct_name]["set_to"] = True
        if _is_output_struct(struct_name):
            struct2additional_method_requirements[struct_name]["set_from"] = True
            struct2additional_method_requirements[struct_name]["from"] = True
        if _is_arg_out_struct(struct_name):
            struct2additional_method_requirements[struct_name]["set_from"] = True
    for struct_name in structs:
        owned_structs: list[str] = []
        if _is_internal_struct(struct_name, owned_structs):
            for s in owned_structs:
                if struct2additional_method_requirements[s]["set_to"]:
                    struct2additional_method_requirements[struct_name]["set_to"] = True
                if struct2additional_method_requirements[s]["to"]:
                    struct2additional_method_requirements[struct_name]["to"] = True
                if struct2additional_method_requirements[s]["set_from"]:
                    struct2additional_method_requirements[struct_name]["set_from"] = True
        owned_structs.clear()
        if _is_internal_struct_of_arr(struct_name, owned_structs):
            for s in owned_structs:
                if _is_input_struct_ptr(s) or _is_input_struct_non_ptr(s):
                    struct2additional_method_requirements[struct_name]["set_to"] = True
                if _is_output_struct(s) or _is_arg_out_struct(s):
                    struct2additional_method_requirements[struct_name]["set_from"] = True
                    struct2additional_method_requirements[struct_name]["from"] = True
    for struct_type in structs:
        fields = get_struct_fields(struct_type)
        field_count: int = (
            len(fields)
            - (1 if "ClientData" in fields else 0)
            - (1 if "ApiVersion" in fields else 0)
            - (1 if generate_config.assume_only_one_local_user and "LocalUserId" in fields and need_ignore_local_user_id_struct(struct_type) else 0)
        )
        if generate_config.min_field_count_to_expand_input_structs > 0 and field_count <= generate_config.min_field_count_to_expand_input_structs and is_method_input_only_struct(struct_type):
            expanded_as_args_structs.append(struct_type)
        if generate_config.min_field_count_to_expand_callback_structs > 0 and field_count <= generate_config.min_field_count_to_expand_callback_structs and _is_callback_output_only_struct(struct_type):
            expanded_as_args_structs.append(struct_type)


def is_need_skip_constant(name: str) -> bool:
    return (
        name
        in [
            "EOS_ANTICHEATCLIENT_PEER_SELF",
        ]
        or "_RESERVED" in name
    )


def is_string_constant(val: str) -> bool:
    return val.startswith("(const char*)") or val.startswith('"')


def is_need_skip_struct(struct_type: str) -> bool:
    return (
        struct_type
        in [
            "EOS_AntiCheatCommon_Quat",
            "EOS_AntiCheatCommon_Vec3f",
            "EOS_P2P_SocketId",
            "EOS_UI_Rect",
        ]
        or "_Reserved" in struct_type
    )


def is_need_skip_callback(callback_type: str) -> bool:
    return callback_type in ["EOS_IntegratedPlatform_OnUserPreLogoutCallback"]


def is_need_skip_method(method_name: str) -> bool:
    return (
        method_name
        in [
            "EOS_ByteArray_ToString",
        ]
        or "_Reserved" in method_name
    )


def is_need_skip_enum_type(ori_enum_type: str) -> bool:
    return ori_enum_type in []


def is_need_skip_enum_value(ori_enum_type: str, enum_value: str) -> bool:
    return False


def get_enum_owned_interface(ori_enum_type: str) -> str:
    for infos in generate_infos.values():
        if ori_enum_type in infos.enums:
            print(f"[type] 不支持的枚举类型 '{ori_enum_type}'，已存在于生成信息中")
            print_stack_and_exit()
        for h in infos.handles:
            if ori_enum_type in infos.handles[h].enums:
                return convert_handle_class_name(h)
    print(f"[type] 不支持的枚举类型 '{ori_enum_type}'，找不到对应的句柄类")
    print_stack_and_exit()


def is_reserved_field(field: str, type: str) -> bool:
    return field == "Reserved" and type == "void*"


def is_internal_platform_specific_field(field: str) -> bool:
    return field in [
        "SystemSpecificOptions",
        "SystemAuthCredentialsOptions",
        "SystemMemoryMonitorReport",
        "PlatformSpecificData",
    ]


def remap_type(type: str, field: str = "", forward_declare: bool = False, struct_name: str = "") -> str:
    if is_enum_type(type):
        return type
    if is_struct_type(type):
        if forward_declare:
            return f"Ref<class {convert_to_struct_class(type)}>"
        else:
            return f"Ref<{convert_to_struct_class(type)}>"
    if is_handle_arr_type(type, field):
        return f"TypedArray<{convert_handle_class_name(type)}>"
    if is_handle_type(type, field):
        if forward_declare:
            return f"Ref<class {convert_handle_class_name(type)}>"
        else:
            return f"Ref<{convert_handle_class_name(type)}>"
    if is_internal_struct_arr_field(type, field, struct_name):
        return f"TypedArray<{convert_to_struct_class(decay_eos_type(type))}>"
    if is_callback_type(decay_eos_type(type)):
        return "Callable"

    if type.startswith("Union") and len(field):
        union_field_map: dict[str, str] = {
            "ParamValue": "Variant",
            "Value": "Variant",
            "AccountId": "String",
        }
        return union_field_map[field]

    simple_remap: dict[str, str] = {
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
        "EOS_LobbyId": "String",
        "const EOS_LobbyId": "String",
        "const char*": "String",
        "EOS_Ecom_SandboxId": "String",
        "const EOS_Ecom_CatalogItemId*": "PackedStringArray",
        "EOS_AntiCheatCommon_Vec3f*": "Vector3",
        "EOS_AntiCheatCommon_Quat*": "Quaternion",
        "const char**": "PackedStringArray",
        "EOS_Ecom_CatalogOfferId": "String",
        "EOS_Ecom_EntitlementId": "String",
        "EOS_Ecom_CatalogItemId": "String",
        "EOS_Ecom_EntitlementName": "String",
        "EOS_Ecom_EntitlementId*": "PackedStringArray",
        "EOS_Ecom_CatalogItemId*": "PackedStringArray",
        "EOS_Ecom_SandboxId*": "PackedStringArray",
        "const char* const*": "PackedStringArray",
        "EOS_Ecom_EntitlementName*": "PackedStringArray",
        "EOS_OnlinePlatformType": "uint32_t",
        "EOS_IntegratedPlatformType": "String",
        "Union{EOS_AntiCheatCommon_ClientHandle : ClientHandle, const char* : String, uint32_t : UInt32, in, EOS_AntiCheatCommon_Vec3f : Vec3f, EOS_AntiCheatCommon_Quat : Quat}": "Variant",
        "Union{int64_t : AsInt64, double : AsDouble, EOS_Bool : AsBool, const char* : AsUtf8}": "Variant",
        "Union{EOS_EpicAccountId : Epic, const char* : External}": "String",
        "EOS_AntiCheatCommon_ClientHandle": "handle_int_t<EOS_AntiCheatCommon_ClientHandle>",
    }

    condition_remap: dict[str, dict[str, str]] = {
        "void*": {"ClientData": "Variant"},
        "const void*": {
            "InitOptions": "Ref<class EOSIntegratedPlatformInitOptions>",
            "DataChunk": "PackedByteArray",
            "MessageData": "PackedByteArray",
            "Data": "PackedByteArray",
            "SystemSpecificOptions": "Variant",
            "PlatformSpecificData": "Variant",
            "SystemMemoryMonitorReport": "Variant",
        },
        "char": {
            "SocketName[EOS_P2P_SOCKETID_SOCKETNAME_SIZE]": "String",
        },
        "const uint8_t*": {
            "RequestedChannel": "int16_t",
        },
        "int16_t*": {"Frame": "PackedInt32Array"},
        "const uint32_t*": {"AllowedPlatformIds": "PackedInt32Array"},
    }

    if type in condition_remap.keys():
        return condition_remap[type].get(field, "Variant")

    return simple_remap.get(type, type)


def is_client_data_field(type: str, field: str) -> bool:
    return type == "void*" and field == "ClientData"


def is_internal_struct_field(type: str, field: str) -> bool:
    decayed: str = decay_eos_type(type)
    if is_special_builtin_type(decayed):
        return False
    if decayed in structs:
        return True
    return False


def is_pure_handle_type(type: str) -> bool:
    return type in ["EOS_AntiCheatCommon_ClientHandle"]


def is_variant_union_type(type: str, field: str) -> bool:
    return type.startswith("Union") and field != "AccountId"


_COUNT_FIELD_SUFFIXES = ("Count", "Size", "Length", "LengthBytes", "SizeBytes")


def _is_similar_field_name(f: str, field: str) -> bool:
    f_splits: list[str] = to_snake_case(f).split("_")
    splits: list[str] = to_snake_case(field).split("_")
    similar: int = 0
    for i in range(min(2, len(f_splits), len(splits))):
        if f_splits[i].removesuffix("s").removesuffix("y") == splits[i].removesuffix("ies").removesuffix("s"):
            similar += 1
        else:
            break
    return similar >= min(2, len(f_splits), len(splits))


def find_count_field(field: str, fields: list[str]) -> str:
    splits: list[str] = to_snake_case(field).split("_")
    similar_fields: list[str] = []
    for f in fields:
        if f == field:
            continue
        if f.endswith(_COUNT_FIELD_SUFFIXES):
            if _is_similar_field_name(f, field):
                return f
            f_splits: list[str] = to_snake_case(f).split("_")
            similar: int = 0
            for i in range(min(2, len(f_splits), len(splits))):
                if f_splits[i].removesuffix("s").removesuffix("y") == splits[i].removesuffix("ies").removesuffix("s"):
                    similar += 1
                else:
                    break
            if similar > 0:
                similar_fields.append(f)
    if len(similar_fields) == 1:
        return similar_fields[0]
    print(f"[type] 字段 '{field}' 匹配到多个相似字段: {similar_fields}")
    print(f"[type] 可用字段列表: {list(fields)}")
    print_stack_and_exit()


def _has_count_field(field: str, fields: list[str]) -> bool:
    for f in fields:
        if f == field:
            continue
        if f.endswith(_COUNT_FIELD_SUFFIXES[:3]) and _is_similar_field_name(f, field):
            return True
    return False


_is_internal_struct_arr_field_cache: dict[tuple[str, str, str], bool] = {}


def is_internal_struct_arr_field(type: str, field: str, struct_name: str = "") -> bool:
    cache_key = (type, field, struct_name)
    if cache_key in _is_internal_struct_arr_field_cache:
        return _is_internal_struct_arr_field_cache[cache_key]

    decayed: str = decay_eos_type(type)
    if is_special_builtin_type(decayed):
        _is_internal_struct_arr_field_cache[cache_key] = False
        return False
    if decayed not in structs:
        _is_internal_struct_arr_field_cache[cache_key] = False
        return False
    if is_handle_type(decayed):
        _is_internal_struct_arr_field_cache[cache_key] = False
        return False
    if not type.endswith("*"):
        _is_internal_struct_arr_field_cache[cache_key] = False
        return False
    if struct_name:
        if struct_name not in structs:
            _is_internal_struct_arr_field_cache[cache_key] = False
            return False
        fields: dict = structs[struct_name].fields
        if field in fields and fields[field].type == type:
            if _has_count_field(field, list(fields.keys())):
                _is_internal_struct_arr_field_cache[cache_key] = True
                return True
        _is_internal_struct_arr_field_cache[cache_key] = False
        return False
    for sn in structs:
        fields: dict = structs[sn].fields
        if field in fields and fields[field].type == type:
            if _has_count_field(field, list(fields.keys())):
                _is_internal_struct_arr_field_cache[cache_key] = True
                return True
    _is_internal_struct_arr_field_cache[cache_key] = False
    return False


def is_requested_channel_ptr_field(type: str, field: str) -> bool:
    return type == "const uint8_t*" and field == "RequestedChannel"


def is_arr_field(type: str, field_or_arg: str, struct_name: str = "") -> bool:
    if is_internal_struct_arr_field(type, field_or_arg, struct_name):
        return False
    if is_internal_struct_field(type, field_or_arg):
        return False
    if is_requested_channel_ptr_field(type, field_or_arg):
        return False
    if is_nullable_float_pointer_field(type, field_or_arg):
        return False
    if type in [
        "const char*",
        "void*",
    ]:
        return False
    if type == "const void*":
        if field_or_arg in [
            "PlatformSpecificData",
            "SystemMemoryMonitorReport",
            "InitOptions",
        ]:
            return False
    if is_special_builtin_type(decay_eos_type(type)):
        return False
    if is_out_param_name(field_or_arg) and type.endswith(("*", "**")):
        return False
    return type.endswith("*")


def is_todo_field(type: str, field: str) -> bool:
    map: dict[str, list[str]] = {}
    return type in map and field in map[type]


def is_system_initialize_options_filed(field: str, type: str) -> bool:
    return field == "SystemInitializeOptions" and type == "void*"


def is_platform_specific_options_field(field: str) -> bool:
    return field == "PlatformSpecificOptions"


def is_memory_func_type(type: str) -> bool:
    return type in [
        "EOS_AllocateMemoryFunc",
        "EOS_ReallocateMemoryFunc",
        "EOS_ReleaseMemoryFunc",
    ]


def is_integrated_platform_init_option_type(decayed_type: str) -> bool:
    return decayed_type == "EOS_IntegratedPlatform_Steam_Options"


def is_integrated_platform_init_option(struct_name: str, field: str) -> bool:
    return struct_name == "EOS_IntegratedPlatform_Options" and field == "InitOptions"


def is_nullable_float_pointer_field(type: str, field: str) -> bool:
    map: dict[str, list[str]] = {"double*": ["TaskNetworkTimeoutSeconds"]}
    return type in map and field in map[type]


def is_struct_ptr(type: str) -> bool:
    return type.endswith("*") and is_special_builtin_type(type.removesuffix("*"))


def is_str_type(type: str, name: str) -> bool:
    if is_socket_id_type(type, name):
        return True
    return not type.startswith("Union") and remap_type(type, name) == "String"


def is_str_arr_type(type: str, name: str) -> bool:
    return remap_type(type, name) == "PackedStringArray"


def is_socket_id_type(type: str, name: str) -> bool:
    return type == "EOS_P2P_SocketId"


def is_audio_frames_type(type: str, field: str) -> bool:
    map: dict[str, list[str]] = {"int16_t*": ["Frames"]}
    return type in map and field in map[type]


def is_local_user_id(field: str) -> bool:
    return field == "LocalUserId"


def get_login_interface_of_local_user_id(field: str, eos_type: str) -> str:
    _assert_is_local_user_id(field)
    interface_lower: str = ""
    if decay_eos_type(eos_type) == "EOS_ProductUserId":
        interface_lower = "eos_connect"
    else:
        interface_lower = "eos_auth"
    from binding_generator.utils.naming import convert_interface_class_name

    return convert_interface_class_name(interface_lower)


def get_gd_type_of_local_user_id(field: str, eos_type: str) -> str:
    _assert_is_local_user_id(field)
    return convert_handle_class_name(decay_eos_type(eos_type))


def _assert_is_local_user_id(field: str):
    assert_condition(field == "LocalUserId")


def is_enum_flags_type(type: str) -> bool:
    return is_enum_type(type) and (type.endswith("Flags") or type.endswith("Combination"))


def need_ignore_local_user_id_struct(struct_type: str) -> bool:
    struct_type = decay_eos_type(struct_type)
    for prefix in [
        "EOS_Achievements_",
        "EOS_Connect_",
        "EOS_Auth_",
    ]:
        if struct_type.startswith(prefix):
            return False
    return True


def need_check_null_local_user_id_struct(struct_type: str) -> bool:
    struct_type = decay_eos_type(struct_type)
    return (
        struct_type
        not in [
            "EOS_AntiCheatServer_BeginSessionOptions",
            "EOS_Connect_QueryProductUserIdMappingsOptions",
            "EOS_Stats_IngestStatOptions",
            "EOS_Stats_QueryStatsOptions",
        ]
        and not struct_type.startswith("EOS_TitleStorage_")
        and not struct_type.startswith("EOS_Achievements_")
    )


def find_count_and_variant_type_fields_in_struct(struct_type: str) -> list[str]:
    ret: list[str] = []
    fields: dict = structs[struct_type].fields
    for field in fields.keys():
        if is_internal_platform_specific_field(field) or fields[field].deprecated:
            ret.append(field)
            continue
        field_type: str = fields[field].type
        if is_arr_field(field_type, field, struct_type) or is_internal_struct_arr_field(field_type, field, struct_type):
            ret.append(find_count_field(field, list(fields.keys())))
        elif is_variant_union_type(field_type, field):
            for f in fields.keys():
                if f == field + "Type":
                    ret.append(f)
                    break
    return ret


def get_str_arr_element_type(str_arr_type: str) -> str:
    if str_arr_type.startswith("const char*"):
        return "const char *"
    return str_arr_type.removesuffix("*").removeprefix("const ")


_struct_api_macro_cache: dict[str, str] = {}
_API_LATEST_PATTERN = re.compile(r"\b(EOS_[A-Z0-9_]+_API_LATEST)\b")


def get_api_latest_macro(struct_type: str) -> str:
    global _struct_api_macro_cache
    if struct_type in _struct_api_macro_cache:
        return _struct_api_macro_cache[struct_type]

    macro: str = ""

    def _find_macro_from_doc() -> str | None:
        if struct_type not in structs:
            return None
        fields = structs[struct_type].fields
        if "ApiVersion" not in fields:
            print(f"[type] 获取 API_LATEST 宏失败: 结构体 '{struct_type}' 没有 ApiVersion 字段")
            return None

        doc = fields["ApiVersion"].doc
        for line in doc:
            for match in _API_LATEST_PATTERN.finditer(line):
                candidate = match.group(1)
                if candidate in api_latest_macros:
                    return candidate
        return None

    if (macro_from_doc := _find_macro_from_doc()) is not None:
        macro = macro_from_doc

    if len(macro) == 0:
        struct_upper = struct_type.upper()
        for suffix in ["_API_LATEST", "OPTIONS_API_LATEST", "_OPTIONS_API_LATEST"]:
            if (macro_with_suffix := struct_upper + suffix) in api_latest_macros:
                macro = macro_with_suffix
                break

        if len(macro) == 0:
            struct_no_options = struct_type.removesuffix("Options")
            if (macro_with_suffix := struct_no_options + "_API_LATEST") in api_latest_macros:
                macro = macro_with_suffix

    if len(macro) == 0:
        print(f"[type] 获取 API_LATEST 宏失败: 结构体 '{struct_type}'")

    _struct_api_macro_cache[struct_type] = macro
    return macro


_STR_MAX_LENGTH_SUFFIXES = (
    "_MAX_LENGTH",
    "_BUFFER_SIZE",
    "_MAXIMUM_LENGTH",
    "_MAX_LENGTH_BYTES",
)
_STR_MAX_LENGTH_PATTERN = re.compile(r"\b(EOS_[A-Z0-9_]+(?:MAX_LENGTH|BUFFER_SIZE|MAXIMUM_LENGTH|MAX_LENGTH_BYTES))\b")

_DEFAULT_STR_BUFFER_SIZE = "256"

_method_to_macro_cache: dict[str, str | None] | None = None


def get_str_result_max_length_macro(method_name: str) -> str:
    global _method_to_macro_cache
    if _method_to_macro_cache is None:
        # 内联 _build_method_macro_cache 逻辑
        macros_cache: dict[str, str] = {}
        for h in handles:
            for c_name, c in handles[h].constants.items():
                if c_name.endswith(_STR_MAX_LENGTH_SUFFIXES):
                    macros_cache[c_name] = c.value
        for c_name, c in unhandled_constants.items():
            if c_name.endswith(_STR_MAX_LENGTH_SUFFIXES):
                macros_cache[c_name] = c.value

        def find_from_doc(method_name: str, handle_name: str) -> str | None:
            if handle_name not in handles or method_name not in handles[handle_name].methods:
                return None
            doc: list[str] = handles[handle_name].methods[method_name].doc
            for line in doc:
                for match in _STR_MAX_LENGTH_PATTERN.finditer(line):
                    candidate = match.group(1)
                    if candidate in macros_cache:
                        return candidate
            return None

        def find_from_constants(method_name: str, handle_name: str) -> str | None:
            prefixes: list[str] = []
            if handle_name.startswith("EOS_H"):
                prefixes.append("EOS_" + handle_name[5:].upper() + "_")
            elif handle_name.startswith("EOS_") and "_H" in handle_name:
                module_part: str = handle_name[4 : handle_name.index("_H")]
                prefixes.append("EOS_" + module_part.upper() + "_")
                prefixes.append("EOS_" + handle_name[4:].upper() + "_")
            elif handle_name == "EOS":
                prefixes.append("EOS_")
            elif handle_name.startswith("EOS_"):
                prefixes.append(handle_name.upper() + "_")

            candidates: list[str] = []
            for macro_name in macros_cache:
                for prefix in prefixes:
                    if macro_name.startswith(prefix):
                        candidates.append(macro_name)
                        break

            if len(candidates) == 0:
                return None

            method_upper: str = method_name.upper()
            for macro_name in candidates:
                best_prefix: str = ""
                for prefix in prefixes:
                    if macro_name.startswith(prefix) and len(prefix) > len(best_prefix):
                        best_prefix = prefix
                macro_key: str = macro_name[len(best_prefix) :]
                for suffix in _STR_MAX_LENGTH_SUFFIXES:
                    if macro_key.endswith(suffix):
                        macro_key = macro_key[: -len(suffix)]
                        break
                if macro_key and macro_key in method_upper:
                    return macro_name

            if len(candidates) == 1:
                return candidates[0]

            return None

        cache: dict[str, str | None] = {}
        for h in handles:
            for m_name in handles[h].methods:
                macro: str | None = find_from_doc(m_name, h)
                if macro is None:
                    macro = find_from_constants(m_name, h)
                cache[m_name] = macro

        _method_to_macro_cache = cache
    macro = _method_to_macro_cache.get(method_name)
    if macro is not None:
        return macro
    return _DEFAULT_STR_BUFFER_SIZE


def has_str_result_max_length_macro(method_name: str) -> bool:
    return get_str_result_max_length_macro(method_name) != _DEFAULT_STR_BUFFER_SIZE


def get_callback_infos(callback_type: str) -> Callback:
    for infos in handles.values():
        callbacks: dict[str, Callback] = infos.callbacks
        for cb in callbacks:
            if cb == callback_type:
                return callbacks[cb]
    print(f"[type] 未知的回调类型: '{callback_type}'")
    print_stack_and_exit()


def _is_base_handle_type(handle_type: str) -> bool:
    return handle_type in ["EOS", "EOS_HAntiCheatCommon"]


def get_base_class(handle_type: str) -> str:
    if handle_type.startswith("EOS_HAntiCheat") and handle_type != "EOS_HAntiCheatCommon":
        return convert_handle_class_name("EOS_HAntiCheatCommon")
    elif "EOS" == handle_type or "EOS_HAntiCheatCommon" == handle_type or handle_type.removeprefix("EOS_H") in interfaces:
        return "Object"
    else:
        return "RefCounted"


def _gen_disabled_macro(handle_type: str) -> str:
    if handle_type in ["EOS", "EOS_HPlatform"]:
        return ""
    return "EOS_" + handle_type.removeprefix("EOS_H").upper() + "_DISABLED"


def _get_callback_type_of_method(method_info: "Method") -> str:
    if len(method_info.args) > 0:
        arg: Arg = method_info.args[-1]
        decayed_type: str = decay_eos_type(arg.type)
        if is_callback_type(decayed_type):
            return decayed_type
    return ""


def print_stack_and_exit():
    import traceback

    for line in traceback.format_stack():
        print(line)
    exit(1)


def assert_condition(condition: bool, msg: str = ""):
    if condition:
        return
    import traceback

    for line in traceback.format_stack():
        print(line)
    if len(msg) > 0:
        print(f"[type] 断言失败: {msg}")
    else:
        print("[type] 断言失败")
    exit(1)

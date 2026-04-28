# 代码生成器全局上下文

from binding_generator.models import (
    Arg,
    Callback,
    Constant,
    Enum,
    FileInfo,
    Handle,
    Method,
    Struct,
)

struct2additional_method_requirements: dict[str, dict[str, bool]] = {}
expanded_as_args_structs: list[str] = []

interfaces: dict[str, Method] = {
    "Platform": Method(
        name="EOS_Platform_Create",
        return_type="EOS_HPlatform",
        args=[Arg(type="const EOS_Platform_Options*", name="Options")],
    )
}
structs: dict[str, Struct] = {}
handles: dict[str, Handle] = {
    "EOS": Handle(
        name="EOS",
        callbacks={
            "EOS_LogMessageFunc": Callback(
                name="EOS_LogMessageFunc",
                return_type="",
                args=[Arg(type="const EOS_LogMessage*", name="Message")],
            )
        },
    ),
    "EOS_HAntiCheatCommon": Handle(
        name="EOS_HAntiCheatCommon",
    ),
}

api_latest_macros: set[str] = set()
release_methods: dict[str, Method] = {}

unhandled_methods: dict[str, Method] = {}
unhandled_callbacks: dict[str, Callback] = {}
unhandled_enums: dict[str, Enum] = {}
unhandled_constants: dict[str, Constant] = {}
unhandled_infos: dict[str, FileInfo] = {}

generate_infos: dict[str, FileInfo] = {}

doc_keyword_map_method: dict[str, str] = {}
doc_keyword_map_enum_member: dict[str, str] = {}
doc_keyword_map_enum: dict[str, str] = {}
doc_keyword_map_constant: dict[str, str] = {}
doc_keyword_map_callback: dict[str, str] = {}
doc_keyword_map_struct: dict[str, str] = {}

callback_to_method: dict[str, str] = {}

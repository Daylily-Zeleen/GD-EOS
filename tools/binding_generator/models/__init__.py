from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Arg:
    type: str = ""
    name: str = ""
    deprecated: bool = False


@dataclass
class EnumMember:
    name: str = ""
    doc: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Method:
    name: str = ""
    return_type: str = ""
    args: list[Arg] = field(default_factory=list)
    doc: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Callback:
    name: str = ""
    return_type: str = ""
    args: list[Arg] = field(default_factory=list)
    doc: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Enum:
    name: str = ""
    members: list[EnumMember] = field(default_factory=list)
    doc: list[str] | str = field(default_factory=list)
    deprecated: bool = False


@dataclass
class StructField:
    type: str = ""
    doc: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Struct:
    name: str = ""
    fields: dict[str, StructField] = field(default_factory=dict)
    doc: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Constant:
    name: str = ""
    value: str = ""
    doc: list[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Handle:
    name: str = ""
    doc: list[str] = field(default_factory=list)
    methods: dict[str, Method] = field(default_factory=dict)
    callbacks: dict[str, Callback] = field(default_factory=dict)
    enums: dict[str, Enum] = field(default_factory=dict)
    constants: dict[str, Constant] = field(default_factory=dict)
    sub_handles: dict[str, str] = field(default_factory=dict)
    deprecated: bool = False


@dataclass
class FileInfo:
    file: str = ""
    enums: dict[str, Enum] = field(default_factory=dict)
    methods: dict[str, Method] = field(default_factory=dict)
    callbacks: dict[str, Callback] = field(default_factory=dict)
    structs: dict[str, Struct] = field(default_factory=dict)
    handles: dict[str, Handle] = field(default_factory=dict)
    constants: dict[str, Constant] = field(default_factory=dict)
    interface_doc: list[str] = field(default_factory=list)

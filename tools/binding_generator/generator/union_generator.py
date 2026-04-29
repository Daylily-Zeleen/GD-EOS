# Variant Union 转换函数代码生成器

from binding_generator.context import structs, variant_unions
from binding_generator.models import VariantUnionInfo
from binding_generator.utils.type import _resolve_enum_typedef, decay_eos_type, get_special_builtin_godot_type

# ─── 基础 C 类型 → Variant 映射规则 ────────────────────────────────────
# 每条规则: (variant_type, variant_to_eos_expr, eos_to_variant_expr)
#   variant_to_eos_expr: {field} = 联合体字段名
#   eos_to_variant_expr: {field} = 联合体字段名

_BASIC_C_TYPE_RULES: dict[str, tuple[str, str, str]] = {
    "int64_t": ("Variant::INT", "p_union.{field} = p_gd;", "return p_union.{field};"),
    "uint64_t": ("Variant::INT", "p_union.{field} = p_gd;", "return p_union.{field};"),
    "int32_t": ("Variant::INT", "p_union.{field} = p_gd;", "return p_union.{field};"),
    "uint32_t": ("Variant::INT", "p_union.{field} = p_gd;", "return p_union.{field};"),
    "double": ("Variant::FLOAT", "p_union.{field} = p_gd;", "return p_union.{field};"),
    "float": ("Variant::FLOAT", "p_union.{field} = p_gd;", "return p_union.{field};"),
    "EOS_Bool": ("Variant::BOOL", "p_union.{field} = p_gd;", "return p_union.{field} != EOS_FALSE;"),
    "const char*": (
        "Variant::STRING",
        "r_str_cache = String(p_gd).utf8(); p_union.{field} = r_str_cache.size() == 1 ? nullptr : r_str_cache.ptr();",
        "return String::utf8(p_union.{field});",
    ),
    # 特殊句柄类型 - 保持硬编码，因为它有独特的访问模式 (->)
    "EOS_AntiCheatCommon_ClientHandle": ("Variant::OBJECT", "p_union.{field} = Object::cast_to<Object>(p_gd);", "return Object::cast_to<Object>(p_union->{field});"),
}

_GODOT_TYPE_RULES: dict[str, tuple[str, str, str]] = {
    # 映射到 Godot 内置类型的特殊 EOS 内置类型的规则
    # 以 Godot 类型名称为键（通过 remap_type 发现），而非 EOS 类型名称
    # 这避免了在生成器中硬编码特定的 EOS 类型名称
    "Vector3": (
        "Variant::VECTOR3",
        "to_eos_type_out<Vector3, decltype(p_union.{field})>(Vector3(p_gd), p_union.{field});",
        "return Vector3{{ p_union.{field}.x, p_union.{field}.y, p_union.{field}.z }};",
    ),
    "Quaternion": (
        "Variant::QUATERNION",
        "to_eos_type_out<Quaternion, decltype(p_union.{field})>(Quaternion(p_gd), p_union.{field});",
        "return Quaternion{{ p_union.{field}.x, p_union.{field}.y, p_union.{field}.z, p_union.{field}.w }};",
    ),
}


def _infer_struct_rule(c_type: str) -> tuple[str, str, str] | None:
    # 根据结构体字段组成自动检测转换规则
    #
    # 检测策略:
    # 1. 如果结构体在 structs 字典中，分析其字段:
    #    - 3 个 float 字段 (x, y, z) → Vector3
    #    - 4 个 float 字段 (w, x, y, z) → Quaternion
    # 2. 如果类型是特殊内置类型（不在 structs 字典中），
    #    通过 get_special_builtin_godot_type() 和 _GODOT_TYPE_RULES 使用 Godot 类型映射
    decayed = decay_eos_type(c_type)

    # 策略 1: 从 structs 字典分析结构体字段
    if decayed in structs:
        fields = structs[decayed].fields
        field_names = list(fields.keys())
        field_types = [fields[f].type for f in field_names]

        if all(ft == "float" for ft in field_types):
            if len(field_names) == 3 and set(field_names) == {"x", "y", "z"}:
                to_eos = "to_eos_type_out<Vector3, decltype(p_union.{field})>(Vector3(p_gd), p_union.{field});"
                to_variant = "return Vector3{{ p_union.{field}.x, p_union.{field}.y, p_union.{field}.z }};"
                return ("Variant::VECTOR3", to_eos, to_variant)

            if len(field_names) == 4 and set(field_names) == {"w", "x", "y", "z"}:
                to_eos = "to_eos_type_out<Quaternion, decltype(p_union.{field})>(Quaternion(p_gd), p_union.{field});"
                to_variant = "return Quaternion{{ p_union.{field}.x, p_union.{field}.y, p_union.{field}.z, p_union.{field}.w }};"
                return ("Variant::QUATERNION", to_eos, to_variant)

    # 策略 2: 对特殊内置类型使用 Godot 类型映射
    gd_type = get_special_builtin_godot_type(decayed)
    if gd_type is not None and gd_type in _GODOT_TYPE_RULES:
        variant_type, to_eos, to_variant = _GODOT_TYPE_RULES[gd_type]
        return (variant_type, to_eos, to_variant)

    return None


def _find_rule(c_type: str) -> tuple[str, str, str] | None:
    # 查找 C 类型的转换规则
    rule = _BASIC_C_TYPE_RULES.get(c_type)
    if rule is not None:
        return rule
    return _infer_struct_rule(c_type)


# ─── C 类型优先级（用于优先选择）──────────────────────────────────
# 当多个 C 类型在 variant_to_eos_union 中映射到相同的 Variant 类型时，
# 选择优先级最高的那个，避免重复的 switch case 标签

_C_TYPE_PRIORITY: dict[str, int] = {
    "int64_t": 40,
    "uint64_t": 30,
    "int32_t": 20,
    "uint32_t": 10,
    "double": 20,
    "float": 10,
}


# ─── Variant 类型穿透情况 ─────────────────────────────────────────

_STRING_VARIANT_TYPES = ["Variant::STRING", "Variant::STRING_NAME", "Variant::NODE_PATH"]
_VECTOR3_VARIANT_TYPES = ["Variant::VECTOR3", "Variant::VECTOR3I"]


# ─── typedef 去重 ───────────────────────────────────────────────────


def _get_unique_enum_types() -> list[str]:
    # 获取去重后的枚举类型列表（共享相同基类的 typedef 类型会被分组）
    seen_resolved: set[str] = set()
    unique: list[str] = []
    for enum_type in variant_unions:
        resolved = _resolve_enum_typedef(enum_type)
        if resolved not in seen_resolved:
            seen_resolved.add(resolved)
            unique.append(enum_type)
    return unique


# ─── 生成 variant_to_eos_union ───────────────────────────────────────────


def _gen_variant_to_eos_switch(info: VariantUnionInfo) -> list[str]:
    # 为一个枚举类型生成 variant→eos 方向的 switch 分支
    #
    # 对于 variant_to_eos_union，每个 Variant 类型只生成一个 case
    # （C++ switch 不允许重复的 case 标签）
    lines: list[str] = []

    # 按 Variant 类型分组字段，保留 c_type 用于优先级选择
    # variant_type → [(enum_member, to_eos_expr, c_type)]
    variant_groups: dict[str, list[tuple[str, str, str]]] = {}

    for vf in info.fields:
        rule = _find_rule(vf.c_type)
        if rule is None:
            print(f"[union_generator] 警告: C 类型 '{vf.c_type}' 没有映射规则 (枚举成员: {vf.enum_member})")
            continue
        variant_type, to_eos_expr, _ = rule
        to_eos_line = to_eos_expr.format(field=vf.union_field_name)
        if variant_type not in variant_groups:
            variant_groups[variant_type] = []
        variant_groups[variant_type].append((vf.enum_member, to_eos_line, vf.c_type))

    for variant_type, members in variant_groups.items():
        # 选择优先的成员（C 类型优先级最高）
        selected_member = max(members, key=lambda m: _C_TYPE_PRIORITY.get(m[2], 0))
        enum_member, to_eos_line, _ = selected_member

        # 生成 case 标签
        if variant_type == "Variant::STRING":
            for svt in _STRING_VARIANT_TYPES:
                lines.append(f"        case {svt}:")
            lines.append("        {")
        elif variant_type == "Variant::VECTOR3":
            for svt in _VECTOR3_VARIANT_TYPES:
                lines.append(f"        case {svt}:")
            lines.append("        {")
        else:
            lines.append(f"        case {variant_type}: {{")

        lines.append(f"            r_union_type = {info.enum_type}::{enum_member};")
        lines.append(f"            {to_eos_line}")
        lines.append("        } break;")

    lines.append("        default: {")
    lines.append('            ERR_PRINT(vformat("Unsupport variant", Variant::get_type_name(p_gd.get_type())));')
    lines.append("        } break;")

    return lines


# ─── 生成 eos_union_to_variant ───────────────────────────────────────────


def _gen_eos_to_variant_switch(info: VariantUnionInfo) -> list[str]:
    # 为一个枚举类型生成 eos→variant 方向的 switch 分支
    lines: list[str] = []

    for vf in info.fields:
        rule = _find_rule(vf.c_type)
        if rule is None:
            continue
        _, _, to_variant_expr = rule
        to_variant_line = to_variant_expr.format(field=vf.union_field_name)

        lines.append(f"        case {info.enum_type}::{vf.enum_member}: {{")
        lines.append(f"            {to_variant_line}")
        lines.append("        } break;")

    lines.append("        default: {")
    lines.append(f'            ERR_FAIL_V_MSG({{}}, vformat("Unsupported {info.enum_type}: ", (int)p_union_type));')
    lines.append("        } break;")

    return lines


# ─── 主生成入口点 ─────────────────────────────────────────────


def gen_variant_union_conversions() -> str:
    # 生成 variant union 转换函数的 .inl 文件内容
    lines: list[str] = []
    lines.append("// 自动生成的 variant union 转换 - 请勿手动编辑")
    lines.append("// 由 tools/binding_generator/generator/union_generator.py 生成")
    lines.append("")

    if len(variant_unions) == 0:
        lines.append("// 未找到 variant union 类型")
        lines.append("")
        return "\n".join(lines)

    unique_enum_types = _get_unique_enum_types()

    # 生成 variant_to_eos_union
    _build_variant_to_eos_union(lines, unique_enum_types)
    lines.append("")

    # 生成 eos_union_to_variant
    _build_eos_to_variant(lines, unique_enum_types)
    lines.append("")

    return "\n".join(lines)


def _build_variant_to_eos_union(lines: list[str], unique_enum_types: list[str]):
    # 生成 variant_to_eos_union 函数
    all_enum_types = list(variant_unions.keys())
    enum_type_list = [f"std::is_same_v<std::decay_t<UnionType>, {et}>" for et in all_enum_types]
    sfinae_cond = " || ".join(enum_type_list)

    lines.append(f"template <typename EOSUnion, typename UnionType, std::enable_if_t<{sfinae_cond}> *_dummy = nullptr>")
    lines.append("inline void variant_to_eos_union(const Variant &p_gd, EOSUnion &p_union, UnionType &r_union_type, CharString &r_str_cache) {")

    first = True
    for enum_type in unique_enum_types:
        info = variant_unions[enum_type]

        if_condition = "if constexpr" if first else "} else if constexpr"
        first = False

        switch_lines = _gen_variant_to_eos_switch(info)

        lines.append(f"    {if_condition} (std::is_same_v<std::decay_t<UnionType>, {enum_type}>) {{")
        lines.append("        switch (p_gd.get_type()) {")
        lines += switch_lines
        lines.append("        }")

    lines.append("    }")
    lines.append("}")


def _build_eos_to_variant(lines: list[str], unique_enum_types: list[str]):
    # 生成 eos_union_to_variant 函数
    all_enum_types = list(variant_unions.keys())
    enum_type_list = [f"std::is_same_v<std::decay_t<UnionType>, {et}>" for et in all_enum_types]
    sfinae_cond = " || ".join(enum_type_list)

    lines.append(f"template <typename EOSUnion, typename UnionType, std::enable_if_t<{sfinae_cond}> *_dummy = nullptr>")
    lines.append("inline Variant eos_union_to_variant(const EOSUnion &p_union, UnionType p_union_type) {")

    first = True
    for enum_type in unique_enum_types:
        info = variant_unions[enum_type]

        if_condition = "if constexpr" if first else "} else if constexpr"
        first = False

        switch_lines = _gen_eos_to_variant_switch(info)

        lines.append(f"    {if_condition} (std::is_same_v<std::decay_t<UnionType>, {enum_type}>) {{")
        lines.append("        switch (p_union_type) {")
        lines += switch_lines
        lines.append("        }")

    lines.append("    }")
    lines.append("}")

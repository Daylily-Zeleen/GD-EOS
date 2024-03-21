#pragma once

#include <godot_cpp/classes/object.hpp>
#include <godot_cpp/core/binder_common.hpp>

#define _BIND_ENUM_CONSTANT(enume_type_name, e, e_bind) \
    ClassDB::bind_integer_constant(get_class_static(), godot::_gde_constant_get_enum_name<enume_type_name>(enume_type_name::e, e_bind), e_bind, enume_type_name::e)

#include "gen/eos_enums.gen.inl"
namespace godot {

#define SNAME(sn) []() -> const StringName & {static const StringName ret{sn};return ret; }()

class EOSConstants : public Object {
    GDCLASS(EOSConstants, Object)

protected:
    static void _bind_methods();

public:
    _USING_ENUMS_CONSTANTS()

    static String get_result_string(EOS_EResult p_eresult);
};

} //namespace godot

_CAST_ENUMS_CONSTANTS()

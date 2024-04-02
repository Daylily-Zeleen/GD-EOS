#pragma once

#include "utils.h"

#include <godot_cpp/classes/ref_counted.hpp>

#ifdef DEBUG_ENABLED
#include "godot_cpp/templates/hash_map.hpp"
#include "godot_cpp/templates/local_vector.hpp"
#endif // DEBUG_ENABLED

namespace godot::eos {

class EOSDataClassOptions : public RefCounted {
    GDCLASS(EOSDataClassOptions, RefCounted)

    bool sort_keys = true;
    bool include_null_in_dict = true;
    bool include_null_in_print = true;
    bool print_newline = true;
    PackedStringArray print_exclude;

public:
    _DECLARE_SETGET_BOOL(sort_keys)
    _DECLARE_SETGET_BOOL(include_null_in_dict)
    _DECLARE_SETGET_BOOL(include_null_in_print)
    _DECLARE_SETGET_BOOL(print_newline)
    _DECLARE_SETGET(print_exclude)

protected:
    static void _bind_methods() {
        _BIND_BEGIN(EOSDataClassOptions)
        _BIND_PROP_BOOL(sort_keys);
        _BIND_PROP_BOOL(include_null_in_dict);
        _BIND_PROP_BOOL(include_null_in_print);
        _BIND_PROP_BOOL(print_newline);
        _BIND_PROP(print_exclude);
        _BIND_END()
    }
};

class EOSDataClass : public RefCounted {
    GDCLASS(EOSDataClass, RefCounted)

    Ref<EOSDataClassOptions> print_options;

    static Ref<EOSDataClassOptions> get_defailt_options() {
        static Ref<EOSDataClassOptions> ret = memnew(EOSDataClassOptions);
        return ret;
    }

    static bool is_valid_prop(const Dictionary &p_prop) {
        return ((int64_t)(p_prop["usage"]) & PROPERTY_USAGE_STORAGE) != 0 &&
                ((String)(p_prop["name"])) != "print_options" && p_prop["name"] != "script";
    }

    bool is_not_exclude_prop(const StringName &p_name, const Ref<EOSDataClassOptions> &p_print_options) const {
        return !p_print_options->get_print_exclude().has(p_name);
    }

    static String stringify(const Variant &p_val, bool p_new_line = false, int p_indent = 0);

protected:
    static void _bind_methods();

    Ref<EOSDataClassOptions> _get_print_options() const {
        if (print_options.is_valid()) {
            return print_options;
        }
        return get_defailt_options();
    }

    TypedArray<StringName> get_props(bool p_sort) const;

public:
    String _to_string() const;

public:
    Dictionary to_dict() const;

    _DECLARE_SETGET_TYPED(print_options, Ref<EOSDataClassOptions>)
};

}; //namespace godot::eos

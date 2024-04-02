#include <core/eos_data_class.h>

namespace godot::eos {

_DEFINE_SETGET_BOOL(EOSDataClassOptions, sort_keys)
_DEFINE_SETGET_BOOL(EOSDataClassOptions, include_null_in_dict)
_DEFINE_SETGET_BOOL(EOSDataClassOptions, include_null_in_print)
_DEFINE_SETGET_BOOL(EOSDataClassOptions, print_newline)
_DEFINE_SETGET(EOSDataClassOptions, print_exclude)

// ==== EOSDataClass ====
_DEFINE_SETGET_TYPED(EOSDataClass, print_options, Ref<EOSDataClassOptions>);

void EOSDataClass::_bind_methods() {
    ClassDB::bind_method(D_METHOD("to_dict"), &EOSDataClass::to_dict);

    ClassDB::bind_method(D_METHOD("get_print_options"), &EOSDataClass::get_print_options);
    ClassDB::bind_method(D_METHOD("set_print_options", "print_options"), &EOSDataClass::set_print_options);
    ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "print_options", PROPERTY_HINT_NONE, "", PROPERTY_USAGE_NONE, EOSDataClassOptions::get_class_static()), "set_print_options", "get_print_options");
}

TypedArray<StringName> EOSDataClass::get_props(bool p_sort) const {
    TypedArray<StringName> ret;

    auto props = get_property_list().filter(callable_mp_static(is_valid_prop));

    for (int i = 0; i < props.size(); ++i) {
        ret.append(props[i].operator Dictionary()["name"]);
    }

    if (p_sort) {
        ret.sort();
    }

    return ret;
}

String EOSDataClass::stringify(const Variant &p_val, bool p_new_line, int p_indent) {
    String ret;

    String tab = "";
    String new_line = "";
    String join_str = ", ";

    if (p_new_line) {
        tab = "\t";
        new_line = "\n";
        join_str = ",\n";
    }

    if (auto dc = Object::cast_to<EOSDataClass>(p_val)) {
        ret = dc->_to_string();
    } else {
        if (p_val.get_type() == Variant::DICTIONARY) {
            Dictionary dict = p_val.operator Dictionary();

            auto keys = dict.keys();
            auto values = dict.values();

            PackedStringArray pairs;

            for (auto i = 0; i < keys.size(); ++i) {
                auto key = keys[i];
                auto val = values[i];
                pairs.push_back(vformat(tab + "%s: %s", stringify(key, p_new_line, p_indent + 1), stringify(val, p_new_line, p_indent + 1)));
            }

            ret = "{" + new_line;
            ret += join_str.join(pairs);
            ret += "}" + new_line;
        } else if (p_val.get_type() == Variant::ARRAY) {
            Array arr = p_val;

            PackedStringArray vals;
            for (auto i = 0; i < arr.size(); ++i) {
                vals.push_back(tab + stringify(arr[i], p_new_line, p_indent + 1));
            }

            ret = "[" + new_line;
            ret += join_str.join(vals);
            ret += "]" + new_line;
        } else {
            ret = p_val.stringify();
        }
    }

    if (p_new_line) {
        ret.indent(tab.repeat(p_indent));
    }
    return ret;
}

String EOSDataClass::_to_string() const {
    auto options = _get_print_options();
    auto prop_names = get_props(options->is_sort_keys()).filter(callable_mp(this, &EOSDataClass::is_not_exclude_prop).bind(options));

    PackedStringArray props;
    for (int i = 0; i < prop_names.size(); ++i) {
        auto val = get(prop_names[i]);
        if (val.get_type() != Variant::NIL || options->is_include_null_in_print()) {
            props.append(vformat(options->is_print_newline() ? "\n\t%s = %s" : "%s = %s", prop_names[i], stringify(val, options->is_print_newline())));
        }
    }

    String line_end = "";
    String new_line = "";
    String new_line_end = "";
    String join_str = ", ";

    if (options->is_print_newline()) {
        line_end = "\n";
        new_line = "\n\t";
        new_line_end = ",\n";
        join_str = ",";
    }

    return vformat("%s (%s%s)", get_class(), join_str.join(props), new_line_end);
}

Dictionary EOSDataClass::to_dict() const {
    auto options = _get_print_options();
    auto prop_names = get_props(options->is_sort_keys());

    Dictionary ret;
    for (int i = 0; i < prop_names.size(); ++i) {
        String prop_name = prop_names[i];
        auto val = get(prop_name);
        if (val.get_type() != Variant::NIL || options->is_include_null_in_dict()) {
            ret[prop_name] = val;
        }
    }

    return ret;
}

} //namespace godot::eos
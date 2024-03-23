#pragma once

#include "utils.h"

#include <godot_cpp/classes/ref_counted.hpp>

#include <gen/forward_declare.gen.h>
#include <gen/eos_enums.gen.inl>
#include <eos_logging.h>

#include "eos_packed_result.h"

// TODO:: tmp
#include "../eos_anticheatcommon_client.h"

#ifdef DEBUG_ENABLED
#include "godot_cpp/templates/hash_map.hpp"
#include "godot_cpp/templates/local_vector.hpp"
#endif // DEBUG_ENABLED

namespace godot {

class EOSDataClassOptions : public RefCounted {
    GDCLASS(EOSDataClassOptions, RefCounted)

    bool sort_keys = true;
    bool include_null_in_dict = true;
    bool include_null_in_print = true;
    bool print_newline = true;
    PackedStringArray print_exclude;

public:
    _DEFINE_SETGET_BOOL(sort_keys)
    _DEFINE_SETGET_BOOL(include_null_in_dict)
    _DEFINE_SETGET_BOOL(include_null_in_print)
    _DEFINE_SETGET_BOOL(print_newline)
    _DEFINE_SETGET(print_exclude)

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
                ((String)(p_prop["name"])) != "print_options";
    }

    bool is_not_exclude_prop(const StringName &p_name, const Ref<EOSDataClassOptions> &p_print_options) const {
        return !p_print_options->get_print_exclude().has(p_name);
    }

    static String stringify(const Variant &p_val, bool p_new_line = false, int p_indent = 0) {
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

protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("to_dict"), &EOSDataClass::to_dict);

        ClassDB::bind_method(D_METHOD("get_print_options"), &EOSDataClass::get_print_options);
        ClassDB::bind_method(D_METHOD("set_print_options", "print_options"), &EOSDataClass::set_print_options);
        ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "print_options", PROPERTY_HINT_NONE, "", PROPERTY_USAGE_NONE, EOSDataClassOptions::get_class_static()), "set_print_options", "get_print_options");
    }

    class SetGetProxy {
        EOSDataClass *m_data;
        const StringName &m_name;

        SetGetProxy(const SetGetProxy &) = delete;
        SetGetProxy &operator=(const SetGetProxy &) = delete;
        SetGetProxy(SetGetProxy &&) = delete;
        SetGetProxy &operator=(SetGetProxy &&) = delete;

    public:
        SetGetProxy(EOSDataClass *p_data, const StringName &p_name) :
                m_data(p_data), m_name(p_name) {}

        SetGetProxy &operator=(const Variant &p_val) {
            m_data->set(m_name, p_val);
            return *this;
        }

        operator Variant() { return m_data->get(m_name); }

        template <typename T>
        operator T() { return operator Variant(); }
    };

    Ref<EOSDataClassOptions> _get_print_options() const {
        if (print_options.is_valid()) {
            return print_options;
        }
        return get_defailt_options();
    }

    TypedArray<StringName> get_props(bool p_sort) const {
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

    bool _set(const StringName &p_name, const Variant &p_property) {
        if (!Variant(this).has_key(p_name)) {
#ifdef DEBUG_ENABLED
            static HashMap<StringName, LocalVector<StringName>> printed;
            StringName klass = get_class();
            if (!printed.has(klass)) {
                printed.insert(klass, {});
            }
            if (printed[klass].find(p_name) < 0) {
                WARN_PRINT(vformat("\"%s\" has not field \"%s\", set to meta.", klass, p_name));
                printed[klass].push_back(p_name);
            }
#endif // DEBUG_ENABLED

            set_meta(p_name, p_property);
            return true;
        }
        return false;
    }

    bool _get(const StringName &p_name, Variant &r_property) const {
        if (has_meta(p_name)) {
            r_property = get_meta(p_name);
            return true;
        }
        return false;
    }

    void _get_property_list(List<PropertyInfo> *p_list) const {
        auto metas = get_meta_list();
        for (decltype(metas.size()) i = 0; i < metas.size(); ++i) {
            StringName meta_name = metas[i];
            Variant val = get_meta(meta_name);
            p_list->push_back(PropertyInfo(val.get_type(), meta_name));
        }
    }

public:
    Variant try_get_client_data() const {
        static const StringName client_data{ "client_data" };
        if (Variant(this).has_key(client_data)) {
            return get(client_data);
        }
        return get_meta(client_data, {});
    }

    Variant operator[](const StringName &p_key) const {
        return this->get(p_key);
    }

    SetGetProxy operator[](const StringName &p_key) { return { this, p_key }; }

    String _to_string() const {
        auto options = _get_print_options();
        auto prop_names = get_props(options->is_sort_keys()).filter(callable_mp(this, &EOSDataClass::is_not_exclude_prop).bind(options));

        PackedStringArray props;
        for (int i = 0; i < prop_names.size(); ++i) {
            auto val = get(prop_names[i]);
            if (val.get_type() != Variant::NIL || options->is_include_null_in_print()) {
                props.append(vformat("%s = %s", prop_names[i], stringify(val, options->is_print_newline())));
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
            join_str = ",\n";
        }

        return vformat("%s (%s%s,%s)", get_class_static(), new_line, join_str.join(props), new_line_end);
    }

public:
    Dictionary to_dict() const {
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

    Ref<EOSDataClassOptions> get_print_options() const { return print_options; }
    void set_print_options(const Ref<EOSDataClassOptions> p_options) { print_options = p_options; }
};

}; //namespace godot

template <typename T>
struct _EOSStructToWrapper {};
template <const char *signal_name>
struct _MakeDataClassPropInfo {};

#define _DECAY(T) std::remove_reference_t<std::remove_const_t<std::remove_pointer_t<std::decay_t<T>>>>

#define INSTANTIATE_DATA_CLASS(eos_data, indentifier)                        \
    _EOSStructToWrapper<_DECAY(decltype(eos_data))>::type ref_##indentifier; \
    ref_##indentifier.instantiate();                                         \
    auto indentifier = *(ref_##indentifier.ptr())

#define MAKE_DATA_CLASS_PROP_INFO_BY_SIGNAL_NAME(signal_name) _MakeDataClassPropInfo<signal_name>::make()

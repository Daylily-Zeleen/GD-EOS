#include <core/eos_data_class.h>

namespace godot::eos {

void EOSDataClass::_bind_methods() {
    ClassDB::bind_method(D_METHOD("to_dict"), &EOSDataClass::to_dict);
}

LocalVector<StringName> EOSDataClass::get_props() const {
    auto props = get_property_list().filter(callable_mp_static(is_valid_prop));

    LocalVector<StringName> ret;
    ret.reserve(props.size());
    for (int i = 0; i < props.size(); ++i) {
        ret.push_back(props[i].operator Dictionary()["name"]);
    }

    return ret;
}

String EOSDataClass::_to_string() const {
    return vformat("<%s#%d>", get_class_static(), get_instance_id());
}

Dictionary EOSDataClass::to_dict() const {
    auto prop_names = get_props();

    Dictionary ret;
    for (int i = 0; i < prop_names.size(); ++i) {
        String prop_name = prop_names[i];
        auto val = get(prop_name);
        if (auto dc = cast_to<EOSDataClass>(val)) {
            val = dc->to_dict();
        } else if (val.get_type() == Variant::DICTIONARY) {
            Dictionary dict = val.operator Dictionary();
            Dictionary new_dict;

            auto keys = dict.keys();
            auto values = dict.values();

            for (auto i = 0; i < keys.size(); ++i) {
                auto key = keys[i];
                auto val = values[i];

                if (auto dc = cast_to<EOSDataClass>(key)) {
                    key = dc->to_dict();
                }
                if (auto dc = cast_to<EOSDataClass>(val)) {
                    val = dc->to_dict();
                }

                new_dict[key] = val;
            }

            val = new_dict;
        } else if (val.get_type() == Variant::ARRAY) {
            Array arr = val;
            Array new_arr;
            for (auto i = 0; i < arr.size(); ++i) {
                Variant v = arr[i];
                if (auto dc = cast_to<EOSDataClass>(v)) {
                    new_arr.push_back(dc->to_dict());
                } else {
                    new_arr.push_back(v);
                }
            }

            val = new_arr;
        }

        ret[prop_name] = val;
    }

    return ret;
}

} //namespace godot::eos
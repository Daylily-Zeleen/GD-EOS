#pragma once

#include "utils.h"

#include <godot_cpp/classes/ref_counted.hpp>

#ifdef DEBUG_ENABLED
#include "godot_cpp/templates/local_vector.hpp"
#endif // DEBUG_ENABLED

namespace godot::eos {

class EOSDataClass : public RefCounted {
    GDCLASS(EOSDataClass, RefCounted)

    static bool is_valid_prop(const Dictionary &p_prop) {
        return ((int64_t)(p_prop["usage"]) & PROPERTY_USAGE_STORAGE) != 0 &&
                ((String)(p_prop["name"])) != "print_options" && p_prop["name"] != "script";
    }

protected:
    static void _bind_methods();

    LocalVector<StringName> get_props() const;

public:
    String _to_string() const;

public:
    Dictionary to_dict() const;
};

}; //namespace godot::eos

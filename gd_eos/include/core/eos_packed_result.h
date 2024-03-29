#pragma once

#include <godot_cpp/classes/ref_counted.hpp>

namespace godot::eos {
class EOSPackedResult : public RefCounted {
    GDCLASS(EOSPackedResult, RefCounted)
protected:
    static void _bind_methods() {}
};
} //namespace godot::eos

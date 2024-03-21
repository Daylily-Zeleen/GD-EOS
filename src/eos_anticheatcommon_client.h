#pragma once
#include "eos_anticheatcommon_types.h"
#include "godot_cpp/classes/ref_counted.hpp"

namespace godot {

class EOSAntiCheatCommon_Client : public Object {
    GDCLASS(EOSAntiCheatCommon_Client, Object)
protected:
    static void _bind_methods(){};
};

} // namespace godot

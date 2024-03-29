#pragma once

#include "godot_cpp/classes/object.hpp"

namespace godot::eos {

class EOSAntiCheatCommon_Client : public Object {
    GDCLASS(EOSAntiCheatCommon_Client, Object)
protected:
    static void _bind_methods(){};
};

} //namespace godot::eos

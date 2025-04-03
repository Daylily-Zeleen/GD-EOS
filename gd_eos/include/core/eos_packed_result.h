#pragma once

#include "eos_data_class.h"

namespace godot::eos {
class EOSPackedResult : public EOSDataClass {
    GDCLASS(EOSPackedResult, EOSDataClass)
protected:
    static void _bind_methods() {}
};
} //namespace godot::eos

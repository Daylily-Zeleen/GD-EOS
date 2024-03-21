#include "eos_constants.h"

#include <godot_cpp/core/class_db.hpp>

namespace godot {

void EOSConstants::_bind_methods() {
    ClassDB::bind_static_method(get_class_static(), D_METHOD("get_result_string", "eresult"), EOSConstants::get_result_string);

    _BIND_ENUMS_CONSTANTS()
}

String EOSConstants::get_result_string(EOS_EResult p_eresult) {
    return EOS_EResult_ToString((EOS_EResult)p_eresult);
}

} //namespace godot
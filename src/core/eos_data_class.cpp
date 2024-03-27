#include "eos_data_class.h"

namespace godot {

_DEFINE_SETGET_BOOL(EOSDataClassOptions, sort_keys)
_DEFINE_SETGET_BOOL(EOSDataClassOptions, include_null_in_dict)
_DEFINE_SETGET_BOOL(EOSDataClassOptions, include_null_in_print)
_DEFINE_SETGET_BOOL(EOSDataClassOptions, print_newline)
_DEFINE_SETGET(EOSDataClassOptions, print_exclude)
} //namespace godot
#include <gdextension_interface.h>

#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

#include "../../gd_eos_defs.h"

#include <godot_cpp/classes/project_settings.hpp>

using namespace godot;

namespace {
void _initialize_gdeos_editor_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_EDITOR) {
        ProjectSettings *ps = ProjectSettings::get_singleton();
        ps->set_setting(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_INTERNAL_DIRECTORY, "user://");
        ps->set_setting(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_EXTERNAL_DIRECTORY, "");

        ps->set_initial_value(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_INTERNAL_DIRECTORY, "user://");
        ps->set_initial_value(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_EXTERNAL_DIRECTORY, "");
        return;
    }
}

void _uninitialize_gdeos_editor_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_EDITOR) {
        return;
    }
}
} // namespace

extern "C" {
GDExtensionBool GDE_EXPORT gdeos_editor_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
    GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(_initialize_gdeos_editor_module);
    init_obj.register_terminator(_uninitialize_gdeos_editor_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_EDITOR);

    return init_obj.init();
}
}

#if defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)
#include <editor/eos_editor_plugin.h>

namespace godot::eos::editor {
void EOSExportPlugin::_bind_methods() {}

String EOSExportPlugin::_get_name() const {
    return "GD-EOS";
}

void EOSExportPlugin::_export_begin(const PackedStringArray &features, bool is_debug, const String &path, uint32_t flags) {
    const String binary_base_dir = "res://addons/gd-eos/bin/";

    if (features.has("windows")) {
        bool bit32 = false;
        for (const String &feature : features) {
            if (feature == "x86_32") {
                bit32 = true;
                break;
            }
        }

        if (bit32) {
            add_shared_object(binary_base_dir.path_join("windows").path_join("EOSSDK-Win32-Shipping.dll"), {}, "/");
            add_shared_object(binary_base_dir.path_join("windows").path_join("x86").path_join("xaudio2_9redist.dll"), {}, "/");
        } else {
            add_shared_object(binary_base_dir.path_join("windows").path_join("EOSSDK-Win64-Shipping.dll"), {}, "/");
            add_shared_object(binary_base_dir.path_join("windows").path_join("x64").path_join("xaudio2_9redist.dll"), {}, "/");
        }
    } else if (features.has("linux")) {
        add_shared_object(binary_base_dir.path_join("linux").path_join("libEOSSDK-Linux-Shipping.so"), {}, "/");
    } else if (features.has("macos")) {
        add_shared_object(binary_base_dir.path_join("macos").path_join("libEOSSDK-Mac-Shipping.dylib"), {}, "/");
    } else if (features.has("android")) {
        String arch;
        for (const String &feature : features) {
            if (feature == "arm32") {
                ERR_CONTINUE_MSG(!arch.is_empty(), "Exporting features have multiple architechture tags!");
                arch = feature;
            } else if (feature == "arm64") {
                ERR_CONTINUE_MSG(!arch.is_empty(), "Exporting features have multiple architechture tags!");
                arch = feature;
            } else if (feature == "x86_32") {
                ERR_CONTINUE_MSG(!arch.is_empty(), "Exporting features have multiple architechture tags!");
                arch = feature;
            } else if (feature == "x86_64") {
                ERR_CONTINUE_MSG(!arch.is_empty(), "Exporting features have multiple architechture tags!");
                arch = feature;
            }
        }
        ERR_FAIL_COND_MSG(arch.is_empty(), "EOS Exporting: Unknown architechture, can't add shared object.");
        add_shared_object(binary_base_dir.path_join("android").path_join(arch).path_join("libEOSSDK.so"), Array::make(arch), "/");
    }
}

// ================

void EOSEditorPlugin::_bind_methods() {}

void EOSEditorPlugin::_notification(int p_what) {
    switch (p_what) {
        case NOTIFICATION_ENTER_TREE: {
            export_plugin.instantiate();
            add_export_plugin(export_plugin);
        } break;
        case NOTIFICATION_EXIT_TREE: {
            remove_export_plugin(export_plugin);
            export_plugin.unref();
        } break;
        default:
            break;
    }
}
} //namespace godot::eos::editor

#endif //defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

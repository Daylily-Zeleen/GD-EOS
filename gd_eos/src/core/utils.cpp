#include <core/utils.h>

#include <godot_cpp/classes/os.hpp>
#include <godot_cpp/classes/project_settings.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#if defined(_WIN32) || defined(_WIN64)
#include <Windows/eos_Windows.h>
#elif defined(__ANDROID__)
#include <Android/eos_android.h>
#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/os.hpp>
#endif

namespace godot::eos::internal {

// String epic_account_id_to_string(const EOS_EpicAccountId accountId) {
//     if (accountId == nullptr) {
//         return String("");
//     }

//     char *tempBuffer = (char *)memalloc(EOS_EPICACCOUNTID_MAX_LENGTH + 1);
//     int32_t tempBufferSize = EOS_EPICACCOUNTID_MAX_LENGTH + 1;
//     EOS_EResult conver_result = EOS_EpicAccountId_ToString(accountId, tempBuffer, &tempBufferSize);

//     ERR_FAIL_COND_V_MSG(conver_result != EOS_EResult::EOS_Success, {}, vformat("Fail result code: %d - %s", conver_result, EOS_EResult_ToString(conver_result)));
//     return String(tempBuffer);
// }

// String product_user_id_to_string(const EOS_ProductUserId localUserId) {
//     if (localUserId == nullptr) {
//         return String("");
//     }

//     char *tempBuffer = (char *)memalloc(EOS_PRODUCTUSERID_MAX_LENGTH + 1);
//     int32_t tempBufferSize = EOS_PRODUCTUSERID_MAX_LENGTH + 1;
//     EOS_EResult conver_result = EOS_ProductUserId_ToString(localUserId, tempBuffer, &tempBufferSize);

//     ERR_FAIL_COND_V_MSG(conver_result != EOS_EResult::EOS_Success, {}, vformat("Fail result code: %d - %s", conver_result, EOS_EResult_ToString(conver_result)));
//     return String(tempBuffer);
// }

} //namespace godot::eos::internal

namespace godot::eos {

#ifdef DEBUG_ENABLED
String eos_product_user_id_to_string(EOS_ProductUserId p_product_user_id) {
    char buffer[EOS_PRODUCTUSERID_MAX_LENGTH + 1];
    int32_t inoutlength{ EOS_PRODUCTUSERID_MAX_LENGTH + 1 };
    EOS_ProductUserId_ToString(p_product_user_id, buffer, &inoutlength);
    return buffer;
}
String eos_epic_account_id_to_string(EOS_EpicAccountId p_epic_account_id) {
    char buffer[EOS_EPICACCOUNTID_MAX_LENGTH + 1];
    int32_t inoutlength{ EOS_EPICACCOUNTID_MAX_LENGTH + 1 };
    EOS_EpicAccountId_ToString(p_epic_account_id, buffer, &inoutlength);
    return buffer;
}
#endif // DEBUG_ENABLED

#define EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_INTERNAL_DIRECTORY "GD_EOS/platforms/android/optional_internal_directory"
#define EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_EXTERNAL_DIRECTORY "GD_EOS/platforms/android/optional_external_directory"

#if defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)
void setup_eos_project_settings() {
    ProjectSettings *ps = ProjectSettings::get_singleton();
    ps->set_setting(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_INTERNAL_DIRECTORY, "");
    ps->set_setting(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_EXTERNAL_DIRECTORY, "user://");

    ps->set_initial_value(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_INTERNAL_DIRECTORY, "");
    ps->set_initial_value(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_EXTERNAL_DIRECTORY, "user://");
}
#endif // defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

void *get_platform_specific_options() {
#if defined(_WIN32) || defined(_WIN64)
    static EOS_Windows_RTCOptions windowsRTCOptions;
    memset(&windowsRTCOptions, 0, sizeof(windowsRTCOptions));
    windowsRTCOptions.ApiVersion = EOS_WINDOWS_RTCOPTIONS_API_LATEST;
    if (OS::get_singleton()->has_feature("editor")) {
        String bin_path = "res://addons/gd_eos/bin/";
#if defined(_WIN32)
        CharString xAudio29DllPath = ProjectSettings::get_singleton()->globalize_path(bin_path.path_join("x86").path_join("xaudio2_9redist.dll")).utf8();
#else // defined(_WIN64)
        CharString xAudio29DllPath = ProjectSettings::get_singleton()->globalize_path(bin_path.path_join("x64").path_join("xaudio2_9redist.dll")).utf8();
#endif
        windowsRTCOptions.XAudio29DllPath = xAudio29DllPath.get_data();
    } else {
        windowsRTCOptions.XAudio29DllPath = VARIANT_TO_CHARSTRING(OS::get_singleton()->get_executable_path().get_base_dir().path_join("xaudio2_9redist.dll"));
    }
    return &windowsRTCOptions;
#elif defined(__ANDROID__)
    static EOS_Android_InitializeOptions androidInitializeOptions;
    memset(&androidInitializeOptions, 0, sizeof(androidInitializeOptions));
    String internal_dir{};
    String external_dir{};
    Variant internal_var = ProjectSettings::get_singleton()->get_setting_with_override(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_INTERNAL_DIRECTORY);
    Variant external_var = ProjectSettings::get_singleton()->get_setting_with_override(EOS_PLATFORM_SPECIFIC_SETTING_ANDROID_EXTERNAL_DIRECTORY);
    if (internal_var.get_type() == Variant::STRING) {
        String path = internal_var;
        if (!path.is_empty()) {
            path = ProjectSettings::get_singleton()->globalize_path(path);
            if (!DirAccess::dir_exists_absolute(path)) {
                DirAccess::make_dir_absolute(path);
            }

            if (DirAccess::dir_exists_absolute(path)) {
                internal_dir = path;
            } else {
                ERR_PRINT(vformat("EOS warning: \"%s\" is not a valid directory.", internal_var));
            }
        }
    } else {
        ERR_PRINT(vformat("EOS warning: \"%s\" is not a valid directory.", internal_var));
    }

    if (external_var.get_type() == Variant::STRING && !String(external_var).is_empty()) {
        String path = internal_var;
        if (!path.is_empty()) {
            path = ProjectSettings::get_singleton()->globalize_path(path);
            if (!DirAccess::dir_exists_absolute(path)) {
                DirAccess::make_dir_absolute(path);
            }

            if (DirAccess::dir_exists_absolute(path)) {
                external_dir = path;
            } else {
                ERR_PRINT(vformat("EOS warning: \"%s\" is not a valid directory.", external_var));
            }
        }
    } else {
        ERR_PRINT(vformat("EOS warning: \"%s\" is not a valid directory.", external_var));
    }

    if (internal_dir.is_empty()) {
        internal_dir = OS::get_singleton()->get_executable_path().get_base_dir();
    }
    if (external_dir.is_empty()) {
        external_dir = ProjectSettings::get_singleton()->globalize_path(OS::get_singleton()->get_user_data_dir());
    }

    androidInitializeOptions.ApiVersion = EOS_ANDROID_INITIALIZEOPTIONS_API_LATEST;
    androidInitializeOptions.OptionalInternalDirectory = VARIANT_TO_CHARSTRING(internal_dir);
    androidInitializeOptions.OptionalExternalDirectory = VARIANT_TO_CHARSTRING(external_dir);
    return &androidInitializeOptions;
#else
    return nullptr;
#endif
}
} //namespace godot::eos
#include "eos_common.hpp"

#include <eos_version.h>

#include <godot_cpp/core/class_db.hpp>
#ifdef LOGGING_ENABLED
#include <godot_cpp/variant/utility_functions.hpp>
#endif // LOGGING_ENABLED

namespace godot {

#ifdef LOGGING_ENABLED
EOSLogging *EOSLogging::singleton{};
void EOSLogging::_bind_methods() {
    _BIND_BEGIN(EOSLogging);
    _BIND_PROP_BOOL(log_print);
    ClassDB::bind_method(D_METHOD("set_log_level", "Log_category", "log_level"), &EOSLogging::set_log_level);

    ADD_SIGNAL(MethodInfo("logging_callback",
            PropertyInfo(Variant::STRING, "category"),
            PropertyInfo(Variant::STRING, "message"),
            PropertyInfo(Variant::INT, "level", {}, "", {}, "EOS_ELogLevel")));

    _BIND_END();
}

EOSLogging::EOSLogging() {
    ERR_FAIL_COND(singleton != nullptr);
    singleton = this;
    EOS_EResult setCallbackResult = EOS_Logging_SetCallback([](const EOS_LogMessage *logMessage) {
        if (EOSLogging::get_singleton()->is_log_print()) {
            String msg = vformat("[EOS %s - %s]: %s", logMessage->Category, logMessage->Message);
            switch (logMessage->Level) {
                case EOS_LOG_Fatal: {
                    UtilityFunctions::printerr(vformat("[EOS Fatal] %s: %s", logMessage->Category, logMessage->Message));
                } break;
                case EOS_LOG_Error: {
                    UtilityFunctions::printerr(vformat("[EOS Error] %s: %s", logMessage->Category, logMessage->Message));
                } break;
                case EOS_LOG_Warning: {
                    UtilityFunctions::print_rich(vformat("[color=yellow][EOS] %s: %s[/color]", logMessage->Category, logMessage->Message));
                } break;
                case EOS_LOG_Info: {
                    UtilityFunctions::print(vformat("[EOS] %s: %s", logMessage->Category, logMessage->Message));
                } break;
                case EOS_LOG_Verbose: {
                    UtilityFunctions::print(vformat("[EOS Verbose] %s: %s", logMessage->Category, logMessage->Message));
                } break;
                case EOS_LOG_VeryVerbose: {
                    UtilityFunctions::print(vformat("[EOS Very Verbose] %s: %s", logMessage->Category, logMessage->Message));
                } break;
                case EOS_LOG_Off:
                case __EOS_ELogLevel_PAD_INT32__:
                    break;
            }
        }
        EOSLogging::get_singleton()->emit_signal(SNAME("logging_callback"), String(logMessage->Category), String(logMessage->Message), logMessage->Level);
    });

    if (setCallbackResult != EOS_EResult::EOS_Success) {
        UtilityFunctions::print("[EOS SDK] Failed to set logging callback: " + String(EOS_EResult_ToString(setCallbackResult)));
    }
}
EOSLogging::~EOSLogging() {
    ERR_FAIL_COND(singleton != this);
    singleton = nullptr;
}
#endif // LOGGING_ENABLED

/////////
EOS_HPlatform *EOSCommon::m_EOS_HPlatform{};
// TODO: 句柄定义宏

void EOSCommon::_bind_methods() {
    ClassDB::bind_static_method(get_class_static(), D_METHOD("get_eos_sdk_version"), get_eos_sdk_version);
#ifdef LOGGING_ENABLED
    ClassDB::bind_static_method(get_class_static(), D_METHOD("get_logging_singleton"), get_logging_singleton);
#endif // LOGGING_ENABLED
    // TODO: 绑定枚举宏
}

void EOSCommon::init() {
    // TODO: platform 接口的初始化
#ifdef LOGGING_ENABLED
    memnew(EOSLogging);
#endif // LOGGING_ENABLED
    // TODO: 获取所有接口句柄 宏
}

String EOSCommon::get_eos_sdk_version() { return EOS_GetVersion(); }

void EOSAnticheatCommon::_bind_methods() {
    // TODO: 绑定枚举宏
}

} //namespace godot

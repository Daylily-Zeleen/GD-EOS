#pragma once

#include "eos_data_class.h"
#include <godot_cpp/classes/ref_counted.hpp>

#include <eos_sdk.h>

#define LOGGING_ENABLED
#ifdef LOGGING_ENABLED
#include <eos_logging.h>
#endif // LOGGING_ENABLED

namespace godot {
class EOSLogging : public Object {
    GDCLASS(EOSLogging, Object)

    bool log_print = false;
    static EOSLogging *singleton;

protected:
    static void _bind_methods();

public:
    EOSLogging();
    ~EOSLogging();

    static EOSLogging *get_singleton() { return singleton; }
    EOS_EResult set_log_level(EOS_ELogCategory LogCategory, EOS_ELogLevel LogLevel);
    // Setget
    _DEFINE_SETGET_BOOL(log_print)
};

class EOSCommon : public Object {
    GDCLASS(EOSCommon, Object)

protected:
    static void _bind_methods();

protected:
    static EOS_HPlatform *m_EOS_HPlatform;
    // TODO: 句柄申明

#ifdef LOGGING_ENABLED
    virtual EOS_EResult set_log_level(EOS_ELogLevel LogLevel) { return EOS_EResult::EOS_NotImplemented; }
#endif // LOGGING_ENABLED

public:
    // TODO: USING 枚举宏

    static void init(); // TODO: 检查是否只初始化一次

    static String get_eos_sdk_version();

#ifdef LOGGING_ENABLED
    static EOSLogging *get_logging_singleton() { return EOSLogging::get_singleton(); }
#endif // LOGGING_ENABLED

public:
    static EOS_HPlatform *get_EOS_HPlatform() { return m_EOS_HPlatform; }
    // TODO: 句柄getter申明
};

class EOSAnticheatCommon : public EOSCommon {
    GDCLASS(EOSAnticheatCommon, EOSCommon)
protected:
    static void _bind_methods();

public:
    // TODO: USING 枚举宏
};

} //namespace godot

// TODO: 枚举 CAST
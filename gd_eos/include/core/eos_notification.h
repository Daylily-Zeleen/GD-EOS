#pragma once

#include <eos_common.h>

#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/callable.hpp>

namespace godot::eos {
namespace internal {
class EOSNotifyRemoverBase {
public:
    virtual void remove_notify(EOS_NotificationId p_notification_id) = 0;
};

template <typename THandle, typename TRemoveCallback>
class EOSNotifyRemover : public EOSNotifyRemoverBase {
private:
    THandle owner_handle;
    TRemoveCallback remove_callback;

public:
    EOSNotifyRemover(THandle p_owner_handle, TRemoveCallback p_remove_callback) :
            owner_handle(p_owner_handle), remove_callback(p_remove_callback) {}

    virtual void remove_notify(EOS_NotificationId p_notification_id) {
        remove_callback(owner_handle, p_notification_id);
    }
};
}; //namespace internal

class EOSNotification : public RefCounted {
    GDCLASS(EOSNotification, RefCounted)
protected:
    static void _bind_methods();

public:
    ~EOSNotification() override;

    void _setup(EOS_NotificationId p_notification_id, internal::EOSNotifyRemoverBase *p_remover, const Callable &p_callback);

    template <typename T>
    void notify(const T &p_arg) {
        if (notify_callback.is_valid()) {
            notify_callback.call(p_arg);
        }
        emit_received(p_arg);
    }

    template <typename... ARGS>
    void notify(ARGS... p_args) {
        if (notify_callback.is_valid()) {
            notify_callback.call(p_args...);
        }
        if constexpr (sizeof...(p_args) == 0) {
            emit_received();
        }
        if constexpr (sizeof...(p_args) == 1) {
            emit_received(p_args...);
        }
        if constexpr (sizeof...(p_args) > 1) {
            emit_received(Array::make(p_args...));
        }
    }

public:
    bool is_valid() const;

    Callable get_callback() const;
    void set_callback(const Callable &p_callback);

    Signal to();

private:
    Callable notify_callback;
    EOS_NotificationId notification_id{ EOS_INVALID_NOTIFICATIONID };
    internal::EOSNotifyRemoverBase *remover;

    void emit_received(const Variant &p_args = Variant());
};
}; // namespace godot::eos

#define _EOS_NOTIFY_CALLBACK(m_callback_info_ty, m_callback_identifier, m_arg_type)           \
    [](m_callback_info_ty m_callback_identifier) {                                            \
        EOSNotification *notification = (EOSNotification *)m_callback_identifier->ClientData; \
        auto cb_data = m_arg_type::from_eos(*m_callback_identifier);                          \
        notification->notify(cb_data);                                                        \
    }

#define _EOS_NOTIFY_CALLBACK_EXPANDED(m_callback_info_ty, m_callback_identifier, ...)         \
    [](m_callback_info_ty m_callback_identifier) {                                            \
        EOSNotification *notification = (EOSNotification *)m_callback_identifier->ClientData; \
        notification->notify(Array::make(##__VA_ARGS__));                                     \
    }

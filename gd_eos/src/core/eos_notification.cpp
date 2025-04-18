#include <core/eos_notification.h>

#include <core/utils.h>

using namespace godot;
using namespace godot::eos;

static const StringName &s_received() {
    static const StringName ret{ "received" };
    return ret;
}

void EOSNotification::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_callback"), &EOSNotification::set_callback);
    ClassDB::bind_method(D_METHOD("get_callback"), &EOSNotification::get_callback);
    ADD_PROPERTY(PropertyInfo(Variant::CALLABLE, "callback"), "set_callback", "get_callback");
    ADD_SIGNAL(MethodInfo(s_received(), PropertyInfo(Variant::NIL, "args")));
}

EOSNotification::~EOSNotification() {
    if (is_valid() && remover) {
        remover->remove_notify(notification_id);
        memdelete(remover);
    }
}

void EOSNotification::_setup(EOS_NotificationId p_notification_id, internal::EOSNotifyRemoverBase *p_remover, const Callable &p_callback) {
    ERR_FAIL_COND(p_notification_id == EOS_INVALID_NOTIFICATIONID);
    ERR_FAIL_NULL(p_remover);

    notification_id = p_notification_id;
    remover = p_remover;
    notify_callback = p_callback;
}

bool EOSNotification::is_valid() const {
    return notification_id != EOS_INVALID_NOTIFICATIONID;
}

Callable EOSNotification::get_callback() const {
    return notify_callback;
}

void EOSNotification::set_callback(const Callable &p_callback) {
    notify_callback = p_callback;
}

Signal EOSNotification::to() {
    return Signal(this, s_received());
}

void EOSNotification::emit_received(const Variant &p_args) {
    emit_signal(s_received(), p_args);
}
#include <core/eos_notification.h>

#include <core/utils.h>

using namespace godot;
using namespace godot::eos;

void EOSNotification::_bind_methods() {
    ADD_SIGNAL(MethodInfo("notified", PropertyInfo(Variant::NIL, "arg")));
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
    return Signal(this, SNAME("notified"));
}

void EOSNotification::emit_notified(const Variant &p_args) {
    emit_signal(SNAME("notified"), p_args);
}
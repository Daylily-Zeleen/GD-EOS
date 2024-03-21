#pragma once
#include "eos_presence.h"
#include "godot_cpp/classes/ref_counted.hpp"

#include "eos_constants.h"
namespace godot {

class EOSGPresenceModification : public RefCounted {
    GDCLASS(EOSGPresenceModification, RefCounted)

protected:
    EOS_HPresenceModification m_internal = nullptr;
    static void _bind_methods();

public:
    EOS_EResult delete_data(Array p_keys);
    EOS_EResult set_data(Dictionary p_data);
    EOS_EResult set_join_info(const String &p_join_info);
    EOS_EResult set_raw_rich_text(const String &p_raw_rich_text);
    EOS_EResult set_status(int new_status);

    EOSGPresenceModification(){};
    ~EOSGPresenceModification() {
        if (m_internal != nullptr) {
            EOS_PresenceModification_Release(m_internal);
        }
    };

    void set_internal(EOS_HPresenceModification p_internal) {
        m_internal = p_internal;
    }

    EOS_HPresenceModification get_internal() {
        return m_internal;
    }
};

} // namespace godot
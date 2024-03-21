#pragma once
#include "eos_sessions.h"
#include "godot_cpp/classes/ref_counted.hpp"

#include "eos_constants.h"
namespace godot {

class EOSGSessionModification : public RefCounted {
    GDCLASS(EOSGSessionModification, RefCounted)

private:
    EOS_HSessionModification m_internal = nullptr;
    static void _bind_methods();

public:
    EOS_EResult add_attribute(const String &key, Variant value, int advertisement_type);
    EOS_EResult remove_attribute(const String &key);
    EOS_EResult set_allowed_platform_ids(const TypedArray<int> &p_platform_ids);
    EOS_EResult set_bucket_id(const String &bucket_id);
    EOS_EResult set_host_address(const String &host_address);
    EOS_EResult set_invites_allowed(bool invites_allowed);
    EOS_EResult set_join_in_progress_allowed(bool join_in_progress_allowed);
    EOS_EResult set_max_players(int max_players);
    EOS_EResult set_permission_level(int permission_level);

    EOSGSessionModification(){};
    ~EOSGSessionModification() {
        if (m_internal != nullptr) {
            EOS_SessionModification_Release(m_internal);
        }
    };

    void set_internal(EOS_HSessionModification p_internal) {
        m_internal = p_internal;
    }

    EOS_HSessionModification get_internal() {
        return m_internal;
    }
};
} // namespace godot

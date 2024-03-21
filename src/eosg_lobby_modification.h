#pragma once
#include "eos_lobby.h"
#include "godot_cpp/classes/ref_counted.hpp"

namespace godot {

class EOSGLobbyModification : public RefCounted {
    GDCLASS(EOSGLobbyModification, RefCounted)

private:
    EOS_HLobbyModification m_internal = nullptr;
    static void _bind_methods();

public:
    EOS_EResult add_attribute(const String &key, Variant value, int visibility);
    EOS_EResult add_member_attribute(const String &key, Variant value, int visibility);
    EOS_EResult remove_attribute(const String &key);
    EOS_EResult remove_member_attribute(const String &key);
    EOS_EResult set_allowed_platform_ids(const TypedArray<int> &platform_ids);
    EOS_EResult set_bucket_id(const String &bucket_id);
    EOS_EResult set_invites_allowed(bool invites_allowed);
    EOS_EResult set_max_members(int max_members);
    EOS_EResult set_permission_level(int permission_level);

    EOSGLobbyModification(){};
    ~EOSGLobbyModification() {
        if (m_internal != nullptr) {
            EOS_LobbyModification_Release(m_internal);
        }
    };

    void set_internal(EOS_HLobbyModification p_internal) {
        m_internal = p_internal;
    }

    EOS_HLobbyModification get_internal() {
        return m_internal;
    }
};
} // namespace godot

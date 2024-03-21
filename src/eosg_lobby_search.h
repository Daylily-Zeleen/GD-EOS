#pragma once
#include "eos_lobby.h"
#include "godot_cpp/classes/ref_counted.hpp"

#include "eos_constants.h"

namespace godot {

class EOSGLobbySearch : public RefCounted {
    GDCLASS(EOSGLobbySearch, RefCounted)

private:
    EOS_HLobbySearch m_internal = nullptr;
    static void _bind_methods();

public:
    Dictionary copy_search_result_by_index(int index);
    int get_search_result_count();
    EOS_EResult remove_parameter(const String &key, int comparison_op);
    EOS_EResult set_lobby_id(const String &lobby_id);
    EOS_EResult set_max_results(int max_results);
    EOS_EResult set_parameter(const String &key, Variant value, int comparison_op);
    EOS_EResult set_target_user_id(const String &target_user_id);
    Signal find(const String &local_user_id);

    EOSGLobbySearch(){};
    ~EOSGLobbySearch() {
        if (m_internal != nullptr) {
            EOS_LobbySearch_Release(m_internal);
        }
    };

    void set_internal(EOS_HLobbySearch p_internal) {
        m_internal = p_internal;
    }

    EOS_HLobbySearch get_internal() {
        return m_internal;
    }
};
} // namespace godot

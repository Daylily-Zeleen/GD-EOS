#include <register_types.h>

#include <eos_interfaces.h>

#if !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
#include "eos_packet_peer_mediator.h"
#endif // !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)

#if defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)
#include <editor/eos_editor_plugin.h>
#include <godot_cpp/classes/editor_plugin_registration.hpp>
#endif // defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

using namespace godot;

void initialize_gdeos_module(ModuleInitializationLevel p_level) {
#if defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        godot::eos::setup_eos_project_settings();
#ifdef false
        GDREGISTER_INTERNAL_CLASS(godot::eos::editor::EOSExportPlugin);
        GDREGISTER_INTERNAL_CLASS(godot::eos::editor::EOSEditorPlugin);
        EditorPlugins::add_by_type<godot::eos::editor::EOSEditorPlugin>();
#endif
    }
#endif // defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSNotification);
    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSDataClass);
    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSPackedResult);

#if !defined(EOS_ANTICHEATCLIENT_DISABLED) || !defined(EOS_ANTICHEATSERVER_DISABLED)
    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSAntiCheatCommon_Client);
#endif // !defined(EOS_ANTICHEATCLIENT_DISABLED) || !defined(EOS_ANTICHEATSERVER_DISABLED)

    REGISTER_EOS_CLASSES()
    REGISTER_EOS_SINGLETONS()

#if !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSMultiPlayerConnectionInfo);
    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSPacketPeerMediator);
    memnew(godot::eos::EOSPacketPeerMediator);
    Engine::get_singleton()->register_singleton(godot::eos::EOSPacketPeerMediator::get_class_static(), godot::eos::EOSPacketPeerMediator::get_singleton());

    GDREGISTER_CLASS(godot::eos::EOSMultiplayerPeer);
#endif // !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)

#ifdef EOS_ASSUME_ONLY_ONE_USER
    eos::EOSProductUserId::_init_local();
    eos::EOSEpicAccountId::_init_local();
#endif // EOS_ASSUME_ONLY_ONE_USER
}

void uninitialize_gdeos_module(ModuleInitializationLevel p_level) {
#if (defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)) && false
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        EditorPlugins::remove_by_type<godot::eos::editor::EOSEditorPlugin>();
    }
#endif // defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

#ifdef EOS_ASSUME_ONLY_ONE_USER
    eos::EOSProductUserId::_deinit_local();
    eos::EOSEpicAccountId::_deinit_local();
#endif // EOS_ASSUME_ONLY_ONE_USER

#if !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
    Engine::get_singleton()->unregister_singleton(godot::eos::EOSPacketPeerMediator::get_class_static());
    memdelete(godot::eos::EOSPacketPeerMediator::get_singleton());
#endif // !defined (EOS_P2P_DISABLED) and ! defined (EOS_CONNECT_DISABLED)

    UNREGISTER_EOS_SINGLETONS()
}

extern "C" {
// Initialization.
GDExtensionBool GDE_EXPORT gdeos_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
    godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_gdeos_module);
    init_obj.register_terminator(uninitialize_gdeos_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}
}
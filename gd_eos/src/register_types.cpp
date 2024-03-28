#include <register_types.h>

#include <eos_interfaces.h>

#if !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
#include "eos_packet_peer_mediator.h"
#endif // !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)

using namespace godot;

void initialize_gdeos_module(ModuleInitializationLevel p_level) {
    if (p_level == MODULE_INITIALIZATION_LEVEL_EDITOR) {
        eos::setup_eos_project_settings();
    }

    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    REGISTER_EOS_CLASSES()
    REGISTER_EOS_SINGLETONS()

#if !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
    GDREGISTER_ABSTRACT_CLASS(godot::eos::EOSPacketPeerMediator);
    memnew(godot::eos::EOSPacketPeerMediator);
    Engine::get_singleton()->register_singleton(godot::eos::EOSPacketPeerMediator::get_class_static(), godot::eos::EOSPacketPeerMediator::get_singleton());

    GDREGISTER_CLASS(godot::eos::EOSMultiplayerPeer);
#endif // !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
}

void uninitialize_gdeos_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

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
#include "register_types.h"

#include "gen/eos_interfaces.h"

#include "eos_packet_peer_mediator.h"

using namespace godot;

// DEFINE_INTERFACE_SINGLETONS()

void initialize_eosg_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    REGISTER_EOS_CLASSES()
    REGISTER_EOS_SINGLETONS()

    GDREGISTER_ABSTRACT_CLASS(EOSPacketPeerMediator);
    memnew(EOSPacketPeerMediator);
    Engine::get_singleton()->register_singleton(EOSPacketPeerMediator::get_class_static(), EOSPacketPeerMediator::get_singleton());

    GDREGISTER_CLASS(EOSMultiplayerPeer);
}

void uninitialize_eosg_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

    Engine::get_singleton()->unregister_singleton(EOSPacketPeerMediator::get_class_static());
    memdelete(EOSPacketPeerMediator::get_singleton());

    UNREGISTER_EOS_SINGLETONS()
}

extern "C" {
// Initialization.
GDExtensionBool GDE_EXPORT eosg_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
    godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_eosg_module);
    init_obj.register_terminator(uninitialize_eosg_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}
}
#include "register_types.h"

#include "eos_constants.h"
#include "eosg_active_session.h"
#include "eosg_continuance_token.h"
#include "eosg_file_transfer_request.h"
#include "eosg_lobby_details.h"
#include "eosg_lobby_modification.h"
#include "eosg_lobby_search.h"
#include "eosg_multiplayer_peer.h"
#include "eosg_packet_peer_mediator.h"
#include "eosg_presence_modification.h"
#include "eosg_session_details.h"
#include "eosg_session_modification.h"
#include "eosg_session_search.h"
#include "eosg_transaction.h"
#include "godot_cpp/classes/engine.hpp"
#include "godot_cpp/godot.hpp"
#include "ieos.h"

using namespace godot;

DEFINE_INTERFACE_SINGLETONS()

void initialize_eosg_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

    GDREGISTER_ABSTRACT_CLASS(godot::EOSGFileTransferRequest);
    GDREGISTER_ABSTRACT_CLASS(godot::EOSGPlayerDataStorageFileTransferRequest);
    GDREGISTER_ABSTRACT_CLASS(godot::EOSGTitleStorageFileTransferRequest);

    GDREGISTER_CLASS(godot::EOSGActiveSession);
    GDREGISTER_CLASS(godot::EOSGContinuanceToken);
    GDREGISTER_CLASS(godot::EOSGLobbyDetails);
    GDREGISTER_CLASS(godot::EOSGLobbyModification);
    GDREGISTER_CLASS(godot::EOSGLobbySearch);
    GDREGISTER_CLASS(godot::EOSGMultiplayerPeer);
    GDREGISTER_CLASS(godot::EOSGPresenceModification);
    GDREGISTER_CLASS(godot::EOSGSessionDetails);
    GDREGISTER_CLASS(godot::EOSGSessionModification);
    GDREGISTER_CLASS(godot::EOSGSessionSearch);
    GDREGISTER_CLASS(godot::EOSGTransaction);

    GDREGISTER_ABSTRACT_CLASS(godot::EOSConstants);

    GDREGISTER_ABSTRACT_CLASS(godot::EOSDataClassOptions);
    GDREGISTER_ABSTRACT_CLASS(godot::EOSDataClass);
    REGISTER_DATA_CLASSES();

    REGISTER_AND_ADD_SINGLETON(godot::IEOS);
    REGISTER_AND_ADD_SINGLETON(godot::EOSGPacketPeerMediator);
    REGISTER_INTERFACE_SINGLETONS();
}

void uninitialize_eosg_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

    UNREGISTER_INTERFACE_SINGLETONS()
    UNREGISTER_AND_DELETE_SINGLETON(godot::IEOS);
    UNREGISTER_AND_DELETE_SINGLETON(godot::EOSGPacketPeerMediator);
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
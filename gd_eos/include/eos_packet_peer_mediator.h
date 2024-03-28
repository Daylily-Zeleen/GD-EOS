#pragma once

#if !defined(EOS_P2P_DISABLED) and !defined(EOS_CONNECT_DISABLED)

#include <interfaces/eos_connect_interface.h>

#include "eos_multiplayer_peer.h"

namespace godot::eos {
struct PacketData {
private:
    PackedByteArray data;
    String remote_user_id;
    int channel = 0;

public:
    void store(uint8_t *p_packet, int p_size_bytes) {
        data.resize(p_size_bytes);
        memcpy(data.ptrw(), p_packet, p_size_bytes);
    }

    int size() {
        return data.size();
    }

    int get_channel() {
        return channel;
    }

    String get_sender() {
        return remote_user_id;
    }

    void set_channel(int channel) {
        this->channel = channel;
    }

    void set_sender(EOS_ProductUserId sender) {
        remote_user_id = internal::product_user_id_to_string(sender);
    }

    const PackedByteArray &get_data() {
        return data;
    }
};

class EOSPacketPeerMediator : public Object {
    GDCLASS(EOSPacketPeerMediator, Object)

private:
    static EOSPacketPeerMediator *singleton;

    static void _bind_methods();

    HashMap<String, EOSMultiplayerPeer *> active_peers;
    HashMap<String, List<PacketData *>> socket_packet_queues;
    List<ConnectionRequestData> pending_connection_requests;
    int max_queue_size = 5000;
    bool initialized = false;

    void _on_process_frame();
    void _init();
    void _terminate();

    static void EOS_CALL _on_peer_connection_established(const EOS_P2P_OnPeerConnectionEstablishedInfo *data);
    static void EOS_CALL _on_peer_connection_interrupted(const EOS_P2P_OnPeerConnectionInterruptedInfo *data);
    static void EOS_CALL _on_remote_connection_closed(const EOS_P2P_OnRemoteConnectionClosedInfo *data);
    static void EOS_CALL _on_incoming_connection_request(const EOS_P2P_OnIncomingConnectionRequestInfo *data);

    void _on_connect_interface_login(const Ref<EOSConnect_LoginCallbackInfo> &p_login_callback_info);
    void _on_connect_interface_login_statues_changed(const Ref<EOSConnect_LoginStatusChangedCallbackInfo> &p_callback_info);

    bool _add_connection_established_callback();
    bool _add_connection_closed_callback();
    bool _add_connection_interrupted_callback();
    bool _add_connection_request_callback();
    void _forward_pending_connection_requests(EOSMultiplayerPeer *peer);

    EOS_NotificationId connection_established_callback_id = EOS_INVALID_NOTIFICATIONID;
    EOS_NotificationId connection_interrupted_callback_id = EOS_INVALID_NOTIFICATIONID;
    EOS_NotificationId connection_closed_callback_id = EOS_INVALID_NOTIFICATIONID;
    EOS_NotificationId connection_request_callback_id = EOS_INVALID_NOTIFICATIONID;

public:
    static EOSPacketPeerMediator *get_singleton() {
        return singleton;
    }

    int get_total_packet_count() {
        int ret = 0;
        for (KeyValue<String, List<PacketData *>> &E : socket_packet_queues) {
            ret += E.value.size();
        }
        return ret;
    }

    int get_packet_count_for_socket(const String &socket_id) {
        ERR_FAIL_COND_V_MSG(!socket_packet_queues.has(socket_id), 0, "Failed to get packet count for socket \"%s\". Socket does not exist.");
        return socket_packet_queues[socket_id].size();
    }

    PackedStringArray get_sockets() {
        PackedStringArray ret;
        for (KeyValue<String, List<PacketData *>> &E : socket_packet_queues) {
            ret.push_back(E.key);
        }
        return ret;
    }

    bool has_socket(const String &socket_id) {
        return socket_packet_queues.has(socket_id);
    }

    int get_queue_size_limit() {
        return max_queue_size;
    }

    void set_queue_size_limit(int limit) {
        ERR_FAIL_COND_MSG(limit <= 0, "Cannot set queue size limit. Limit must be greater than 0");
        max_queue_size = limit;
    }

    int get_connection_request_count() {
        return pending_connection_requests.size();
    }

    int get_packet_count_from_remote_user(const String &remote_user_id, const String &socket_id);
    bool poll_next_packet(const String &socket_id, PacketData **out_packet);
    bool next_packet_is_peer_id_packet(const String &socket_id);
    bool register_peer(EOSMultiplayerPeer *peer);
    void unregister_peer(EOSMultiplayerPeer *peer);
    void clear_packet_queue(const String &socket_id);
    void clear_packets_from_remote_user(const String &socket_id, const String &remote_user_id);

    void _notification(int p_what);

    EOSPacketPeerMediator();
    ~EOSPacketPeerMediator();
};
} //namespace godot::eos

#endif // !defined(EOS_P2P_DISABLED) and !defined(EOS_CONNECT_DISABLED)
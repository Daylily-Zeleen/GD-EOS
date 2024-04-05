#pragma once
#if !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)

#include <handles/eos_common.handles.h>
#include <godot_cpp/classes/multiplayer_peer_extension.hpp>
#include <godot_cpp/templates/hash_map.hpp>

#include "core/utils.h"

namespace godot::eos {
struct ConnectionRequestData {
    EOS_ProductUserId local_user_id;
    EOS_ProductUserId remote_user_id;
    String socket_name;
};

class EOSMultiPlayerConnectionInfo : public RefCounted {
    GDCLASS(EOSMultiPlayerConnectionInfo, RefCounted)

    // 暴露给 gds 不区分 SocketId 与 SocketName
    String socket_id; 
    Ref<EOSProductUserId> remote_user_id;
    Ref<EOSProductUserId> local_user_id;

protected:
    static void _bind_methods();

public:
    _DECLARE_SETGET(socket_id);
    _DECLARE_SETGET(remote_user_id);
    _DECLARE_SETGET(local_user_id);

    static Ref<EOSMultiPlayerConnectionInfo> make(const String &p_socket_id, EOS_ProductUserId p_local_user_id, EOS_ProductUserId p_remote_user_id);
    static Ref<EOSMultiPlayerConnectionInfo> make(const ConnectionRequestData &p_from);

    static PropertyInfo make_property_info(const String &p_property_name = "connection_info");
};

class EOSMultiplayerPeer : public MultiplayerPeerExtension {
    GDCLASS(EOSMultiplayerPeer, MultiplayerPeerExtension)

    template <typename T>
    using SharedPtr = internal::_SharedPtr<T>;

private:
    enum Event : int8_t {
        EVENT_STORE_PACKET,
        EVENT_RECIEVE_PEER_ID,
        EVENT_MESH_CONNECTION_REQUEST
    };

    enum : int8_t {
        INDEX_EVENT_TYPE = 0,
        INDEX_TRANSFER_MODE = 1,
        INDEX_PEER_ID = 2,
        INDEX_PAYLOAD_DATA = 6,
    };

    enum : int8_t {
        CH_RELIABLE = 0,
        CH_UNRELIABLE = 1,
        CH_MAX = 2,
    };

    enum Mode : int8_t {
        MODE_NONE,
        MODE_SERVER,
        MODE_CLIENT,
        MODE_MESH,
    };

    class EOSPacket : public internal::_Sharable {
    private:
        PackedByteArray packet;
        int sender_peer_id = 0;
        Event event;
        EOS_EPacketReliability reliability;
        uint8_t channel = 0;

        void _alloc_packet(int size_bytes = PACKET_HEADER_SIZE) {
            packet.resize(size_bytes);
        }

    public:
        static constexpr int PACKET_HEADER_SIZE = 6;

        void prepare();
        void store_payload(const uint8_t *p_payload_data, const uint32_t p_payload_size_bytes);

        int payload_size() const {
            return packet.size() - PACKET_HEADER_SIZE;
        }

        int packet_size() const {
            return packet.size();
        }

        const uint8_t *get_payload() const {
            if (packet.size() <= PACKET_HEADER_SIZE) {
                return nullptr; //Return nullptr if there's no payload.
            }
            return packet.ptr() + INDEX_PAYLOAD_DATA;
        }

        const uint8_t *get_packet() const {
            //Return nullptr if the packed has not been allocated
            return packet.ptr();
        }

        EOS_EPacketReliability get_reliability() const {
            return reliability;
        }

        void set_reliability(EOS_EPacketReliability p_reliability) {
            this->reliability = p_reliability;
        }

        uint8_t get_channel() const {
            return channel;
        }

        void set_channel(uint8_t p_channel) {
            this->channel = p_channel;
        }

        Event get_event() const {
            return event;
        }

        void set_event(Event p_event) {
            this->event = p_event;
        }

        int get_sender() const {
            return sender_peer_id;
        }

        void set_sender(int p_id) {
            sender_peer_id = p_id;
        }
    };

    class EOSSocket {
    private:
        EOS_P2P_SocketId socket;
        List<SharedPtr<EOSPacket>> incoming_packets;

    public:
        const EOS_P2P_SocketId *get_id() const {
            return &socket;
        }

        String get_name() const {
            return socket.SocketName;
        }

        void push_packet(const SharedPtr<EOSPacket> &packet) {
            incoming_packets.push_back(packet);
        }

        SharedPtr<EOSPacket> pop_packet() {
            SharedPtr<EOSPacket> ret = incoming_packets.front()->get();
            incoming_packets.pop_front();
            return ret;
        }

        void clear_packet_queue() {
            incoming_packets.clear();
        }

        bool has_packet() const {
            return incoming_packets.size() != 0;
        }

        int get_packet_count() const {
            return incoming_packets.size();
        }

        EOS_EPacketReliability get_packet_reliability() const {
            const SharedPtr<EOSPacket> &packet = incoming_packets.front()->get();
            return packet->get_reliability();
        }

        int32_t get_packet_channel() const {
            const SharedPtr<EOSPacket> &packet = incoming_packets.front()->get();
            return packet->get_channel();
        }

        int32_t get_packet_peer() const {
            const SharedPtr<EOSPacket> &packet = incoming_packets.front()->get();
            return packet->get_sender();
        }

        void close();
        void clear_packets_from_peer(int p_peer);
        bool _socket_id_is_valid(const String &socket_id);

        EOSSocket() = default;

        EOSSocket(const EOS_P2P_SocketId &socket) {
            this->socket = socket;
        }

        EOSSocket(const String &socket_name) {
            memset(socket.SocketName, 0, sizeof(socket.SocketName));
            ERR_FAIL_COND_MSG(!_socket_id_is_valid(socket_name), "Failed to create socket. Socket id is not valid.\nNOTE: Socket id cannot be empty, must only have alpha-numeric characters, and must not be longer than 32 characters");
            socket.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;
            STRNCPY_S(socket.SocketName, EOS_P2P_SOCKETID_SOCKETNAME_SIZE, socket_name.utf8(), socket_name.length());
        }
    };

    _FORCE_INLINE_ bool _is_active() const { return active_mode != MODE_NONE; }

    Error _broadcast(const EOSPacket &packet, int exclude = 0);
    Error _send_to(EOS_ProductUserId remote_peer, const EOSPacket &packet);
    bool _is_requesting_connection(EOS_ProductUserId p_remote_user_id);
    // bool _find_connection_request(EOS_ProductUserId remote_user, EOS_ProductUserId &out_request);
    EOS_EPacketReliability _convert_transfer_mode_to_eos_reliability(TransferMode mode) const;
    TransferMode _convert_eos_reliability_to_transfer_mode(EOS_EPacketReliability reliability) const;
    void _disconnect_remote_user(EOS_ProductUserId remote_user_id);
    void _clear_peer_packet_queue(int p_id);

    static Ref<EOSProductUserId> s_local_user_id_wrapped;
    static EOS_ProductUserId s_local_user_id;

    SharedPtr<EOSPacket> current_packet;
    uint32_t unique_id;
    int target_peer = 0;
    ConnectionStatus connection_status = CONNECTION_DISCONNECTED;
    Mode active_mode = MODE_NONE;
    EOS_Bool allow_delayed_delivery = EOS_TRUE;
    bool auto_accept_connection_requests = true;
    TransferMode transfer_mode = TransferMode::TRANSFER_MODE_RELIABLE;
    uint32_t transfer_channel = CH_RELIABLE;
    bool refusing_connections = false;
    bool polling = false;

    HashMap<uint32_t, EOS_ProductUserId> peers;

    EOSSocket socket;
    List<EOS_ProductUserId> pending_connection_requests;

    static void _bind_methods();

    int _get_peer_id(EOS_ProductUserId remote_user_id);
    bool _has_user_id(EOS_ProductUserId remote_user_id);
    void _accept_connection_request(EOS_ProductUserId remote_user_id);
    void _deny_connection_request(EOS_ProductUserId remote_user_id);

public:
    static void set_local_user_id(const Ref<EOSProductUserId> &p_local_user_id);
    static Ref<EOSProductUserId> get_local_user_id_wrapped();
    // 只在 cpp 中使用
    static const EOS_ProductUserId get_local_user_id() { return s_local_user_id; }

    void peer_connection_established_callback(const EOS_P2P_OnPeerConnectionEstablishedInfo *data);
    void remote_connection_closed_callback(const EOS_P2P_OnRemoteConnectionClosedInfo *data);
    void peer_connection_interrupted_callback(const EOS_P2P_OnPeerConnectionInterruptedInfo *data);
    void connection_request_callback(const ConnectionRequestData &data);

    Error create_server(const String &socket_id);
    Error create_client(const String &socket_id, const Ref<EOSProductUserId> &remote_user_id);
    Error create_mesh(const String &socket_id);
    Error add_mesh_peer(const Ref<EOSProductUserId> &remote_user_id);

    String get_socket_name() const;
    TypedArray<EOSProductUserId> get_all_connection_requests();
    Ref<EOSProductUserId> get_peer_user_id(int peer_id);
    int get_peer_id(const Ref<EOSProductUserId> &remote_user_id);
    bool has_peer(int peer_id);
    bool has_user_id(const Ref<EOSProductUserId> &remote_user_id);
    Dictionary get_all_peers();
    void set_allow_delayed_delivery(bool allow);
    bool is_allowing_delayed_delivery();
    void set_auto_accept_connection_requests(bool enable);
    bool is_auto_accepting_connection_requests();
    void accept_connection_request(const Ref<EOSProductUserId> &remote_user_id);
    void deny_connection_request(const Ref<EOSProductUserId> &remote_user_id);
    void accept_all_connection_requests();
    void deny_all_connection_requests();
    int get_active_mode();

    bool is_polling() {
        return polling;
    }

    void set_is_polling(bool polling) {
        this->polling = polling;
    }

    virtual Error _get_packet(const uint8_t **r_buffer, int32_t *r_buffer_size) override;
    virtual Error _put_packet(const uint8_t *p_buffer, int32_t p_buffer_size) override;
    virtual int32_t _get_available_packet_count() const override;
    virtual int32_t _get_max_packet_size() const override;
    //virtual PackedByteArray _get_packet_script() override;
    //virtual Error _put_packet_script(const PackedByteArray &p_buffer) override;
    virtual int32_t _get_packet_channel() const override;
    virtual MultiplayerPeer::TransferMode _get_packet_mode() const override;
    virtual void _set_transfer_channel(int32_t p_channel) override;
    virtual int32_t _get_transfer_channel() const override;
    virtual void _set_transfer_mode(MultiplayerPeer::TransferMode p_mode) override;
    virtual MultiplayerPeer::TransferMode _get_transfer_mode() const override;
    virtual void _set_target_peer(int32_t p_peer) override;
    virtual int32_t _get_packet_peer() const override;
    virtual bool _is_server() const override;
    virtual void _poll() override;
    virtual void _close() override;
    virtual void _disconnect_peer(int32_t p_peer, bool p_force = false) override;
    virtual int32_t _get_unique_id() const override;
    virtual void _set_refuse_new_connections(bool p_enable) override;
    virtual bool _is_refusing_new_connections() const override;
    virtual bool _is_server_relay_supported() const override;
    virtual MultiplayerPeer::ConnectionStatus _get_connection_status() const override;

    EOSMultiplayerPeer() = default;
    ~EOSMultiplayerPeer();
};
} //namespace godot::eos

#endif // !defined(EOS_P2P_DISABLED) && !defined(EOS_CONNECT_DISABLED)
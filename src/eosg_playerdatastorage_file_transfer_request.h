#pragma once
#include "eos_playerdatastorage.h"
#include "eosg_file_transfer_request.h"
#include "godot_cpp/classes/ref_counted.hpp"

namespace godot {

class EOSGPlayerDataStorageFileTransferRequest : public EOSGFileTransferRequest {
    GDCLASS(EOSGPlayerDataStorageFileTransferRequest, EOSGFileTransferRequest)

private:
    EOS_HPlayerDataStorageFileTransferRequest m_internal = nullptr;
    static void _bind_methods();

public:
    Dictionary get_filename() override;
    EOS_EResult cancel_request() override;
    EOS_EResult get_file_request_state() override;

    EOSGPlayerDataStorageFileTransferRequest(){};
    ~EOSGPlayerDataStorageFileTransferRequest() {
        if (m_internal != nullptr) {
            EOS_PlayerDataStorageFileTransferRequest_Release(m_internal);
        }
    }

    void set_internal(EOS_HPlayerDataStorageFileTransferRequest p_internal) {
        m_internal = p_internal;
    }

    EOS_HPlayerDataStorageFileTransferRequest get_internal() {
        return m_internal;
    }

public:
    // Unavaliable in Godot.
    void wrap(EOS_HPlayerDataStorageFileTransferRequest p_handle) {
        set_internal(p_handle);
    }

    void write_file_data_callback(const Dictionary &p_cb_data) {
        emit_signal(SNAME("write_file_data_callback"), p_cb_data);
    }

    void write_file_callback(const Dictionary &p_cb_data) {
        emit_signal(SNAME("write_file_callback"), p_cb_data);
    }

    void read_file_data_callback(const Dictionary &p_cb_data) {
        emit_signal(SNAME("read_file_data_callback"), p_cb_data);
    }

    void read_file_callback(const Dictionary &p_cb_data) {
        emit_signal(SNAME("read_file_callback"), p_cb_data);
    }

    void file_transfer_progress_callback(const Dictionary &p_cb_data) {
        emit_signal(SNAME("file_transfer_progress_callback"), p_cb_data);
    }
};

} //namespace godot

#pragma once

#include <eos_sdk.h>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/variant.hpp>

namespace godot::eos::internal {

struct _FileTransferData {
    Object *interface_handle;
    Ref<RefCounted> request_handle;

    Callable operation_callback;
    Callable progress_callback;

    Callable completion_callback;

    _FileTransferData(Object *p_interface_handle, const Ref<RefCounted> &p_request_handle, const Callable &p_operation_callback, const Callable &p_progress_callback, const Callable &p_completion_callback) :
            interface_handle(p_interface_handle), request_handle(p_request_handle), operation_callback(p_operation_callback), progress_callback(p_progress_callback), completion_callback(p_completion_callback) {}
};

template <typename EOSCallbackInfoTy, typename GDCallbackInfoTy, const char *SIGNAL_NAME>
EOS_PlayerDataStorage_EReadResult read_file_data_callback(const EOSCallbackInfoTy *p_data) {
    auto file_transfer_data = (_FileTransferData *)(p_data->ClientData);
    ERR_FAIL_COND_V(!file_transfer_data->operation_callback.is_valid(), EOS_PlayerDataStorage_EReadResult::EOS_RR_FailRequest);

    auto data = GDCallbackInfoTy::from_eos(*p_data);
    Variant res = file_transfer_data->operation_callback.call(data);
    ERR_FAIL_COND_V_MSG(res.get_type() != Variant::INT || (int32_t)res < 1 || (int32_t)res > 3, EOS_PlayerDataStorage_EReadResult::EOS_RR_FailRequest, "Read file data callback shoul return a Value of PlayerDataStorage.ReadResult.");

    EOS_PlayerDataStorage_EReadResult read_result = (EOS_PlayerDataStorage_EReadResult)(res.operator int32_t());
    if (read_result == EOS_PlayerDataStorage_EReadResult::EOS_RR_FailRequest || read_result == EOS_PlayerDataStorage_EReadResult::EOS_RR_CancelRequest) {
        return read_result;
    }

    if (file_transfer_data->request_handle.is_valid()) {
        // 仅作为通知使用
        file_transfer_data->request_handle->emit_signal(SNAME(SIGNAL_NAME), data);
    }
    return read_result;
}

template <typename EOSCallbackInfoTy, typename GDCallbackInfoTy, const char *SIGNAL_NAME>
EOS_PlayerDataStorage_EWriteResult write_file_data_callback(const EOSCallbackInfoTy *p_data, void *r_data_buffer, uint32_t *r_data_written) {
    auto file_transfer_data = (_FileTransferData *)(p_data->ClientData);
    ERR_FAIL_COND_V(!file_transfer_data->operation_callback.is_valid(), EOS_PlayerDataStorage_EWriteResult::EOS_WR_FailRequest);

    auto data = GDCallbackInfoTy::from_eos(*p_data);
    Variant res = file_transfer_data->operation_callback.call(data);
    ERR_FAIL_COND_V_MSG(res.get_type() != Variant::INT || (int32_t)res < 1 || (int32_t)res > 4, EOS_PlayerDataStorage_EWriteResult::EOS_WR_FailRequest, "Write file data callback shoul return a Value of PlayerDataStorage.WriteResult.");

    EOS_PlayerDataStorage_EWriteResult write_result = (EOS_PlayerDataStorage_EWriteResult)(res.operator int32_t());
    if (write_result == EOS_PlayerDataStorage_EWriteResult::EOS_WR_FailRequest || write_result == EOS_PlayerDataStorage_EWriteResult::EOS_WR_CancelRequest) {
        return write_result;
    }

    PackedByteArray out_data_buffer = data->get_out_data_buffer();
    ERR_FAIL_COND_V_MSG(out_data_buffer.size() > p_data->DataBufferLengthBytes, EOS_PlayerDataStorage_EWriteResult::EOS_WR_FailRequest, "The out data buffer is too large.");
    ERR_FAIL_COND_V_MSG(out_data_buffer.size() <= 0 && write_result == EOS_PlayerDataStorage_EWriteResult::EOS_WR_ContinueWriting, EOS_PlayerDataStorage_EWriteResult::EOS_WR_FailRequest, "The out data buffer is empty.");

    ERR_FAIL_COND_V(out_data_buffer.size() > p_data->DataBufferLengthBytes, EOS_PlayerDataStorage_EWriteResult::EOS_WR_FailRequest);
    memcpy(r_data_buffer, out_data_buffer.ptr(), out_data_buffer.size());
    *r_data_written = out_data_buffer.size();

    if (file_transfer_data->request_handle.is_valid()) {
        // 仅作为通知使用
        file_transfer_data->request_handle->emit_signal(SNAME(SIGNAL_NAME), data);
    }
    return write_result;
}

//=========
template <typename EOSCallbackInfoTy, typename GDCallbackInfoTy, const char *SIGNAL_NAME>
EOS_TitleStorage_EReadResult title_storage_read_file_data_callback(const EOSCallbackInfoTy *p_data) {
    auto file_transfer_data = (_FileTransferData *)(p_data->ClientData);
    ERR_FAIL_COND_V(!file_transfer_data->operation_callback.is_valid(), EOS_TitleStorage_EReadResult::EOS_TS_RR_FailRequest);

    auto data = GDCallbackInfoTy::from_eos(*p_data);
    Variant res = file_transfer_data->operation_callback.call(data);
    ERR_FAIL_COND_V_MSG(res.get_type() != Variant::INT || (int32_t)res < 1 || (int32_t)res > 3, EOS_TitleStorage_EReadResult::EOS_TS_RR_FailRequest, "Read file data callback shoul return a Value of PlayerDataStorage.ReadResult.");

    EOS_TitleStorage_EReadResult read_result = (EOS_TitleStorage_EReadResult)(res.operator int32_t());
    if (read_result == EOS_TitleStorage_EReadResult::EOS_TS_RR_FailRequest || read_result == EOS_TitleStorage_EReadResult::EOS_TS_RR_CancelRequest) {
        return read_result;
    }

    if (file_transfer_data->request_handle.is_valid()) {
        // 仅作为通知使用
        file_transfer_data->request_handle->emit_signal(SNAME(SIGNAL_NAME), data);
    }
    return read_result;
}

// ================
template <typename EOSCallbackInfoTy, typename GDCallbackInfoTy, const char *SIGNAL_NAME>
inline void file_transfer_progress_callback(const EOSCallbackInfoTy *p_data) {
    auto file_transfer_data = (_FileTransferData *)(p_data->ClientData);
    auto data = GDCallbackInfoTy::from_eos(*p_data);

    if (file_transfer_data->progress_callback.is_valid()) {
        file_transfer_data->progress_callback.call(data);
    }

    if (file_transfer_data->request_handle.is_valid()) {
        file_transfer_data->request_handle->emit_signal(SNAME(SIGNAL_NAME), data);
    }
}

template <typename EOSCallbackInfoTy, typename GDCallbackInfoTy, const char *SIGNAL_NAME, const char *INTERFACE_SIGNAL_NAME>
void file_transfer_completion_callback(const EOSCallbackInfoTy *p_data) {
    auto file_transfer_data = (_FileTransferData *)(p_data->ClientData);
    auto data = GDCallbackInfoTy::from_eos(*p_data);

    if (file_transfer_data->completion_callback.is_valid()) {
        file_transfer_data->completion_callback.call(data);
    }

    if (file_transfer_data->request_handle.is_valid()) {
        file_transfer_data->request_handle->emit_signal(SNAME(SIGNAL_NAME), data);
    }

    if (auto interface = Object::cast_to<Object>(file_transfer_data->interface_handle)) {
        interface->emit_signal(SNAME(INTERFACE_SIGNAL_NAME), p_data);
    }

    // 即使是取消/失败操作也会调用completion回调
    memdelete(file_transfer_data);
}

#define MAKE_FILE_TRANSFER_DATA(...) memnew(_FileTransferData(this, __VA_ARGS__))

} //namespace godot::eos::internal
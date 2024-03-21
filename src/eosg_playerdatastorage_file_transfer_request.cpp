#include "eosg_playerdatastorage_file_transfer_request.h"
#include "eos_playerdatastorage.h"
#include "utils.h"

using namespace godot;

void EOSGPlayerDataStorageFileTransferRequest::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_file_request_state"), &EOSGPlayerDataStorageFileTransferRequest::get_file_request_state);
    ClassDB::bind_method(D_METHOD("get_filename"), &EOSGPlayerDataStorageFileTransferRequest::get_filename);
    ClassDB::bind_method(D_METHOD("cancel_request"), &EOSGPlayerDataStorageFileTransferRequest::cancel_request);

    ADD_SIGNAL(MethodInfo("write_file_data_callback", PropertyInfo(Variant::DICTIONARY, "callback_data")));
    ADD_SIGNAL(MethodInfo("write_file_callback", PropertyInfo(Variant::DICTIONARY, "callback_data")));

    ADD_SIGNAL(MethodInfo("read_file_data_callback", PropertyInfo(Variant::DICTIONARY, "callback_data")));
    ADD_SIGNAL(MethodInfo("read_file_callback", PropertyInfo(Variant::DICTIONARY, "callback_data")));

    ADD_SIGNAL(MethodInfo("file_transfer_progress_callback", PropertyInfo(Variant::DICTIONARY, "callback_data")));
}

EOS_EResult EOSGPlayerDataStorageFileTransferRequest::get_file_request_state() {
    ERR_FAIL_NULL_V_MSG(m_internal, static_cast<EOS_EResult>(EOS_EResult::EOS_InvalidState), "The object has not been initialized by EOS.");
    return static_cast<EOS_EResult>(EOS_PlayerDataStorageFileTransferRequest_GetFileRequestState(m_internal));
}

Dictionary EOSGPlayerDataStorageFileTransferRequest::get_filename() {
    Dictionary ret;
    if (m_internal == nullptr) {
        ret["result_code"] = static_cast<EOS_EResult>(EOS_EResult::EOS_InvalidState);
        ret["filename"] = "";
        return ret;
    }
    char *outBuffer = (char *)(memalloc(EOS_PLAYERDATASTORAGE_FILENAME_MAX_LENGTH_BYTES + 1));
    int outBufferLength = EOS_PLAYERDATASTORAGE_FILENAME_MAX_LENGTH_BYTES + 1;
    EOS_EResult result = EOS_PlayerDataStorageFileTransferRequest_GetFilename(m_internal, EOS_PLAYERDATASTORAGE_FILENAME_MAX_LENGTH_BYTES + 1, outBuffer, &outBufferLength);
    ret["result_code"] = static_cast<EOS_EResult>(result);
    ret["filename"] = EOSG_GET_STRING(outBuffer);
    memfree(outBuffer);
    return ret;
}

EOS_EResult EOSGPlayerDataStorageFileTransferRequest::cancel_request() {
    ERR_FAIL_NULL_V_MSG(m_internal, static_cast<EOS_EResult>(EOS_EResult::EOS_InvalidState), "The object has not been initialized by EOS.");
    return static_cast<EOS_EResult>(EOS_PlayerDataStorageFileTransferRequest_CancelRequest(m_internal));
}
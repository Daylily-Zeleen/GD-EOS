#pragma once
#include "godot_cpp/classes/ref_counted.hpp"

#include "eos_constants.h"

namespace godot {

class EOSGFileTransferRequest : public RefCounted {
    GDCLASS(EOSGFileTransferRequest, RefCounted)

private:
    static void _bind_methods() {
        BIND_VIRTUAL_METHOD(EOSGFileTransferRequest, get_file_request_state);
        BIND_VIRTUAL_METHOD(EOSGFileTransferRequest, get_filename);
        BIND_VIRTUAL_METHOD(EOSGFileTransferRequest, cancel_request);
    };

public:
    // TODO: make these methods pure virtual
    virtual EOS_EResult get_file_request_state() {
        return EOS_EResult::EOS_InvalidState;
    }
    virtual Dictionary get_filename() {
        return Dictionary();
    }
    virtual EOS_EResult cancel_request() {
        return EOS_EResult::EOS_InvalidState;
    }

    EOSGFileTransferRequest(){};
    ~EOSGFileTransferRequest(){};
};
} // namespace godot

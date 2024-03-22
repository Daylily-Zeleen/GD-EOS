#pragma once

#include "godot_cpp/classes/ref_counted.hpp"

namespace godot {
class EOSHandleWrapper : public RefCounted {
    GDCLASS(EOSHandleWrapper, RefCounted)
protected:
    static void _bind_methods() {}
};

template <typename EOSHandleTy>
class EOSHandle : public EOSHandleWrapper {
    GDCLASS(EOSHandle, EOSHandleWrapper)

    EOSHandleTy m_handle;

protected:
    static void _bind_methods() {}

public:
    void set_handle(EOSHandleTy p_handle) { m_handle = p_handle; }
    EOSHandleTy get_handle() const { return m_handle; }
};

} //namespace godot
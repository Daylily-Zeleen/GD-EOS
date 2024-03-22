#pragma once

// #include <eos_anticheatcommon_client.h>
#include <eos_sdk.h>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/templates/local_vector.hpp>
#include <godot_cpp/variant/typed_array.hpp>
#include <godot_cpp/variant/variant.hpp>

namespace godot {

#define VARIANT_TO_CHARSTRING(str) ((String)str).utf8()
#define VARIANT_TO_EOS_BOOL(var) \
    ((var.get_type() == Variant::BOOL) ? ((var.operator bool()) ? EOS_TRUE : EOS_FALSE) : EOS_FALSE)
#define EOSG_GET_STRING(str) ((str == nullptr) ? String("") : String(str))
#define EOSG_GET_BOOL(eosBool) ((eosBool == EOS_TRUE) ? true : false)

#ifdef _MSC_VER // Check if using Microsoft Visual Studio
#define STRNCPY_S(dest, destsz, src, count) strncpy_s(dest, destsz, src, count)
#else
#define STRNCPY_S(dest, destsz, src, count) strncpy(dest, src, count)
#endif

String eosg_epic_account_id_to_string(EOS_EpicAccountId accountId);

static EOS_EpicAccountId eosg_string_to_epic_account_id(const char *p_account_id) {
    EOS_EpicAccountId accountId = EOS_EpicAccountId_FromString(p_account_id);
    return accountId;
}

String eosg_product_user_id_to_string(EOS_ProductUserId localUserId);

static EOS_ProductUserId eosg_string_to_product_user_id(const char *p_account_id) {
    EOS_ProductUserId accountId = EOS_ProductUserId_FromString(p_account_id);
    return accountId;
}

template <typename T>
using gd_arg_t = std::conditional_t<!std::is_trivial_v<T> || (sizeof(T) > 8), const T &, T>;

#define _ARG_TYPE(arg) gd_arg_t<decltype(arg)>

static StringName _get_class_name(const Variant &p_val) {
    if (auto ref = Object::cast_to<RefCounted>(p_val)) {
        return ref->get_class();
    }
    return "";
}

#define _DEFINE_SETGET(field)                  \
    auto get_##field() const { return field; } \
    void set_##field(_ARG_TYPE(field) p_val) { field = p_val; }

#define _DEFINE_SETGET_BOOL(field)            \
    bool is_##field() const { return field; } \
    void set_##field(_ARG_TYPE(field) p_val) { field = p_val; }

#define _BIND_BEGIN(klass) auto tmp_obj = memnew(klass);
#define _BIND_PROP(field)                                                                                                         \
    ClassDB::bind_method(D_METHOD("get_" #field), &std::remove_pointer_t<decltype(tmp_obj)>::get_##field);                        \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &std::remove_pointer_t<decltype(tmp_obj)>::set_##field);                 \
    ADD_PROPERTY(PropertyInfo(Variant(tmp_obj->get_##field()).get_type(), #field, PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT, \
                         _get_class_name(tmp_obj->get_##field())),                                                                \
            "set_" #field, "get_" #field);

#define _BIND_PROP_ENUM(field, enum_owner, enum_type)                                                             \
    ClassDB::bind_method(D_METHOD("get_" #field), &std::remove_pointer_t<decltype(tmp_obj)>::get_##field);        \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &std::remove_pointer_t<decltype(tmp_obj)>::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant::INT, #field, PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT,               \
                         #enum_owner "." #enum_type),                                                             \
            "set_" #field, "get_" #field);

#define _BIND_PROP_BOOL(field)                                                                                    \
    ClassDB::bind_method(D_METHOD("is_" #field), &std::remove_pointer_t<decltype(tmp_obj)>::is_##field);          \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &std::remove_pointer_t<decltype(tmp_obj)>::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant::BOOL, #field), "set_" #field, "is_" #field);
#define _BIND_END() memdelete(tmp_obj);

#define _INTERFACE_BIND_METHOD(m_klass, m_method_name, ...) \
    ClassDB::bind_method(D_METHOD(String(#m_method_name) == String("create_platform") ? "create" : #m_method_name, ##__VA_ARGS__), &m_klass::m_method_name)
#define _INTERFACE_BIND_SIGNAL(m_interface_prefix, m_name) \
    ADD_SIGNAL(MethodInfo(#m_name, MAKE_DATA_CLASS_PROP_INFO_BY_SIGNAL_NAME(m_interface_prefix##m_name)))
#define _CONNECT_INTERFACE_SIGNAL(m_interface_prefix, m_signal_name, m_klass) \
    IEOS::get_singleton()->connect(#m_interface_prefix #m_signal_name, callable_mp(this, &m_klass::m_signal_name))

#define REGISTER_AND_ADD_SINGLETON(m_klass) \
    GDREGISTER_ABSTRACT_CLASS(m_klass);     \
    memnew(m_klass);                        \
    godot::Engine::get_singleton()->register_singleton(m_klass::get_class_static(), m_klass::get_singleton())

#define UNREGISTER_AND_DELETE_SINGLETON(m_klass)                                       \
    godot::Engine::get_singleton()->unregister_singleton(m_klass::get_class_static()); \
    memdelete(m_klass::get_singleton())

// =====================
// ClientData
struct _CallbackClientData {
    Variant client_data;
    Object *handle_wrapper;
    Callable completion_callback;

    _CallbackClientData(Object *p_handle_wrapper, const Variant &p_client_data, const Callable &p_completion_callback = {}) :
            handle_wrapper(p_handle_wrapper), client_data(p_client_data), completion_callback(p_completion_callback) {}

    static auto cast_to_scoped(void *p_client_data) {
        struct ScopedObject {
        private:
            _CallbackClientData *ccd;

        public:
            Variant &get_client_data() const { return ccd->client_data; }
            Object *get_handle_warpper() const { return ccd->handle_wrapper; }
            Callable &get_completion_callback() const { return ccd->completion_callback; }

            ScopedObject(_CallbackClientData *p_ccd) :
                    ccd(p_ccd) {}
            ~ScopedObject() { memdelete(ccd); }
        } ret((_CallbackClientData *)p_client_data);
        return ret;
    }
};

#define _MAKE_CALLBACK_CLIENT_DATA(client_data, ...) memnew(_CallbackClientData(this, client_data, ##__VA_ARGS__))
#define _GET_CLIENT_DATA(callback_client_data, r_handle_wrapper) to_godot_client_data(callback_client_data, r_handle_wrapper)

inline Variant to_godot_client_data(void *p_from, Object *&r_handle_wrapper) {
    auto casted = (_CallbackClientData *)p_from;
    auto ret = casted->client_data;
    r_handle_wrapper = casted->handle_wrapper;
    memdelete(casted);
    return ret;
}

template <typename From, typename To>
static To to_godot_type(From p_from) {
    static_assert(std::is_same_v<From, To>);
    return p_from;
}

template <typename From, typename To>
static To to_eos_type(From p_from) {
    static_assert(std::is_same_v<From, To>);
    return p_from;
}

template <typename From, typename To, typename Tint>
PackedStringArray to_godot_type_arr(From p_from, Tint p_count) {
    static_assert(false);
    return {};
}

template <typename From, typename To, typename Tint>
const To to_eos_type_arr(From p_from, Tint r_count) {
    static_assert(false);
    return {};
}
// EOS_Bool
template <>
bool to_godot_type(EOS_Bool p_from) { return p_from; }
template <>
EOS_Bool to_eos_type(bool p_from) { return p_from; }

// EOS_ProductUserId
template <>
String to_godot_type(EOS_ProductUserId p_from) { return eosg_product_user_id_to_string(p_from); }
template <>
EOS_ProductUserId to_eos_type(const String &p_from) { return eosg_string_to_product_user_id(VARIANT_TO_CHARSTRING(p_from).get_data()); }

// EOS_EpicAccountId
template <>
String to_godot_type(EOS_EpicAccountId p_from) { return eosg_epic_account_id_to_string(p_from); }
template <>
EOS_EpicAccountId to_eos_type(const String &p_from) { return eosg_string_to_epic_account_id(VARIANT_TO_CHARSTRING(p_from).get_data()); }

// const char *
using cstr_t = const char *;
template <>
String to_godot_type(cstr_t p_from) { return String::utf8(p_from); }
template <>
cstr_t to_eos_type(const String &p_from) { return p_from.utf8().ptr(); }

// cstr_t*
template <typename Tint>
PackedStringArray to_godot_type_arr(cstr_t *p_from, Tint p_count) {
    PackedStringArray ret;
    ret.resize(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret[i] = to_godot_type<cstr_t, String>(p_from[i]);
    }
    return ret;
}

template <typename Tint>
cstr_t *to_eos_type_arr(const PackedStringArray &p_from, Tint &r_count) {
    cstr_t *ret = nullptr;
    if (p_from.size()) {
        ret = (cstr_t *)memalloc(sizeof(cstr_t) * p_from.size());
        for (int i = 0; i < p_from.size(); i++) {
            ret[i] = VARIANT_TO_CHARSTRING(p_from[i]).get_data();
        }
    }
    r_count = p_from.size();
    return ret;
}

// const cstr_t*
template <typename Tint>
PackedStringArray to_godot_type_arr(const cstr_t *p_from, Tint p_count) {
    return to_godot_type_arr(p_from, p_count);
}

template <typename Tint>
const cstr_t *to_eos_type_arr(const PackedStringArray &p_from, Tint &r_count) {
    return to_eos_type_arr(p_from, r_count);
}

// int16_t*
template <typename Tint>
PackedInt32Array to_godot_type_arr(int16_t *p_from, Tint p_count) {
    PackedInt32Array ret;
    ret.resize(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret[i] = p_from[i];
    }
    return ret;
}

template <typename Tint>
int16_t *to_eos_type_arr(const PackedInt32Array &p_from, Tint &r_count) {
    int16_t *ret = nullptr;
    if (p_from.size()) {
        ret = (int16_t *)memalloc(sizeof(int16_t) * p_from.size());
        for (int i = 0; i < p_from.size(); i++) {
            ret[i] = p_from[i];
        }
    }
    r_count = p_from.size();
    return ret;
}

// const int16_t*
template <typename Tint>
PackedInt32Array to_godot_type_arr(const int16_t *p_from, Tint p_count) {
    return to_godot_type_arr(p_from, p_count);
}

template <typename Tint>
const int16_t *to_eos_type_arr(const PackedStringArray &p_from, Tint &r_count) {
    return to_eos_type_arr(p_from, r_count);
}

// uint8_t*
template <typename Tint>
PackedInt32Array to_godot_type_arr(uint8_t *p_from, Tint p_count) {
    PackedInt32Array ret;
    ret.resize(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret[i] = p_from[i];
    }
    return ret;
}

template <typename Tint>
uint8_t *to_eos_type_arr(const PackedInt32Array &p_from, Tint &r_count) {
    uint8_t *ret = nullptr;
    if (p_from.size()) {
        ret = (uint8_t *)memalloc(sizeof(uint8_t) * p_from.size());
        for (int i = 0; i < p_from.size(); i++) {
            ret[i] = p_from[i];
        }
    }
    r_count = p_from.size();
    return ret;
}

// uint32_t*
template <typename Tint>
PackedInt64Array to_godot_type_arr(uint32_t *p_from, Tint p_count) {
    PackedInt64Array ret;
    ret.resize(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret[i] = p_from[i];
    }
    return ret;
}

template <typename Tint>
uint32_t *to_eos_type_arr(const PackedInt64Array &p_from, Tint &r_count) {
    uint32_t *ret = nullptr;
    if (p_from.size()) {
        ret = (uint32_t *)memalloc(sizeof(uint32_t) * p_from.size());
        for (int i = 0; i < p_from.size(); i++) {
            ret[i] = p_from[i];
        }
    }
    r_count = p_from.size();
    return ret;
}

// const uint32_t*
template <typename Tint>
PackedInt64Array to_godot_type_arr(const uint32_t *p_from, Tint p_count) {
    return to_godot_type_arr(p_from, p_count);
}

template <typename Tint>
const uint32_t *to_eos_type_arr(const PackedStringArray &p_from, Tint &r_count) {
    return to_eos_type_arr(p_from, r_count);
}

// ===
// const void *
template <typename Tint>
PackedByteArray to_godot_type_arr(const void *p_from, Tint p_length) {
    PackedByteArray ret;
    ret.resize(p_length);
    memcpy(ret.ptrw(), p_from, p_length);
    return ret;
}

template <typename Tint>
const void *to_eos_type_arr(const PackedByteArray &p_from, Tint &r_count) {
    void *ret = nullptr;
    if (p_from.size()) {
        ret = (char *)memalloc(sizeof(char) * p_from.size());
        memcpy(ret, p_from.ptr(), p_from.size());
    }
    r_count = p_from.size();
    return ret;
}

static const uint8_t *to_eos_requested_channel(uint16_t p_channel) {
    if (p_channel < 0) {
        return nullptr;
    }
    ERR_FAIL_COND_V(p_channel > UINT8_MAX, nullptr);

    static LocalVector<uint8_t> channels;
    auto idx = channels.find(p_channel);
    if (idx < 0) {
        channels.push_back(p_channel);
        idx = channels.size() - 1;
    }
    return channels.ptr() + idx;
}

// Hack
using eos_p2p_socketid_socked_name_t = char[EOS_P2P_SOCKETID_SOCKETNAME_SIZE];
template <>
String to_godot_type(const eos_p2p_socketid_socked_name_t &p_from) { return p_from; }

template <>
EOS_AntiCheatCommon_Vec3f to_eos_type(const Vector3 &p_from) {
    return { p_from.x, p_from.y, p_from.z };
}
template <>
EOS_AntiCheatCommon_Quat to_eos_type(const Quaternion &p_from) {
    return { p_from.w, p_from.x, p_from.y, p_from.z };
}

// For code generator
#define _DECLTYPE_GODOT_ARG_TYPE(m_field) gd_arg_t<decltype(m_field)>

template <typename RefOut, typename In, typename InArg = std::conditional_t<std::is_pointer_v<In>, In, In &>, typename Out = std::remove_pointer_t<decltype(RefOut().ptr())>>
inline RefOut to_godot_data(InArg p_in) {
    if constexpr (std::is_pointer_v<InArg>) {
        return Out::from_eos(*p_in);
    } else {
        return Out::from_eos(p_in);
    }
}

template <typename RefEOSData, typename Out, typename OutT = std::remove_const_t<Out>>
inline void to_eos_data(const RefEOSData &p_in, OutT &r_out) {
    if constexpr (std::is_pointer_v<Out>) {
        static_assert(false, "让我看看!");
        r_out = *p_in->get_eos_data();
    } else {
        p_in->set_to_eos(r_out);
    }
}

template <typename EOSUnion, typename UnionType>
inline void variant_to_eos_union(const Variant &p_gd, EOSUnion &p_union, UnionType &r_union_type) {
    if constexpr (std::is_same_v<UnionType, EOS_EAntiCheatCommonEventParamType>) {
        switch (p_gd.get_type()) {
            case Variant::OBJECT: {
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_ClientHandle;
                p_union->ClientHandle = Object::cast_to<Object>(p_gd); // (EOSAntiCheatCommon_Client *)
            } break;
            case Variant::INT: {
                p_union->Int64 = p_gd;
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Int64;
            } break;
            case Variant::STRING:
            case Variant::STRING_NAME:
            case Variant::NODE_PATH: {
                p_union->String = VARIANT_TO_CHARSTRING(p_gd).get_data();
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_String;
            } break;
            case Variant::VECTOR3:
            case Variant::VECTOR3I: {
                p_union->Vec3f = to_eos_type((Vetor3(p_gd)));
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Vector3f;
            } break;
            case Variant::QUATERNION: {
                p_union->Quat = to_eos_type((Quaternion(p_gd)));
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Quat;
            } break;
            default: {
                assert(false, "Unsupport");
            } break;
        }
    } else if constexpr (std::is_same_v<UnionType, EOS_EAttributeType>) {
        switch (p_gd.get_type()) {
            case Variant::INT: {
                p_union->AsInt64 = p_gd;
                r_union_type = EOS_EAttributeType::EOS_AT_INT64;
            } break;
            case Variant::FLOAT: {
                p_union->AsDouble = p_gd;
                r_union_type = EOS_EAttributeType::EOS_AT_DOUBLE;

            } break;
            case Variant::BOOL: {
                p_union->AsBool = p_gd;
                r_union_type = EOS_EAttributeType::EOS_AT_BOOLEAN;

            } break;
            case Variant::STRING:
            case Variant::STRING_NAME:
            case Variant::NODE_PATH: {
                p_union->AsUtf8 = VARIANT_TO_CHARSTRING(p_gd).get_data();
                r_union_type = EOS_EAttributeType::EOS_AT_STRING;
            } break;
            default: {
                assert(false, "Unsupport");
            } break;
        }
    } else {
        static_assert(false, "Unsupport union type");
    }
}

template <typename EOSUnion, typename UnionType>
inline Variant eos_union_to_variant(const EOSUnion &p_union, UnionType p_union_type) {
    if constexpr (std::is_same_v<UnionType, EOS_EAntiCheatCommonEventParamType>) {
        switch (p_union_type) {
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_ClientHandle: {
                return Object::cast_to<Object>(p_union->ClientHandle); // (EOSAntiCheatCommon_Client *)
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Int32: {
                return p_union.UInt32;
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Int32: {
                return p_union.Int32;
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_UInt64: {
                return p_union.UInt64;
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Int64: {
                return p_union.Int64;
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_String: {
                return p_union.String;
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Vector3f: {
                return Vector3{ p_union.Vec3f.x, p_union.Vec3f.y, p_union.Vec3f.z };
            } break;
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Quat: {
                return Quaternion{ p_union.Quat.x, p_union.Quat.y, p_union.Quat.z, p_union.Quat.w };
            } break;
        }
    } else if constexpr (std::is_same_v<UnionType, EOS_EAttributeType>) {
        switch (p_union_type) {
            case EOS_EAttributeType::EOS_AT_INT64: {
                return p_union->AsInt64;
            } break;
            case EOS_EAttributeType::EOS_AT_DOUBLE: {
                return p_union->AsDouble;
            } break;
            case EOS_EAttributeType::EOS_AT_BOOLEAN: {
                return p_union->AsBool;
            } break;
            case EOS_EAttributeType::EOS_AT_STRING: {
                return String::utf8(p_union->AsUtf8);
            } break;
        }
    } else {
        static_assert(false, "Unsupport union type");
    }
}

template <typename EOSUnion>
inline void string_to_eos_union_account_id(const String &p_gd, EOSUnion &p_union, EOS_EMetricsAccountIdType p_union_type) {
    if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_Epic) {
        p_union.Epic = eosg_string_to_epic_account_id(VARIANT_TO_CHARSTRING(p_gd).get_data());
    } else if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_External) {
        p_union.External = VARIANT_TO_CHARSTRING(p_gd).get_data();
    }
}
template <typename EOSUnion>
inline String eos_union_account_id_to_string(const EOSUnion &p_union, EOS_EMetricsAccountIdType p_union_type) {
    if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_Epic) {
        return eosg_epic_account_id_to_string(p_union.Epic);
    } else if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_External) {
        return String::utf8(p_union.External);
    }
}

#define _FROM_EOS_FIELD(gd_field, eos_field) \
    gd_field = to_godot_type<decltype(eos_field), decltype(gd_field)>(eos_field)
#define _FROM_EOS_FIELD_ARR(gd_field, eos_field, eos_field_count) \
    gd_field = to_godot_type_arr<decltype(eos_field), decltype(gd_field)>(eos_field, eos_field_count)
#define _FROM_EOS_FIELD_CLIENT_DATA(gd_field, eos_field) \
    gd_field = ((_CallbackClientData *)eos_field)->client_data
#define _FROM_EOS_FIELD_STRUCT(gd_field, eos_field) \
    gd_field = to_godot_data<decltype(gd_field)>(eos_field)
#define _FROM_EOS_FIELD_STRUCT_ARR(gd_data_type, gd_field, eos_field, eos_filed_count) \
    gd_field.resize(eos_filed_count);                                                  \
    for (decltype(eos_filed_count) i = 0; i < eos_filed_count; ++i) {                  \
        gd_field[i] = to_godot_data<gd_data_type>(eos_field[i]);                       \
    }
#define _FROM_EOS_FIELD_HANDLER(gd_field, eos_field) \
    gd_field->set_handle(eps_field)
#define _FROM_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE(gd_field, eos_field) \
    gd_field = (decltype(gd_field))eos_field
#define _FROM_EOS_FIELD_REQUESTED_CHANNEL(gd_field, eos_field) \
    static_assert(false, "不该发生")
#define _FROM_EOS_FIELD_UNION(gd_field, eos_field)                                        \
    if constexpr (std::is_same_v<EOS_EMetricsAccountIdType, decltype(eos_field##Type)>) { \
        gd_field = eos_union_account_id_to_string(eos_field, eos_field##Type);            \
        gd_field##_type = eos_field##Type;                                                \
    } else {                                                                              \
        gd_field = eos_union_to_variant(eos_field, eos_field##Type);                      \
    }

#define _TO_EOS_FIELD(eos_field, gd_field) \
    eos_field = to_eos_type<_DECLTYPE_GODOT_ARG_TYPE(gd_field), decltype(eos_field)>(gd_field)
#define _TO_EOS_FIELD_ARR(eos_field, gd_field, r_eos_field_count) \
    eos_field = to_eos_type_arr<_DECLTYPE_GODOT_ARG_TYPE(gd_field), decltype(eos_field)>(gd_field, r_eos_field_count)
#define _TO_EOS_FIELD_CLIENT_DATA(eos_field, gd_field) \
    static_assert(false, "不应该发生")
#define _TO_EOS_FIELD_STRUCT(eos_field, gd_field) \
    to_eos_data<decltype(gd_field), decltype(eos_field)>(gd_field, eos_field)
#define _TO_EOS_FIELD_STRUCT_ARR(gd_data_type, eos_field, gd_field, r_eos_field_count)           \
    r_eos_field_count = gd_field.size();                                                         \
    if (r_eos_field_count) {                                                                     \
        using _ #gd_data_type = std::remove_const_v<std::remove_pointer_t<decltype(eos_field)>>; \
        eos_field = memalloc(sizeof(_ #gd_data_type) * r_eos_field_count);                       \
        for (decltype(r_eos_field_count) i = 0; i < r_eos_field_count; ++i) {                    \
            Object::cast_to<gd_data_type>(gd_field[0])->set_to_eos(eos_field[0]);                \
        }                                                                                        \
    } else {                                                                                     \
        eos_field = nullptr;                                                                     \
    }
#define _TO_EOS_FIELD_HANDLER(eos_field, gd_field) \
    eos_field = gd_field.is_valid ? gd_field->get_handle() : nullptr
#define _TO_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE(eos_field, gd_field) \
    eos_field = (void *)gd_field
#define _TO_EOS_FIELD_REQUESTED_CHANNEL(eos_field, gd_field) \
    eos_field = to_eos_requested_channel(gd_field)
#define _TO_EOS_FIELD_UNION(eos_field, gd_field)                                          \
    if constexpr (std::is_same_v<EOS_EMetricsAccountIdType, decltype(eos_field##Type)>) { \
        string_to_eos_union_account_id(gd_field, eos_field, gd_field##_type);             \
        eos_field##Type = gd_field##_type;                                                \
    } else {                                                                              \
        variant_to_eos_union(gd_field, eos_field, eos_field##Type);                       \
    }

// 绑定
#define _MAKE_PROP_INFO(m_class, m_name) PropertyInfo(Variant::OBJECT, #m_name, {}, "", PROPERTY_USAGE_DEFAULT, m_class::get_class_static())

// 展开转换
template <typename GDDataClass, typename EOSArraTy, typename TInt>
godot::TypedArray<GDDataClass> _to_godot_value_struct_arr(EOSArraTy p_eos_arr, TInt p_count) {
    godot::TypedArray<GDDataClass> ret;
    ret.resize(p_count);
    for (decltype(p_count) i = 0; i < p_count; ++i) {
        ret[i] = to_godot_data<GDDataClass>(p_eos_arr[i]);
    }
    return ret;
}

template <typename GDHandle, typename EOSHandle>
godot::Ref<GDHandle> _to_godot_handle(EOSHandle p_eos_handle) {
    godot::Ref<GDHandle> ret;
    ret.instantiate();
    ret->set_handle(p_eos_handle);
    return ret;
}

template <typename EOSUnion, typename EOSUnionTypeEnum>
auto _to_godot_val_from_union(EOSUnion &p_eos_union, EOSUnionTypeEnum p_type) {
    if constexpr (std::is_same_v<EOS_EMetricsAccountIdType, EOSUnionTypeEnum>) {
        return eos_union_account_id_to_string(p_eos_union, p_type);
    } else {
        return eos_union_to_variant(p_eos_union, p_type);
    }
}

#define _EXPAND_TO_GODOT_VAL(m_gd_Ty, eos_field) to_godot_type<decltype(data->(eos_field)), m_gd_Ty>(data->(eos_field))
#define _EXPAND_TO_GODOT_VAL_ARR(m_gd_Ty, eos_field, eos_field_count) to_godot_type_arr<decltype(data->(eos_field)), m_gd_Ty>(data->(eos_field), data->(eos_field_count))
#define _EXPAND_TO_GODOT_VAL_CLIENT_DATA(m_gd_Ty, eos_field) ((_CallbackClientData *)eos_field)->client_data
#define _EXPAND_TO_GODOT_VAL_STRUCT(m_gd_Ty, eos_field) to_godot_data<m_gd_Ty>(data->eos_field)
#define _EXPAND_TO_GODOT_VAL_STRUCT_ARR(m_gd_Ty, eos_field, eos_filed_count) _to_godot_value_struct_arr<m_gd_Ty, decltype(data->(eos_field)), decltype(data->(eso_field_count))>(data->(eos_field), data->(eos_filed_count))
#define _EXPAND_TO_GODOT_VAL_HANDLER(m_gd_Ty, eos_field) _to_godot_handle<m_gd_Ty, decltype(data->(eos_field))>(data->(eos_field))
#define _EXPAND_TO_GODOT_VAL_ANTICHEAT_CLIENT_HANDLE(m_gd_Ty, eos_field) (m_gd_Ty *)(data->(eos_field))
#define _EXPAND_TO_GODOT_VAL_REQUESTED_CHANNEL(gd_field, eos_field) static_assert(false, "不该发生")
#define _EXPAND_TO_GODOT_VAL_UNION(m_gd_Ty, eos_field) _to_godot_val_from_union(data->(eos_field), data->(eos_field##Type))

// 回调
#define _EOS_METHOD_CALLBACK(m_callbak_info_ty, m_callback_signal, m_arg_type)  \
    [](m_callbak_info_ty data) {                                                \
        auto cd = _CallbackClientData::cast_to_scoped(data->ClientData);        \
        auto cb_data = m_arg_type::from_eos(data);                              \
        if (cd.get_completion_callback().is_valid()) {                          \
            cd.get_completion_callback().call(cb_data);                         \
        }                                                                       \
        cd->get_handle_wrapper->emit_signal(SNAME(m_callback_signal), cb_data); \
    }

#define _EOS_METHOD_CALLBACK_EXPANDED(m_callbak_info_ty, m_callback_signal, ...)      \
    [](m_callbak_info_ty data) {                                                      \
        auto cd = _CallbackClientData::cast_to_scoped(data->ClientData);              \
        if (cd.get_completion_callback().is_valid()) {                                \
            cd.get_completion_callback().call(__VA_ARGS__);                           \
        }                                                                             \
        cd->get_handle_wrapper->emit_signal(SNAME(m_callback_signal), ##__VA_ARGS__); \
    }

// TODO: EOS_IntegratedPlatform_SetUserPreLogoutCallback 需要配合 方法生成 特殊处理
// 有返回值回调返回默认值时不会释放
#define _EOS_METHOD_CALLBACK_RET(m_ret_ty, m_default_ret, m_callbak_info_ty, m_callback_signal, m_arg_type) \
    [](m_callbak_info_ty data) {                                                                            \
        auto cd = (_CallbackClientData *)data->ClientData;                                                  \
        auto cb_data = m_arg_type::from_eos(data);                                                          \
        m_default_ret ret = m_default_ret;                                                                  \
        if (cd->completion_callback.is_valid()) {                                                           \
            auto res = cd->completion_callback.call(cb_data);                                               \
            if (ret.get_type() == Variant::INT) {                                                           \
                ret = (m_default_ret)res;                                                                   \
            } else if (ret.get_type() != Variant::NIL) {                                                    \
                ERR_PRINT(vformat("The callback return type must be \"%s\"", #m_ret_ty));                   \
            }                                                                                               \
        }                                                                                                   \
        cd->get_handle_wrapper->emit_signal(SNAME(m_callback_signal), cb_data);                             \
        if (ret != m_default_ret) {                                                                         \
            memdelete((_CallbackClientData *)data->ClientData);                                             \
        }                                                                                                   \
        return ret;                                                                                         \
    }

#define _EOS_METHOD_CALLBACK_EXPANDED_RET(m_ret_ty, m_default_ret, m_callbak_info_ty, m_callback_signal, ...) \
    [](m_callbak_info_ty data) {                                                                              \
        auto cd = _CallbackClientData::cast_to_scoped(data->ClientData);                                      \
        m_default_ret ret = m_default_ret;                                                                    \
        if (cd.get_completion_callback().is_valid()) {                                                        \
            auto res = cd.get_completion_callback().call(##__VA_ARGS__);                                      \
            if (ret.get_type() == Variant::INT) {                                                             \
                ret = (m_default_ret)res;                                                                     \
            } else if (ret.get_type() != Variant::NIL) {                                                      \
                ERR_PRINT(vformat("The callback return type must be \"%s\"", #m_ret_ty));                     \
            }                                                                                                 \
        }                                                                                                     \
        cd->get_handle_wrapper->emit_signal(SNAME(m_callback_signal), ##__VA_ARGS__);                         \
        if (ret != m_default_ret) {                                                                           \
            memdelete((_CallbackClientData *)data->ClientData);                                               \
        }                                                                                                     \
        return ret;                                                                                           \
    }

#define _EOS_OPTIONS_PTR_IDENTIFY(m_options_ty) m_options_ty##_options_ptr
// 参数
#define _EOS_METHOD_OPTIONS(m_gd_option, m_options_ty) \
    m_options_ty *_EOS_OPTIONS_PTR_IDENTIFY(m_options_ty) = &(m_gd_option->to_eos_data());

#define _EOS_OPTIONS_IDENTIFY(m_options_ty) m_options_ty##_option
#define _EOS_METHOD_OPTIONS_INTEGRATE(m_options_ty, m_api_version...) \
    m_options_ty _EOS_OPTIONS_IDENTIFY(m_options_ty);                 \
    _EOS_OPTIONS_IDENTIFY(m_options_ty)->ApiVersion = m_api_version;  \
    (##__VA_ARGS__);                                                  \
    m_options_ty *_EOS_OPTIONS_PTR_IDENTIFY(m_options_ty) = &_EOS_OPTIONS_IDENTIFY(m_options_ty);

// For string out parameters.
class StrResult : public RefCounted {
    GDCLASS(StrResult, RefCounted)
    EOS_EResult result_code;
    String result;

public:
    _DEFINE_SETGET(result_code);
    _DEFINE_SETGET(result);

    StrResult() = default;
    StrResult(EOS_EResult p_result_code, char *p_result, uint32_t p_length = -1) :
            result_code(p_result_code), result(String::utf8(p_result, p_length)) {}

protected:
    static void _bind_methods() {
        _BIND_BEGIN(StrResult);
        _BIND_PROP(result_code);
        _BIND_PROP(result);
        _BIND_END();
    }
};

#define _DEFINE_INOUT_STR_ARGUMENTS(m_max_length, length_int_type) \
    char *out_str = (char *)memalloc(m_max_length);                \
    length_int_type out_length = 0
#define _INPUT_STR_ARGUMENTS_FOR_CALL() out_str, out_length
#define _MAKE_STR_RESULT(m_result_code) Ref<StrResult>(memnew(StrResult(m_result_code, out_str, out_length)))

} // namespace godot

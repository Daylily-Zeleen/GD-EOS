#pragma once

#include <eos_sdk.h>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/templates/local_vector.hpp>
#include <godot_cpp/variant/variant.hpp>

namespace godot::eos {

#define ENABLE_IF(condition) std::enable_if_t<condition> *_dummy = nullptr

template <typename T>
using gd_arg_t = std::conditional_t<!std::is_trivial_v<T> || (sizeof(T) > 8), const T &, T>;

#define _ARG_TYPE(arg) eos::gd_arg_t<decltype(arg)>
} //namespace godot::eos

namespace godot::eos::internal {

#define _EOS_VERSION_GREATER_THAN_1_6_1 (EOS_MAJOR_VERSION > 1 || (EOS_MAJOR_VERSION == 1 && EOS_MINOR_VERSION > 16) || (EOS_MAJOR_VERSION == 1 && EOS_MINOR_VERSION == 16 && EOS_PATCH_VERSION > 1))

#define _BIND_ENUM_CONSTANT(enume_type_name, e, e_bind) \
    ClassDB::bind_integer_constant(get_class_static(), godot::_gde_constant_get_enum_name<enume_type_name>(enume_type_name::e, e_bind), e_bind, enume_type_name::e)

#define SNAME(sn) []() -> const StringName & {static const StringName ret{sn};return ret; }()

#define VARIANT_TO_CHARSTRING(str) ((String)str).utf8()
#ifdef _MSC_VER // Check if using Microsoft Visual Studio
#define STRNCPY_S(dest, destsz, src, count) strncpy_s(dest, destsz, src, count)
#else
#define STRNCPY_S(dest, destsz, src, count) strncpy(dest, src, count)
#endif

String epic_account_id_to_string(const EOS_EpicAccountId accountId);

static EOS_EpicAccountId string_to_epic_account_id(const char *p_account_id) {
    EOS_EpicAccountId accountId = EOS_EpicAccountId_FromString(p_account_id);
    return accountId;
}

String product_user_id_to_string(const EOS_ProductUserId localUserId);

static EOS_ProductUserId string_to_product_user_id(const char *p_account_id) {
    EOS_ProductUserId accountId = EOS_ProductUserId_FromString(p_account_id);
    return accountId;
}

#define _DECLARE_SETGET(field)           \
    decltype(field) get_##field() const; \
    void set_##field(_ARG_TYPE(field) p_val);

#define _DEFINE_SETGET(klass, field)                                    \
    decltype(klass::field) klass::get_##field() const { return field; } \
    void klass::set_##field(_ARG_TYPE(field) p_val) { field = p_val; }

#define _DECLARE_SETGET_STR(field) \
    String get_##field() const;    \
    void set_##field(const String &p_val);

#define _DEFINE_SETGET_STR(klass, field)                                                 \
    String klass::get_##field() const { return String::utf8((char *)field.get_data()); } \
    void klass::set_##field(const String &p_val) { field = p_val.utf8(); }

#define _DECLARE_SETGET_STR_ARR(field)     \
    PackedStringArray get_##field() const; \
    void set_##field(const PackedStringArray &p_val);

#define _DEFINE_SETGET_STR_ARR(klass, field)                            \
    PackedStringArray klass::get_##field() const {                      \
        PackedStringArray ret;                                          \
        for (const CharString &str_buffer : field) {                    \
            ret.push_back(String::utf8((char *)str_buffer.get_data())); \
        }                                                               \
        return ret;                                                     \
    }                                                                   \
    void klass::set_##field(const PackedStringArray &p_val) {           \
        field.clear();                                                  \
        for (const String &str : p_val) {                               \
            field.push_back(str.utf8());                                \
        }                                                               \
    }

#define _DECLARE_SETGET_STRUCT_PTR(gd_type, field) \
    gd_type get_##field() const;                   \
    void set_##field(const gd_type &p_val);

#define _DEFINE_SETGET_STRUCT_PTR(klass, gd_type, field)                                                  \
    gd_type klass::get_##field() const { return to_godot_type<const decltype(field) &, gd_type>(field); } \
    void klass::set_##field(const gd_type &p_val) { field = to_eos_type<const gd_type &, decltype(field)>(p_val); }

#define _DECLARE_SETGET_TYPED(field, type) \
    type get_##field() const;              \
    void set_##field(eos::gd_arg_t<type> p_val);

#define _DEFINE_SETGET_TYPED(klass, field, type)      \
    type klass::get_##field() const { return field; } \
    void klass::set_##field(eos::gd_arg_t<type> p_val) { field = p_val; }

#define _DECLARE_SETGET_BOOL(field)     \
    decltype(field) is_##field() const; \
    void set_##field(_ARG_TYPE(field) p_val);

#define _DEFINE_SETGET_BOOL(klass, field)            \
    bool klass::is_##field() const { return field; } \
    void klass::set_##field(_ARG_TYPE(field) p_val) { field = p_val; }

#define _BIND_BEGIN(klass) using _BINDING_CLASS = klass;

#define _BIND_PROP(field)                                                               \
    ClassDB::bind_method(D_METHOD("get_" #field), &_BINDING_CLASS::get_##field);        \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant(decltype(_BINDING_CLASS::field){}).get_type(), #field), "set_" #field, "get_" #field);

#define _BIND_PROP_STRUCT_PTR(field, struct_ty)                                         \
    ClassDB::bind_method(D_METHOD("get_" #field), &_BINDING_CLASS::get_##field);        \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant(struct_ty()).get_type(), #field),                 \
            "set_" #field, "get_" #field);

#define _BIND_PROP_STR(field)                                                           \
    ClassDB::bind_method(D_METHOD("get_" #field), &_BINDING_CLASS::get_##field);        \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant::STRING, #field),                                 \
            "set_" #field, "get_" #field);

#define _BIND_PROP_STR_ARR(field)                                                       \
    ClassDB::bind_method(D_METHOD("get_" #field), &_BINDING_CLASS::get_##field);        \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant::PACKED_STRING_ARRAY, #field),                    \
            "set_" #field, "get_" #field);

#define _BIND_PROP_OBJ(field, obj_ty)                                                                  \
    ClassDB::bind_method(D_METHOD("get_" #field), &_BINDING_CLASS::get_##field);                       \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field);                \
    ADD_PROPERTY(PropertyInfo(Variant::OBJECT, #field, PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT, \
                         obj_ty::get_class_static()),                                                  \
            "set_" #field, "get_" #field);

#define _BIND_PROP_ENUM(field, enum_owner, enum_type)                                               \
    ClassDB::bind_method(D_METHOD("get_" #field), &_BINDING_CLASS::get_##field);                    \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field);             \
    ADD_PROPERTY(PropertyInfo(Variant::INT, #field, PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT, \
                         #enum_owner "." #enum_type),                                               \
            "set_" #field, "get_" #field);

#define _BIND_PROP_BOOL(field)                                                          \
    ClassDB::bind_method(D_METHOD("is_" #field), &_BINDING_CLASS::is_##field);          \
    ClassDB::bind_method(D_METHOD("set_" #field, "val"), &_BINDING_CLASS::set_##field); \
    ADD_PROPERTY(PropertyInfo(Variant::BOOL, #field), "set_" #field, "is_" #field);
#define _BIND_END()

// =====================
// ClientData
struct _CallbackClientData {
    Variant client_data;
    Object *handle_wrapper;
    Callable callback;

    _CallbackClientData(Object *p_handle_wrapper, const Variant &p_client_data, const Callable &p_callback = {}) :
            handle_wrapper(p_handle_wrapper), client_data(p_client_data), callback(p_callback) {}

    static auto cast_to_scoped(void *p_client_data) {
        struct ScopedObject {
        private:
            _CallbackClientData *ccd;

        public:
            Variant &get_client_data() const { return ccd->client_data; }
            Object *get_handle_wrapper() const { return ccd->handle_wrapper; }
            Callable &get_callback() const { return ccd->callback; }

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

// EOS_Bool
template <>
bool to_godot_type(EOS_Bool p_from) { return p_from; }
template <>
EOS_Bool to_eos_type(bool p_from) { return p_from; }

using cstr_t = const char *;
// EOS_ProductUserId
template <>
String to_godot_type(const EOS_ProductUserId p_from) { return product_user_id_to_string(p_from); }
template <>
CharString to_godot_type(const EOS_ProductUserId p_from) { return product_user_id_to_string(p_from).utf8(); }
template <>
EOS_ProductUserId to_eos_type(const CharString &p_from) { return EOS_ProductUserId_FromString((char *)p_from.get_data()); }
template <>
const EOS_ProductUserId to_eos_type(const CharString &p_from) { return to_eos_type<const CharString &, EOS_ProductUserId>(p_from); }
template <>
EOS_ProductUserId to_eos_type(cstr_t p_from) { return EOS_ProductUserId_FromString(p_from); }
template <>
const EOS_ProductUserId to_eos_type(cstr_t p_from) { return to_eos_type<cstr_t, EOS_ProductUserId>(p_from); }

// EOS_EpicAccountId
template <>
String to_godot_type(const EOS_EpicAccountId p_from) { return epic_account_id_to_string(p_from); }
template <>
CharString to_godot_type(const EOS_EpicAccountId p_from) { return epic_account_id_to_string(p_from).utf8(); }
template <>
EOS_EpicAccountId to_eos_type(const CharString &p_from) { return EOS_EpicAccountId_FromString((char *)p_from.get_data()); }
template <>
const EOS_EpicAccountId to_eos_type(const CharString &p_from) { return to_eos_type<const CharString &, EOS_EpicAccountId>(p_from); }
template <>
EOS_EpicAccountId to_eos_type(cstr_t p_from) { return EOS_EpicAccountId_FromString(p_from); }
template <>
const EOS_EpicAccountId to_eos_type(cstr_t p_from) { return to_eos_type<cstr_t, EOS_EpicAccountId>(p_from); }

// const char *
template <>
String to_godot_type(const cstr_t p_from) { return String::utf8(p_from); }
template <>
CharString to_godot_type(const cstr_t p_from) { return { p_from }; }
template <>
cstr_t to_eos_type<const CharString &, cstr_t>(const CharString &p_from) {
    return p_from.size() == 1 ? nullptr : (char *)p_from.ptr();
}
template <>
cstr_t to_eos_type<CharString, cstr_t>(CharString p_from) {
    return to_eos_type<const CharString &, cstr_t>((const CharString &)p_from);
}

// cstr_t*
template <typename Tint>
LocalVector<CharString> to_godot_type_arr(const cstr_t *p_from, Tint p_count) {
    LocalVector<CharString> ret;
    ret.reserve(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret.push_back(to_godot_type<cstr_t, CharString>(p_from[i]));
    }
    return ret;
}

template <typename Tint>
cstr_t *to_eos_type_arr(const LocalVector<CharString> &p_from, Tint &r_count) {
    cstr_t *ret = (p_from.size()) ? (cstr_t *)p_from.ptr() : nullptr;
    r_count = p_from.size();
    return ret;
}

// const cstr_t*
template <typename Tint>
LocalVector<CharString> to_godot_type_arr(cstr_t *p_from, Tint p_count) {
    return to_godot_type_arr((const cstr_t *)p_from, p_count);
}

// cstr_t*
template <typename Tint>
LocalVector<CharString> to_godot_type_arr(const EOS_ProductUserId *p_from, Tint p_count) {
    LocalVector<CharString> ret;
    ret.resize(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret[i] = to_godot_type<EOS_ProductUserId, CharString>(p_from[i]);
    }
    return ret;
}

template <typename Tint>
LocalVector<CharString> to_godot_type_arr(EOS_ProductUserId *p_from, Tint p_count) {
    return to_godot_type_arr((const EOS_ProductUserId *)p_from, p_count);
}

// int16_t*
template <typename Tint>
PackedInt32Array to_godot_type_arr(const int16_t *p_from, Tint p_count) {
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
PackedInt32Array to_godot_type_arr(int16_t *p_from, Tint p_count) {
    return to_godot_type_arr((const int16_t *)p_from, p_count);
}

// uint8_t*
template <typename Tint>
PackedInt32Array to_godot_type_arr(const uint8_t *p_from, Tint p_count) {
    PackedInt32Array ret;
    ret.resize(p_count);
    for (int i = 0; i < p_count; ++i) {
        ret[i] = p_from[i];
    }
    return ret;
}

// uint32_t*
template <typename Tint>
PackedInt64Array to_godot_type_arr(const uint32_t *p_from, Tint p_count) {
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
PackedInt64Array to_godot_type_arr(uint32_t *p_from, Tint p_count) {
    return to_godot_type_arr((const uint32_t *)p_from, p_count);
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
    ERR_FAIL_COND_V_MSG(p_channel > UINT8_MAX, nullptr, "Requested channel should be a uint8_t or -1.");

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
CharString to_godot_type(const eos_p2p_socketid_socked_name_t &p_from) {
    // 长度限制？
    return CharString(&p_from[0]);
}
template <>
String to_godot_type(const eos_p2p_socketid_socked_name_t &p_from) {
    return String(&p_from[0]);
}

template <typename From, typename To>
inline void to_eos_type_out(gd_arg_t<From> p_from, To &r_to) {
    r_to = to_eos_type<gd_arg_t<From>, To>(p_from);
}

template <>
inline void to_eos_type_out<const CharString &, eos_p2p_socketid_socked_name_t>(const CharString &p_from, eos_p2p_socketid_socked_name_t &r_to) {
    if ((p_from.size() == 33 && p_from[32] != 0) || p_from.size() > 33) {
        WARN_PRINT(vformat("EOS: Socket name \"%s\"'s length is greater than 32, will be truncatured.", String(p_from)));
    }
    memset(&r_to[0], 0, EOS_P2P_SOCKETID_SOCKETNAME_SIZE);
    memcpy(&r_to[0], p_from.ptr(), MIN(p_from.size(), EOS_P2P_SOCKETID_SOCKETNAME_SIZE - 1));
}
template <>
inline void to_eos_type_out<CharString, eos_p2p_socketid_socked_name_t>(const CharString &p_from, eos_p2p_socketid_socked_name_t &r_to) {
    to_eos_type_out<const CharString &, eos_p2p_socketid_socked_name_t>(p_from, r_to);
}

template <>
inline void to_eos_type_out<const String &, eos_p2p_socketid_socked_name_t>(const String &p_from, eos_p2p_socketid_socked_name_t &r_to) {
    to_eos_type_out<const CharString &, eos_p2p_socketid_socked_name_t>(p_from.utf8(), r_to);
}

template <>
EOS_AntiCheatCommon_Vec3f to_eos_type(const Vector3 &p_from) {
    return { p_from.x, p_from.y, p_from.z };
}
template <>
Vector3 to_godot_type(const EOS_AntiCheatCommon_Vec3f &p_from) {
    return { p_from.x, p_from.y, p_from.z };
}

template <>
EOS_AntiCheatCommon_Quat to_eos_type(const Quaternion &p_from) {
    return { p_from.w, p_from.x, p_from.y, p_from.z };
}

template <>
Quaternion to_godot_type(const EOS_AntiCheatCommon_Quat &p_from) {
    return { p_from.x, p_from.y, p_from.z, p_from.w };
}

// template <>
// inline void to_eos_type_out<Vector3, EOS_AntiCheatCommon_Vec3f *>(const Vector3 &p_from, EOS_AntiCheatCommon_Vec3f *&r_to) {
//     static_assert(std::is_same_v<decltype(r_to), EOS_AntiCheatCommon_Vec3f *&>, "已被特殊处理，该方法不该被调用到。");
// }
// template <>
// inline void to_eos_type_out<const Vector3 &, EOS_AntiCheatCommon_Vec3f *>(const Vector3 &p_from, EOS_AntiCheatCommon_Vec3f *&r_to) {
//     static_assert(std::is_same_v<decltype(r_to), EOS_AntiCheatCommon_Vec3f *&>, "已被特殊处理，该方法不该被调用到。");
// }

// template <>
// inline void to_eos_type_out<Quaternion, EOS_AntiCheatCommon_Quat *>(const Quaternion &p_from, EOS_AntiCheatCommon_Quat *&r_to) {
//     static_assert(std::is_same_v<decltype(r_to), EOS_AntiCheatCommon_Quat *&>, "已被特殊处理，该方法不该被调用到。");
// }
// template <>
// inline void to_eos_type_out<const Quaternion &, EOS_AntiCheatCommon_Quat *>(const Quaternion &p_from, EOS_AntiCheatCommon_Quat *&r_to) {
//     static_assert(std::is_same_v<decltype(r_to), EOS_AntiCheatCommon_Quat *&>, "已被特殊处理，该方法不该被调用到。");
// }

// For code generator
#define _DECLTYPE_GODOT_ARG_TYPE(m_field) gd_arg_t<decltype(m_field)>

template <typename RefOut, typename In, typename InArg = std::conditional_t<std::is_pointer_v<In>, const In, const In &>, typename Out = std::remove_pointer_t<decltype(RefOut().ptr())>>
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
        r_out = p_in.is_valid() ? &p_in->to_eos() : nullptr;
    } else {
        if (p_in.is_valid()) {
            p_in->set_to_eos(r_out);
        } else {
            memset(&r_out, 0, sizeof(r_out));
        }
    }
}

template <typename EOSUnion, typename UnionType, std::enable_if_t<std::is_same_v<std::decay_t<UnionType>, EOS_EAntiCheatCommonEventParamType> || std::is_same_v<std::decay_t<UnionType>, EOS_EAttributeType>> *_dummy = nullptr>
inline void variant_to_eos_union(const Variant &p_gd, EOSUnion &p_union, UnionType &r_union_type, CharString &r_str_cache) {
    if constexpr (std::is_same_v<std::decay_t<UnionType>, EOS_EAntiCheatCommonEventParamType>) {
        switch (p_gd.get_type()) {
            case Variant::OBJECT: {
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_ClientHandle;
                p_union.ClientHandle = Object::cast_to<Object>(p_gd);
            } break;
            case Variant::INT: {
                p_union.Int64 = p_gd;
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Int64;
            } break;
            case Variant::STRING:
            case Variant::STRING_NAME:
            case Variant::NODE_PATH: {
                // Hack: 是否有不使用静态变量的方案
                r_str_cache = String(p_gd).utf8();
                p_union.String = r_str_cache.size() == 1 ? nullptr : r_str_cache.ptr();
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_String;
            } break;
            case Variant::VECTOR3:
            case Variant::VECTOR3I: {
                to_eos_type_out<Vector3, decltype(p_union.Vec3f)>(Vector3(p_gd), p_union.Vec3f);
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Vector3f;
            } break;
            case Variant::QUATERNION: {
                to_eos_type_out<Quaternion, decltype(p_union.Quat)>(Quaternion(p_gd), p_union.Quat);
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Quat;
            } break;
#if _EOS_VERSION_GREATER_THAN_1_6_1
            case Variant::FLOAT: {
                p_union.Float = p_gd;
                r_union_type = EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Float;
            } break;
#endif // _EOS_VERSION_GREATER_THAN_1_6_1
            default: {
                ERR_PRINT(vformat("Unsupport variant", Variant::get_type_name(p_gd.get_type())));
            } break;
        }
    } else if constexpr (std::is_same_v<std::decay_t<UnionType>, EOS_EAttributeType>) {
        switch (p_gd.get_type()) {
            case Variant::INT: {
                p_union.AsInt64 = p_gd;
                r_union_type = EOS_EAttributeType::EOS_AT_INT64;
            } break;
            case Variant::FLOAT: {
                p_union.AsDouble = p_gd;
                r_union_type = EOS_EAttributeType::EOS_AT_DOUBLE;

            } break;
            case Variant::BOOL: {
                p_union.AsBool = p_gd;
                r_union_type = EOS_EAttributeType::EOS_AT_BOOLEAN;

            } break;
            case Variant::STRING:
            case Variant::STRING_NAME:
            case Variant::NODE_PATH: {
                r_str_cache = String(p_gd).utf8();
                p_union.AsUtf8 = r_str_cache.size() == 1 ? nullptr : r_str_cache.ptr();
                r_union_type = EOS_EAttributeType::EOS_AT_STRING;
            } break;
            default: {
                ERR_PRINT(vformat("Unsupport variant", Variant::get_type_name(p_gd.get_type())));
            } break;
        }
    }
}

template <typename EOSUnion, typename UnionType, std::enable_if_t<std::is_same_v<std::decay_t<UnionType>, EOS_EAntiCheatCommonEventParamType> || std::is_same_v<std::decay_t<UnionType>, EOS_EAttributeType>> *_dummy = nullptr>
inline Variant eos_union_to_variant(const EOSUnion &p_union, UnionType p_union_type) {
    if constexpr (std::is_same_v<std::decay_t<UnionType>, EOS_EAntiCheatCommonEventParamType>) {
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
#if _EOS_VERSION_GREATER_THAN_1_6_1
            case EOS_EAntiCheatCommonEventParamType::EOS_ACCEPT_Float: {
                return p_union.Float;
            } break;
#endif // _EOS_VERSION_GREATER_THAN_1_6_1
        }
    } else if constexpr (std::is_same_v<std::decay_t<UnionType>, EOS_EAttributeType>) {
        switch (p_union_type) {
            case EOS_EAttributeType::EOS_AT_INT64: {
                return p_union.AsInt64;
            } break;
            case EOS_EAttributeType::EOS_AT_DOUBLE: {
                return p_union.AsDouble;
            } break;
            case EOS_EAttributeType::EOS_AT_BOOLEAN: {
                return p_union.AsBool != EOS_FALSE;
            } break;
            case EOS_EAttributeType::EOS_AT_STRING: {
                return String::utf8(p_union.AsUtf8);
            } break;
            default: {
                ERR_FAIL_V_MSG({}, vformat("Unsuppoert AttributeType: ", (int)p_union_type));
            } break;
        }
    }
}

template <typename EOSUnion>
inline void string_to_eos_union_account_id(const CharString &p_gd, EOSUnion &p_union, EOS_EMetricsAccountIdType p_union_type) {
    if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_Epic) {
        p_union.Epic = string_to_epic_account_id(p_gd.get_data());
    } else if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_External) {
        p_union.External = p_gd.get_data();
    }
}
template <typename EOSUnion>
inline String eos_union_account_id_to_string(const EOSUnion &p_union, EOS_EMetricsAccountIdType p_union_type) {
    if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_Epic) {
        return epic_account_id_to_string(p_union.Epic);
    } else if (p_union_type == EOS_EMetricsAccountIdType::EOS_MAIT_External) {
        return String::utf8(p_union.External);
    }
}

template <typename FromGD, typename ToUnion, typename UnionTy, std::enable_if_t<!std::is_same_v<std::decay_t<UnionTy>, EOS_EMetricsAccountIdType>> *_dummy = nullptr>
void to_eos_data_union(const FromGD &p_from, ToUnion &p_union, UnionTy &p_union_type, CharString &r_str_cache) {
    variant_to_eos_union(p_from, p_union, p_union_type, r_str_cache);
}

template <typename ToUnion>
void to_eos_data_union(const String &p_from, ToUnion &p_union, EOS_EMetricsAccountIdType p_union_type, CharString &r_str_cache) {
    r_str_cache = p_from.utf8();
    string_to_eos_union_account_id(r_str_cache, p_union, p_union_type);
}
template <typename ToUnion>
void to_eos_data_union(const CharString &p_from, ToUnion &p_union, EOS_EMetricsAccountIdType p_union_type, CharString &r_str_cache) {
    string_to_eos_union_account_id(p_from, p_union, p_union_type);
}

template <typename FromUnion, typename UnionTy, std::enable_if_t<!std::is_same_v<std::decay_t<UnionTy>, EOS_EMetricsAccountIdType>> *_dummy = nullptr>
Variant to_godot_data_union(const FromUnion &p_from, UnionTy p_union_type) {
    return eos_union_to_variant(p_from, p_union_type);
}

template <typename FromUnion>
String to_godot_data_union(const FromUnion &p_from, EOS_EMetricsAccountIdType p_union_type) {
    return eos_union_account_id_to_string(p_from, p_union_type);
}

#define _FROM_EOS_FIELD(gd_field, eos_field) \
    gd_field = to_godot_type<std::conditional_t<std::is_same_v<decltype(eos_field), eos_p2p_socketid_socked_name_t>, const eos_p2p_socketid_socked_name_t &, decltype(eos_field)>, decltype(gd_field)>(eos_field)
#define _FROM_EOS_FIELD_ARR(gd_field, eos_field, eos_field_count) \
    gd_field = to_godot_type_arr(eos_field, eos_field_count)
#define _FROM_EOS_STR_ARR(gd_field, eos_field, eos_field_count)                                 \
    gd_field.clear();                                                                           \
    for (decltype(eos_field_count) i = 0; i < eos_field_count; ++i) {                           \
        using eos_str_t = std::remove_const_t<std::remove_reference_t<decltype(eos_field[0])>>; \
        gd_field.push_back(to_godot_type<eos_str_t, CharString>(eos_field[i]));                 \
    }
#define _FROM_EOS_FIELD_CLIENT_DATA(gd_field, eos_field) \
    gd_field = ((_CallbackClientData *)eos_field)->client_data
#define _FROM_EOS_FIELD_STRUCT(gd_field, eos_field) \
    if (!eos_field) {                               \
        gd_field.unref();                           \
    } else {                                        \
        if (gd_field.is_null()) {                   \
            gd_field.instantiate();                 \
        }                                           \
        gd_field->set_from_eos(*eos_field);         \
    }
// gd_field = to_godot_data<decltype(gd_field), decltype(eos_field)>(eos_field);

#define _FROM_EOS_FIELD_STRUCT_ARR(gd_data_type, gd_field, eos_field, eos_filed_count) \
    gd_field.resize(eos_filed_count);                                                  \
    for (decltype(eos_filed_count) i = 0; i < eos_filed_count; ++i) {                  \
        gd_field[i] = gd_data_type::from_eos(eos_field[i]);                            \
    }
#define _FROM_EOS_FIELD_HANDLER(gd_field, gd_type_to_cast, eos_field) \
    if (gd_field.is_null()) {                                         \
        gd_field.reference_ptr(memnew(gd_type_to_cast));              \
    }                                                                 \
    Object::cast_to<gd_type_to_cast>(gd_field.ptr())->set_handle(eos_field)
#define _FROM_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE(gd_field, eos_field) \
    gd_field = (decltype(gd_field))eos_field
#define _FROM_EOS_FIELD_REQUESTED_CHANNEL(gd_field, eos_field) \
    static_assert(false, "不该发生")
#define _FROM_EOS_FIELD_UNION(gd_field, eos_field)                                                      \
    if constexpr (std::is_same_v<EOS_EMetricsAccountIdType, std::decay_t<decltype(eos_field##Type)>>) { \
        gd_field = to_godot_data_union(eos_field, eos_field##Type);                                     \
        gd_field##_type = eos_field##Type;                                                              \
    } else {                                                                                            \
        gd_field = to_godot_data_union(eos_field, eos_field##Type);                                     \
    }

#define _TO_EOS_FIELD(eos_field, gd_field) \
    to_eos_type_out<_DECLTYPE_GODOT_ARG_TYPE(gd_field), decltype(eos_field)>(std::move(gd_field), eos_field)
#define _TO_EOS_FIELD_ARR(eos_field, gd_field, r_eos_field_count) \
    eos_field = (decltype(eos_field))to_eos_type_arr(gd_field, r_eos_field_count)
#define _TO_EOS_STR_ARR(eos_field, gd_field, r_eos_field_count)                                 \
    eos_field = nullptr;                                                                        \
    if (gd_field.size()) {                                                                      \
        using eos_str_t = std::remove_const_t<std::remove_reference_t<decltype(eos_field[0])>>; \
        using arr_ty = eos_str_t *;                                                             \
        arr_ty arr = memnew_arr(eos_str_t, gd_field.size());                                    \
        for (decltype(gd_field.size()) i = 0; i < gd_field.size(); ++i) {                       \
            arr[i] = to_eos_type<const CharString &, eos_str_t>(gd_field[i]);                   \
        }                                                                                       \
        eos_field = arr;                                                                        \
        r_eos_field_count = gd_field.size();                                                    \
    } else {                                                                                    \
        r_eos_field_count = 0;                                                                  \
    }
#define _TO_EOS_STR_ARR_FROM_PACKED_STRING_ARR(eos_field, gd_field, r_eos_field_count)          \
    eos_field = nullptr;                                                                        \
    LocalVector<CharString> _##gd_field;                                                        \
    if (gd_field.size()) {                                                                      \
        using eos_str_t = std::remove_const_t<std::remove_reference_t<decltype(eos_field[0])>>; \
        using arr_ty = eos_str_t *;                                                             \
        arr_ty arr = memnew_arr(eos_str_t, gd_field.size());                                    \
        for (decltype(gd_field.size()) i = 0; i < gd_field.size(); ++i) {                       \
            _##gd_field.push_back(gd_field[i].to_utf8_buffer());                                \
            eos_field[i] = to_eos_type<const CharString &, eos_str_t>(_##gd_field[i]);          \
        }                                                                                       \
        eos_field = arr;                                                                        \
        r_eos_field_count = gd_field.size();                                                    \
    } else {                                                                                    \
        r_eos_field_count = 0;                                                                  \
    }
#define _TO_EOS_FIELD_CLIENT_DATA(eos_field, gd_field) \
    static_assert(false, "不应该发生")
#define _TO_EOS_FIELD_STRUCT(eos_field, gd_field) \
    to_eos_data<decltype(gd_field), decltype(eos_field)>(gd_field, eos_field)
#define _TO_EOS_FIELD_STRUCT_ARR(gd_data_type, eos_field, gd_field, r_eos_field_count)              \
    r_eos_field_count = gd_field.size();                                                            \
    if (r_eos_field_count) {                                                                        \
        using _eos_data_type = std::remove_const_t<std::remove_pointer_t<decltype(eos_field)>>;     \
        auto eos_data_arr = (_eos_data_type *)memalloc(sizeof(_eos_data_type) * r_eos_field_count); \
        memset(&eos_field, 0, sizeof(_eos_data_type) * r_eos_field_count);                          \
        for (decltype(r_eos_field_count) i = 0; i < r_eos_field_count; ++i) {                       \
            auto casted_data = Object::cast_to<gd_data_type>(gd_field[0]);                          \
            ERR_BREAK(casted_data == nullptr);                                                      \
            casted_data->set_to_eos(eos_data_arr[0]);                                               \
        }                                                                                           \
        eos_field = eos_data_arr;                                                                   \
    } else {                                                                                        \
        eos_field = nullptr;                                                                        \
    }
#define _TO_EOS_FIELD_HANDLER(eos_field, gd_field, gd_type_to_cast) \
    eos_field = gd_field.is_valid() ? Object::cast_to<gd_type_to_cast>(gd_field.ptr())->get_handle() : nullptr
#define _TO_EOS_FIELD_ANTICHEAT_CLIENT_HANDLE(eos_field, gd_field) \
    eos_field = (void *)gd_field
#define _TO_EOS_FIELD_REQUESTED_CHANNEL(eos_field, gd_field) \
    eos_field = to_eos_requested_channel(gd_field)
#define _TO_EOS_FIELD_UNION(eos_field, gd_field)                                                        \
    CharString cache_##gd_field;                                                                        \
    if constexpr (std::is_same_v<EOS_EMetricsAccountIdType, std::decay_t<decltype(eos_field##Type)>>) { \
        to_eos_data_union(gd_field, eos_field, gd_field##_type, cache_##gd_field);                      \
        eos_field##Type = gd_field##_type;                                                              \
    } else {                                                                                            \
        to_eos_data_union(gd_field, eos_field, eos_field##Type, cache_##gd_field);                      \
    }

// 绑定
#define _MAKE_PROP_INFO(m_class, m_name) PropertyInfo(Variant::OBJECT, #m_name, {}, "", PROPERTY_USAGE_DEFAULT, m_class::get_class_static())
#define _MAKE_PROP_INFO_ENUM(m_name, enum_owner, enum_type) PropertyInfo(Variant::INT, #m_name, {}, "", PROPERTY_USAGE_DEFAULT, #enum_owner "." #enum_type)

// 展开转换
template <typename GDDataClass, typename EOSArraTy, typename TInt>
godot::TypedArray<GDDataClass> _to_godot_value_struct_arr(EOSArraTy p_eos_arr, TInt p_count) {
    godot::TypedArray<GDDataClass> ret;
    ret.resize(p_count);
    for (decltype(p_count) i = 0; i < p_count; ++i) {
        ret[i] = to_godot_data<GDDataClass, decltype(p_eos_arr[i])>(p_eos_arr[i]);
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
    if constexpr (std::is_same_v<EOS_EMetricsAccountIdType, std::decay_t<EOSUnionTypeEnum>>) {
        return eos_union_account_id_to_string(p_eos_union, p_type);
    } else {
        return eos_union_to_variant(p_eos_union, p_type);
    }
}

#define _EXPAND_TO_GODOT_VAL(m_gd_Ty, eos_field) to_godot_type<std::conditional_t<std::is_same_v<decltype(eos_field), eos_p2p_socketid_socked_name_t>, const eos_p2p_socketid_socked_name_t &, decltype(eos_field)>, m_gd_Ty>((eos_field))
#define _EXPAND_TO_GODOT_VAL_ARR(m_gd_Ty, eos_field, eos_field_count) to_godot_type_arr((eos_field), (eos_field_count))
// #define _EXPAND_TO_GODOT_VAL_ARR(m_gd_Ty, eos_field, eos_field_count) to_godot_type_arr<decltype((eos_field)), m_gd_Ty>((eos_field), (eos_field_count))
#define _EXPAND_TO_GODOT_VAL_CLIENT_DATA(m_gd_Ty, eos_field) ((_CallbackClientData *)eos_field)->client_data
#define _EXPAND_TO_GODOT_VAL_STRUCT(m_gd_Ty, eos_field) to_godot_data<m_gd_Ty, decltype(eos_field)>(eos_field)
#define _EXPAND_TO_GODOT_VAL_STRUCT_ARR(m_gd_Ty, eos_field, eos_filed_count) _to_godot_value_struct_arr<m_gd_Ty, decltype((eos_field)), decltype((eso_field_count))>((eos_field), (eos_filed_count))
#define _EXPAND_TO_GODOT_VAL_HANDLER(m_gd_Ty, eos_field) _to_godot_handle<m_gd_Ty, decltype((eos_field))>((eos_field))
#define _EXPAND_TO_GODOT_VAL_ANTICHEAT_CLIENT_HANDLE(m_gd_Ty, eos_field) (m_gd_Ty *)((eos_field))
#define _EXPAND_TO_GODOT_VAL_REQUESTED_CHANNEL(gd_field, eos_field) static_assert(false, "不该发生")
#define _EXPAND_TO_GODOT_VAL_UNION(m_gd_Ty, eos_field) _to_godot_val_from_union((eos_field), (eos_field##Type))

// 回调
#define _EOS_LOGGING_CALLBACK() [](const EOS_LogMessage *Message) {                                \
    if (EOS::get_log_message_callback().is_valid() && Message) {                                   \
        EOS::get_log_message_callback().call(Message->Category, Message->Message, Message->Level); \
    }                                                                                              \
}

#define _EOS_NOTIFY_CALLBACK(m_callback_info_ty, m_callback_identifier, m_callback_signal, m_arg_type)              \
    [](m_callback_info_ty m_callback_identifier) {                                                                  \
        if (auto obj = godot::Object::cast_to<godot::Object>((godot::Object *)m_callback_identifier->ClientData)) { \
            obj->emit_signal(SNAME(m_callback_signal), m_arg_type::from_eos(*m_callback_identifier));               \
        }                                                                                                           \
    }

#define _EOS_NOTIFY_CALLBACK_EXPANDED(m_callback_info_ty, m_callback_identifier, m_callback_signal, ...)              \
    [](m_callback_info_ty m_callback_identifier) {                                                                  \
        if (auto obj = godot::Object::cast_to<godot::Object>((godot::Object *)m_callback_identifier->ClientData)) { \
            obj->emit_signal(SNAME(m_callback_signal), ##__VA_ARGS__);                                              \
        }                                                                                                           \
    }

#define _EOS_METHOD_CALLBACK(m_callback_info_ty, m_callback_identifier, m_callback_signal, m_arg_type) \
    [](m_callback_info_ty m_callback_identifier) {                                                     \
        auto cd = _CallbackClientData::cast_to_scoped(m_callback_identifier->ClientData);              \
        auto cb_data = m_arg_type::from_eos(*m_callback_identifier);                                   \
        if (cd.get_callback().is_valid()) {                                                            \
            cd.get_callback().call(cb_data);                                                           \
        }                                                                                              \
        cd.get_handle_wrapper()->emit_signal(SNAME(m_callback_signal), cb_data);                       \
    }

#define _EOS_METHOD_CALLBACK_EXPANDED(m_callback_info_ty, m_callback_identifier, m_callback_signal, ...) \
    [](m_callback_info_ty m_callback_identifier) {                                                       \
        auto cd = _CallbackClientData::cast_to_scoped(m_callback_identifier->ClientData);                \
        if (cd.get_callback().is_valid()) {                                                              \
            cd.get_callback().call(__VA_ARGS__);                                                         \
        }                                                                                                \
        cd.get_handle_wrapper()->emit_signal(SNAME(m_callback_signal), ##__VA_ARGS__);                   \
    }

#define _EOS_USER_PRE_LOGOUT_CALLBACK(m_callback_info_ty, m_callback_identifier, m_callback_signal, m_arg_type)                          \
    [](m_callback_info_ty m_callback_identifier) {                                                                                       \
        auto cd = (_CallbackClientData *)m_callback_identifier->ClientData;                                                              \
        auto cb_data = m_arg_type::from_eos(*m_callback_identifier);                                                                     \
        auto return_action = EOS_EIntegratedPlatformPreLogoutAction::EOS_IPLA_ProcessLogoutImmediately;                                  \
        if (cd->callback.is_valid()) {                                                                                                   \
            auto res = cd->callback.call(cb_data);                                                                                       \
            if (res.get_type() != Variant::INT || (int32_t)res != 0 || (int32_t)res != 1) {                                              \
                ERR_PRINT("Read file data callback shoul return a Value of IntegreatePlatform.EOS_EIntegratedPlatformPreLogoutAction."); \
            } else {                                                                                                                     \
                return_action = (EOS_EIntegratedPlatformPreLogoutAction)(res.operator int32_t());                                        \
            }                                                                                                                            \
        }                                                                                                                                \
        cd->handle_wrapper->emit_signal(SNAME(m_callback_signal), cb_data);                                                              \
        return return_action;                                                                                                            \
    }

//
#define _EOS_PLATFORM_SETUP_TICK()                                                                                                                                                    \
protected:                                                                                                                                                                            \
    void tick_internal() {                                                                                                                                                            \
        if (m_handle) {                                                                                                                                                               \
            EOS_Platform_Tick(m_handle);                                                                                                                                              \
        }                                                                                                                                                                             \
    }                                                                                                                                                                                 \
    void setup_tick() {                                                                                                                                                               \
        MainLoop *main_loop = godot::Engine::get_singleton()->get_main_loop();                                                                                                        \
        ERR_FAIL_COND_MSG(main_loop == nullptr || !main_loop->has_signal("process_frame"), "EOS wraning: Can't tick automatically, please call \"EOSPlatform::tick()\" by youself."); \
        ERR_FAIL_COND(main_loop->connect("process_frame", callable_mp(this, &EOSPlatform::tick_internal)) != OK);                                                                     \
    }                                                                                                                                                                                 \
    void _notification(int p_what) {                                                                                                                                                  \
        if (p_what == NOTIFICATION_POSTINITIALIZE) {                                                                                                                                  \
            callable_mp(this, &EOSPlatform::setup_tick).call_deferred();                                                                                                              \
        }                                                                                                                                                                             \
    }

// Memory
EOS_MEMORY_CALL static void *_memallocate(size_t SizeInBytes, size_t Alignment) {
    return Memory::alloc_static(SizeInBytes);
}
EOS_MEMORY_CALL static void *_memreallocate(void *Pointer, size_t SizeInBytes, size_t Alignment) {
    return Memory::realloc_static(Pointer, SizeInBytes);
}
EOS_MEMORY_CALL static void _memrelease(void *Pointer) {
    Memory::free_static(Pointer);
}

} //namespace godot::eos::internal

namespace godot::eos {

// Platform Specific Options
#if defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)
void setup_eos_project_settings();
#endif // defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

void *get_platform_specific_options();

} //namespace godot::eos
#pragma once

#include <godot_cpp/classes/editor_export_platform.hpp>
#include <godot_cpp/classes/editor_export_plugin.hpp>

namespace godot::eos::editor {

// 安卓导出插件：在导出 Android 包时自动注入 EOS SDK 所需的 aar 依赖、
// Gradle 依赖以及登录协议 scheme 字符串资源，免去用户手动修改安卓工程。
class EOSAndroidExportPlugin : public EditorExportPlugin {
    GDCLASS(EOSAndroidExportPlugin, EditorExportPlugin)

protected:
    static void _bind_methods();

public:
    PackedStringArray _get_android_libraries(const Ref<EditorExportPlatform> &p_platform, bool p_debug) const override;
    PackedStringArray _get_android_dependencies(const Ref<EditorExportPlatform> &p_platform, bool p_debug) const override;
    String _get_name() const override;
    bool _supports_platform(const Ref<EditorExportPlatform> &p_platform) const override;

    // 在导出开始时把 eos_login_protocol_scheme 注入到安卓工程的 strings.xml，
    // 这样 EOS Android SDK 才能通过 scheme 完成登录回调。
    void _export_begin(const PackedStringArray &p_features, bool p_is_debug, const String &p_path, uint32_t p_flags) override;
};

} //namespace godot::eos::editor

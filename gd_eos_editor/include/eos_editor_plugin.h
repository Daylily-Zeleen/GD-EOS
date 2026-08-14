#pragma once

#include <godot_cpp/classes/editor_export_plugin.hpp>
#include <godot_cpp/classes/editor_plugin.hpp>
#include <godot_cpp/classes/ref.hpp>

#include "eos_android_export_plugin.h"

namespace godot::eos::editor {

class EOSEditorPlugin : public EditorPlugin {
    GDCLASS(EOSEditorPlugin, EditorPlugin)

protected:
    static void _bind_methods();

    // 安卓自动配置导出插件，由本编辑器插件持有并注册/注销。
    Ref<EOSAndroidExportPlugin> android_export_plugin;

    // 工具菜单回调：在项目根生成 .env 模板。
    void _generate_env_template();

public:
    void _notification(int p_what);
};

} //namespace godot::eos::editor

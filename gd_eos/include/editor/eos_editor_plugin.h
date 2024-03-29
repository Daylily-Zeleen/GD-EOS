#pragma once
#if defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

#include <godot_cpp/classes/editor_export_plugin.hpp>
#include <godot_cpp/classes/editor_plugin.hpp>

namespace godot::eos::editor {

class EOSExportPlugin : public EditorExportPlugin {
    GDCLASS(EOSExportPlugin, EditorExportPlugin)
protected:
    static void _bind_methods();

public:
    virtual String _get_name() const override;
    virtual void _export_begin(const PackedStringArray &features, bool is_debug, const String &path, uint32_t flags) override;
};

class EOSEditorPlugin : public EditorPlugin {
    GDCLASS(EOSEditorPlugin, EditorPlugin)

    Ref<EOSExportPlugin> export_plugin;

protected:
    static void _bind_methods();

public:
    void _notification(int p_what);
};

} //namespace godot::eos::editor

#endif // defined(TOOLS_ENABLED) || defined(DEV_ENABLED) || defined(DEBUG_ENABLED)

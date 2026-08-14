#include "eos_android_export_plugin.h"

#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/editor_export_platform.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/os.hpp>
#include <godot_cpp/classes/project_settings.hpp>
#include <godot_cpp/core/error_macros.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include "../../gd_eos_defs.h"

static constexpr const char *CLIENT_ID_ENV_KEY = "CLIENT_ID";
static constexpr const char *EOS_CLIENT_ID_ENV_KEY = "EOS_CLIENT_ID";

namespace godot::eos::editor {

namespace {

// 优先从 res://.env 读取 EOS ClientId（键名 CLIENT_ID）。
// 再尝试从系统环境变量读取  EOS_CLIENT_ID/ CLIENT_ID。
String _read_client_id_from_env(String &r_cliend_id_source_msg) {
    String client_id;

    // 优先从 res://.env 读取
    const String dotenv_content = FileAccess::get_file_as_string("res://.env");
    if (!dotenv_content.is_empty()) {
        const PackedStringArray lines = dotenv_content.split("\n");
        for (int i = 0; i < lines.size(); ++i) {
            const String line = lines[i].strip_edges();
            if (line.is_empty() || line.begins_with("#"))
                continue;

            const PackedStringArray key_value = line.split("=", true, 1);
            if (key_value.size() != 2)
                continue;

            const String key = key_value[0].strip_edges();
            String value = key_value[1].strip_edges();

            if (key == CLIENT_ID_ENV_KEY) {
                // 去掉可能的引号
                if (value.length() >= 2 && (value.begins_with("\"") && value.ends_with("\""))) {
                    value = value.substr(1, value.length() - 2);
                }
                client_id = value;
                r_cliend_id_source_msg = vformat("\"%s\" from \"res://.env\".", CLIENT_ID_ENV_KEY);
                break;
            }
        }
    }

    // 尝试从系统环境变量中读取（用于 CI/CD 等场景）
    if (client_id.is_empty()) {
        OS *os = OS::get_singleton();
        if (os != nullptr) {
            const String from_eos = os->get_environment(EOS_CLIENT_ID_ENV_KEY);
            if (!from_eos.is_empty()) {
                client_id = from_eos;
                r_cliend_id_source_msg = vformat("system environment variable: \"%s\".", EOS_CLIENT_ID_ENV_KEY);
            } else {
                const String from_plain = os->get_environment(CLIENT_ID_ENV_KEY);
                if (!from_plain.is_empty()) {
                    client_id = from_plain;
                    r_cliend_id_source_msg = vformat("system environment variable: \"%s\".", CLIENT_ID_ENV_KEY);
                }
            }
        }
    }

    return client_id;
}

// 把 eos_login_protocol_scheme 字符串资源注入到安卓工程的 res/values/strings.xml。
// 该文件在用户安装安卓构建模板后生成，路径在 4.3-4.7 各版本保持一致，
// 因此无需区分 Groovy/KTS 构建脚本。
bool _inject_login_scheme(const String &p_client_id) {
    if (p_client_id.is_empty()) {
        ERR_PRINT("GD-EOS: Can't not find EOS ClientId to inject EOS login scheme. Please set \"CLIENT_ID=your_client_id\" in \"res://.env\", or set \"EOS_CLIENT_ID\"/\"CLIENT_ID\" in your system environment variables.");
        return false;
    }
    const String scheme = "eos." + p_client_id.to_lower();

    const String strings_path = "res://android/build/res/values/strings.xml";
    if (DirAccess::dir_exists_absolute("res://android/build/res/values")) {
        // 安卓构建模板尚未安装，导出流程稍后会报错，这里直接跳过。
        return false;
    }

    String xml = FileAccess::get_file_as_string(strings_path); // 读取原文件内容
    const String resource_line = "    <string name=\"eos_login_protocol_scheme\">" + scheme + "</string>\n";
    if (xml.is_empty()) {
        xml = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<resources>\n" + resource_line + "</resources>\n";
    } else if (xml.contains("eos_login_protocol_scheme")) {
        // 已存在，替换为最新值（幂等，避免重复）。
        const PackedStringArray parts = xml.split("eos_login_protocol_scheme");
        // 简单替换：找到 <string name="eos_login_protocol_scheme">...</string> 整行
        const PackedStringArray lines = xml.split("\n");
        String new_xml;
        for (int i = 0; i < lines.size(); ++i) {
            if (lines[i].contains("eos_login_protocol_scheme")) {
                new_xml += resource_line;
            } else {
                new_xml += lines[i] + String("\n");
            }
        }
        xml = new_xml;
    } else {
        // 在 </resources> 前插入。
        int idx = xml.find("</resources>");
        if (idx == -1) {
            xml += resource_line;
        } else {
            xml = xml.substr(0, idx) + resource_line + xml.substr(idx, xml.length());
        }
    }

    const Ref<FileAccess> wf = FileAccess::open(strings_path, FileAccess::WRITE);
    if (wf.is_valid()) {
        wf->store_string(xml);
        wf->close();
    } else {
        ERR_PRINT(vformat("GD-EOS: Can't inject EOS login scheme into '%s': %s", strings_path, UtilityFunctions::error_string(FileAccess::get_open_error())));
    }

    return true;
}

} // namespace

void EOSAndroidExportPlugin::_bind_methods() {}

PackedStringArray EOSAndroidExportPlugin::_get_android_libraries(const Ref<EditorExportPlatform> &p_platform, bool p_debug) const {
    PackedStringArray libs;
    libs.push_back("res://addons/" EOS_PLUGIN_FOLDER "/bin/android/eossdk-StaticSTDC-release.aar");
    return libs;
}

PackedStringArray EOSAndroidExportPlugin::_get_android_dependencies(const Ref<EditorExportPlatform> &p_platform, bool p_debug) const {
    PackedStringArray deps;
    deps.push_back("androidx.appcompat:appcompat:1.5.1");
    deps.push_back("androidx.constraintlayout:constraintlayout:2.1.4");
    deps.push_back("androidx.security:security-crypto:1.0.0");
    deps.push_back("androidx.browser:browser:1.4.0");
    // Java 8 desugaring（EOS SDK 1.18+ 需要）
    deps.push_back("androidx.webkit:webkit:1.7.0");
    return deps;
}

String EOSAndroidExportPlugin::_get_name() const {
    return "GD-EOS Android";
}

bool EOSAndroidExportPlugin::_supports_platform(const Ref<EditorExportPlatform> &p_platform) const {
    if (p_platform.is_null()) {
        return false;
    }
    return p_platform->get_os_name() == "Android";
}

void EOSAndroidExportPlugin::_export_begin(const PackedStringArray &p_features, bool p_is_debug, const String &p_path, uint32_t p_flags) {
    // 仅在导出 Android 时注入登录 scheme。
    if (!p_features.has("android")) {
        return;
    }

    String client_id_source_msg;
    const String client_id = _read_client_id_from_env(client_id_source_msg);
    if (_inject_login_scheme(client_id)) {
        UtilityFunctions::print("GD-EOS: Injected EOS login scheme into Android project. ClientId is got from ", client_id_source_msg);
    }
}

} //namespace godot::eos::editor

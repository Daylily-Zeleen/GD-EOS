# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import shutil

from SCons.Environment import Environment
from SCons.Script import ARGUMENTS, Exit, Help, SConscript
from SCons.Tool import Tool
from SCons.Variables import Variables

os.system("chcp 65001")

env: Environment = SConscript("godot-cpp/SConstruct")

# ─── 构建选项 ─────────────────────────────────────────────────────────────

opts = Variables(None, ARGUMENTS)
gd_eos_tool = Tool("gd_eos", toolpath=["tools"])
gd_eos_tool.options(opts, env)
opts.Update(env)
Help(opts.GenerateHelpText(env))

# 提示可忽略的警告
_hint_keys = [
    "min_field_count_to_expand_input_structs",
    "min_field_count_to_expand_callback_structs",
    "assume_only_one_local_user",
    "generate_eos_bindings",
]
_hint = ", ".join(f"'{k}'" for k in _hint_keys if k in ARGUMENTS)
if _hint:
    print(f"HINT: You can ignore warnings about {_hint} safely.")

gd_eos_tool.generate(env)

# ─── SDK 版本检查 ─────────────────────────────────────────────────────────

# 当 EOS SDK 版本大于 1.18.1.2 时禁止为 32 位 Windows 和 Android 平台编译
_eos_major, _eos_minor, _eos_patch, _hotfix = env.GD_EOS_GET_SDK_VERSION()
_skip_32bit = (_eos_major, _eos_minor, _eos_patch, _hotfix) > (1, 18, 1, 2)

if env["platform"] == "windows" and "64" not in env["arch"]:
    if _skip_32bit:
        print(f"Error: EOS SDK {_eos_major}.{_eos_minor}.{_eos_patch}.{_hotfix} does not support 32-bit Windows platform.")
        print("Please use 64-bit architecture or downgrade EOS SDK to version 1.18.1.2 or earlier.")
        Exit(1)

if env["platform"] == "android" and "64" not in env["arch"]:
    if _skip_32bit:
        print(f"Error: EOS SDK {_eos_major}.{_eos_minor}.{_eos_patch}.{_hotfix} does not support 32-bit Android platform.")
        print("Please use 64-bit architecture or downgrade EOS SDK to version 1.18.1.2 or earlier.")
        Exit(1)

# ─── 路径配置 ─────────────────────────────────────────────────────────────

LIB_NAME = "libgdeos"
EOS_SDK_FOLDER = "thirdparty/eos-sdk/SDK/"
OUTPUT_BIN_FOLDER = "bin/"
BASE_DIR = "gd_eos/"
PLUGIN_FOLDER = "demo/addons/gd-eos/"
PLUGIN_BIN_FOLDER = os.path.join(PLUGIN_FOLDER, "bin")
EXTENSION_FILE = os.path.join(PLUGIN_FOLDER, "gd-eos.gdextension")
EOS_AAR_DIR = os.path.join(EOS_SDK_FOLDER, "Bin/Android/static-stdc++/aar/")
ANDROID_BUILD_TMP_DIR = "./.android_build_tmp/"


# ─── 辅助函数 ─────────────────────────────────────────────────────────────


def _copy_file(from_path: str, to_path: str) -> None:
    if not os.path.exists(os.path.dirname(to_path)):
        os.makedirs(os.path.dirname(to_path))
    shutil.copyfile(from_path, to_path)


def _get_min_compatible_version() -> str:
    # godot-cpp 4.3 以上支持 GodotCPPDocData
    try:
        env._dict["BUILDERS"]["GodotCPPDocData"]
        return "4.3"
    except Exception:
        return "4.2"


def _gather_sources_recursively(base_dir: str, sources: list) -> None:
    for f in os.listdir(base_dir):
        dir_path = os.path.join(base_dir, f)
        if os.path.isdir(dir_path):
            sources += env.Glob(os.path.join(dir_path, "*.cpp"))
            _gather_sources_recursively(dir_path, sources)


# ─── 平台相关配置 ────────────────────────────────────────────────────────


def _configure_windows(env: Environment, arch: str) -> None:
    # 忽略 LNK1218 警告，以便在 GitHub Action 中使用 scons cache
    env.Append(LINKFLAGS=["/ignore:4099"])
    env.Append(LIBPATH=[EOS_SDK_FOLDER + "Lib/"])

    if "64" in arch:
        env.Append(LIBS=["EOSSDK-Win64-Shipping"])
    else:
        env.Append(LIBS=["EOSSDK-Win32-Shipping"])


def _configure_linux(env: Environment) -> None:
    env.Append(LIBS=["EOSSDK-Linux-Shipping"])


def _configure_macos(env: Environment) -> None:
    env.Append(LIBS=["EOSSDK-Mac-Shipping"])


def _configure_android(env: Environment, arch: str) -> None:
    eos_android_arch_map = {
        "x86_64": "x86_64",
        "x86_32": "x86",
        "arm64": "arm64-v8a",
        "arm32": "armeabi-v7a",
    }
    eos_android_arch = eos_android_arch_map.get(arch, "arm64-v8a")

    import zipfile

    # 查找 aar 文件
    aar_file = next((f for f in os.listdir(EOS_AAR_DIR) if f.lower().endswith("aar")), None)
    if not aar_file:
        print("Can't find EOSSDK's static stdc++ aar file.")
        Exit(1)

    # 生成临时目录
    if not os.path.exists(ANDROID_BUILD_TMP_DIR):
        os.mkdir(ANDROID_BUILD_TMP_DIR)

    # 复制为 .zip 并提取 libs
    copied_file = os.path.join(ANDROID_BUILD_TMP_DIR, "tmp.zip")
    shutil.copyfile(os.path.join(EOS_AAR_DIR, aar_file), copied_file)

    with zipfile.ZipFile(copied_file) as zf:
        for f in zf.namelist():
            if f.startswith("jni"):
                zf.extract(f, ANDROID_BUILD_TMP_DIR)

    lib_dir = os.path.join(ANDROID_BUILD_TMP_DIR, "jni", eos_android_arch)
    env.Append(LIBPATH=[lib_dir])
    env.Append(LIBS=["EOSSDK"])


def _configure_ios(env: Environment, arch: str) -> None:
    if arch != "arm64":
        raise Exception("Only arm64 is supported on iOS.")

    ios_framework_path = PLUGIN_BIN_FOLDER + "/ios/EOSSDK.xcframework"
    shutil.rmtree(ios_framework_path, ignore_errors=True)
    shutil.copytree(EOS_SDK_FOLDER + "Bin/IOS/EOSSDK.xcframework", ios_framework_path)

    env.Append(
        LINKFLAGS=[
            "-F",
            PLUGIN_BIN_FOLDER + "/ios/EOSSDK.xcframework/ios-arm64",
            "-framework",
            "AuthenticationServices",
            "-framework",
            "EOSSDK",
        ]
    )


# ─── 完成后处理 ──────────────────────────────────────────────────────────


def _copy_platform_dependencies(platform: str, arch: str) -> None:
    if platform == "windows":
        if "64" in arch:
            dest_dir = PLUGIN_BIN_FOLDER + "/windows/x64"
            shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.copytree(EOS_SDK_FOLDER + "Bin/x64", dest_dir)
            _copy_file(EOS_SDK_FOLDER + "Bin/EOSSDK-Win64-Shipping.dll", PLUGIN_BIN_FOLDER + "/windows/EOSSDK-Win64-Shipping.dll")
        else:
            dest_dir = PLUGIN_BIN_FOLDER + "/windows/x86"
            shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.copytree(EOS_SDK_FOLDER + "Bin/x86", dest_dir)
            _copy_file(EOS_SDK_FOLDER + "Bin/EOSSDK-Win32-Shipping.dll", PLUGIN_BIN_FOLDER + "/windows/EOSSDK-Win32-Shipping.dll")

    elif platform == "linux":
        _copy_file(EOS_SDK_FOLDER + "Bin/libEOSSDK-Linux-Shipping.so", PLUGIN_BIN_FOLDER + "/linux/libEOSSDK-Linux-Shipping.so")

    elif platform == "macos":
        _copy_file(EOS_SDK_FOLDER + "Bin/libEOSSDK-Mac-Shipping.dylib", PLUGIN_BIN_FOLDER + "/macos/libEOSSDK-Mac-Shipping.dylib")

    elif platform == "android":
        if os.path.exists(ANDROID_BUILD_TMP_DIR):
            shutil.rmtree(ANDROID_BUILD_TMP_DIR)


def _copy_output_library(env: Environment, platform: str, target: str, suffix: str, shared_lib_suffix: str) -> None:
    if platform == "macos":
        src = f"{OUTPUT_BIN_FOLDER}/macos/{LIB_NAME}.{platform}.{target}.framework/{LIB_NAME}.{platform}.{target}"
        dst = f"{PLUGIN_BIN_FOLDER}/macos/{LIB_NAME}.{platform}.{target}.framework/{LIB_NAME}.{platform}.{target}".replace(".dev.", ".")
    else:
        src = f"{OUTPUT_BIN_FOLDER}/{platform}/{LIB_NAME}{suffix}{shared_lib_suffix}"
        dst = f"{PLUGIN_BIN_FOLDER}/{platform}/{LIB_NAME}{suffix}{shared_lib_suffix}".replace(".dev.", ".")
    _copy_file(src, dst)


def _update_gdextension_file() -> None:
    version = open("version", "r").readline().strip()

    with open(EXTENSION_FILE, "r", encoding="utf8") as f:
        lines = f.readlines()

    for i in range(len(lines)):
        if lines[i].startswith("version = ") and lines[i].endswith("\n"):
            lines[i] = f'version = "{version}"\n'
        if lines[i].startswith("compatibility_minimum") and lines[i].endswith("\n"):
            lines[i] = f"compatibility_minimum = {_get_min_compatible_version()}\n"
            break

    with open(EXTENSION_FILE, "w", encoding="utf8") as f:
        f.writelines(lines)


def _copy_readme_files() -> None:
    files_to_copy = [
        ("README.md", os.path.join(PLUGIN_FOLDER, "README.md")),
        ("README.zh.md", os.path.join(PLUGIN_FOLDER, "README.zh.md")),
        ("LICENSE", os.path.join(PLUGIN_FOLDER, "LICENSE")),
    ]

    for src, dst in files_to_copy:
        _copy_file(src, dst)

    # 替换 readme 中图片的路径
    for _, fp in files_to_copy[:2]:
        with open(fp, "r", encoding="utf8") as f:
            lines = f.readlines()

        for i in range(len(lines)):
            if "(demo/addons/gd-eos/" in lines[i]:
                lines[i] = lines[i].replace("(demo/addons/gd-eos/", "(")

        with open(fp, "w", encoding="utf8") as f:
            f.writelines(lines)


def _on_complete(target, source, env) -> None:
    platform = env["platform"]
    arch = env["arch"]
    target_type = env["target"]
    suffix = env.get("suffix", "")
    shared_lib_suffix = env["SHLIBSUFFIX"]

    _copy_output_library(env, platform, target_type, suffix, shared_lib_suffix)
    _copy_platform_dependencies(platform, arch)
    _update_gdextension_file()
    _copy_readme_files()

    env.GD_EOS_POSTPROCESS()


# ─── 主构建函数 ───────────────────────────────────────────────────────────


def _build_gd_eos(env: Environment):
    # 绑定生成与预处理
    _, generated_sources = env.GD_EOS_GENERATE_BINDINGS()
    env.GD_EOS_PREPROCESS()

    # 头文件搜索路径
    env.Append(
        CPPPATH=[
            os.path.join(EOS_SDK_FOLDER, "Include"),
            os.path.join(BASE_DIR, "include"),
            os.path.join(BASE_DIR, "gen", "include"),
        ]
    )

    # 收集源文件
    sources = env.Glob(os.path.join(BASE_DIR, "src", "*.cpp"))
    _gather_sources_recursively(os.path.join(BASE_DIR, "src"), sources)
    sources.extend([f for f in generated_sources if str(f).endswith(".cpp")])

    # doc (godot-cpp 4.3 以上)
    doc_data = env.GD_EOS_GENERATE_DOC_DATA()
    if doc_data:
        sources.append(doc_data)

    if env.get("is_msvc", False):
        env.Append(CXXFLAGS=["/bigobj"])

    # 添加依赖库
    env.Append(LIBPATH=[EOS_SDK_FOLDER + "Bin/"])

    platform = env["platform"]
    arch = env["arch"]

    if platform == "windows":
        _configure_windows(env, arch)
    elif platform == "linux":
        _configure_linux(env)
    elif platform == "macos":
        _configure_macos(env)
    elif platform == "android":
        _configure_android(env, arch)
    elif platform == "ios":
        _configure_ios(env, arch)

    # 构建库
    if platform == "macos":
        library = env.SharedLibrary(
            f"{OUTPUT_BIN_FOLDER}/macos/{LIB_NAME}.{platform}.{env['target']}.framework/{LIB_NAME}.{platform}.{env['target']}",
            source=sources,
        )
    else:
        library = env.SharedLibrary(
            f"{OUTPUT_BIN_FOLDER}/{platform}/{LIB_NAME}{env['suffix']}{env['SHLIBSUFFIX']}",
            source=sources,
        )

    # 禁用 scons 缓存
    env.NoCache(sources)

    complete_command = env.Command("complete", library, _on_complete)
    env.Depends(complete_command, library)
    env.Default(complete_command)

    env.GD_EOS_ADD_CLEAN_FILES(library)
    return library


_build_gd_eos(env)

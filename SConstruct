#!/usr/bin/env python
import os
import shutil

import build_version

import gd_eos.eos_code_generator as eos_code_generator

# Generate
eos_code_generator.generator_eos_interfaces()

env = SConscript("godot-cpp/SConstruct")
lib_name = "libgdeos"

plugin_bin_folder = "demo/addons/gd-eos/bin"
output_bin_folder = "bin/"

eos_sdk_folder = "thirdparty/eos-sdk/SDK/"
base_dir = "gd_eos/"

extension_file = "demo/addons/gd-eos/gdeos.gdextension"

# For reference:
# - CCFLAGS are compilation flags shared between C and C++
# - CFLAGS are for C-specific compilation flags
# - CXXFLAGS are for C++-specific compilation flags
# - CPPFLAGS are for pre-processor flags
# - CPPDEFINES are for pre-processor defines
# - LINKFLAGS are for linking flags

# 头文件搜索路径
env.Append(
    CPPPATH=[
        os.path.join(eos_sdk_folder, "Include"),
        os.path.join(base_dir, "include"),
        os.path.join(base_dir, "gen", "include"),
    ]
)


# 递归获取源文件
def gather_sources_recursively(base_dir: str) -> None:
    global sources
    for f in os.listdir(base_dir):
        dir: str = os.path.join(base_dir, f)
        if os.path.isdir(dir):
            sources += Glob(os.path.join(dir, "*.cpp"))
            gather_sources_recursively(dir)


sources = Glob(os.path.join(base_dir, "src", "*.cpp"))
gather_sources_recursively(os.path.join(base_dir, "src"))
gather_sources_recursively(os.path.join(base_dir, "gen", "src"))


if env.get("is_msvc", False):
    env.Append(CXXFLAGS=["/bigobj"])


# 添加依赖库
env.Append(LIBPATH=[eos_sdk_folder + "Bin/"])
if env["platform"] == "windows":
    # TODO: dont ignore this warning
    # this disables LINK : error LNK1218: warning treated as error;
    # so that it can build in github action with scons cache
    env.Append(LINKFLAGS=["/ignore:4099"])

    env.Append(LIBPATH=[eos_sdk_folder + "Lib/"])
    if "64" in env["arch"]:
        env.Append(LIBS=["EOSSDK-Win64-Shipping"])
    else:
        env.Append(LIBS=["EOSSDK-Win32-Shipping"])


elif env["platform"] == "linux":
    env.Append(LIBS=["EOSSDK-Linux-Shipping"])

elif env["platform"] == "macos":
    env.Append(LIBS=["EOSSDK-Mac-Shipping"])

elif env["platform"] == "android":
    eos_android_arch = "arm64-v8a"
    if env["arch"] == "x86_64":
        eos_android_arch = "x86_64"
    elif env["arch"] == "x86_32":
        eos_android_arch = "x86"
    elif env["arch"] == "arm64":
        eos_android_arch = "arm64-v8a"
    elif env["arch"] == "arm32":
        eos_android_arch = "armeabi-v7a"

    # 1.16.1 需要链接对应的 so
    lib_dir = eos_sdk_folder + f"Bin/Android/static-stdc++/libs/{eos_android_arch}/"
    if os.path.exists(lib_dir):
        env.Append(LIBPATH=[eos_sdk_folder + f"Bin/Android/static-stdc++/libs/{eos_android_arch}/"])
        env.Append(LIBS=["EOSSDK"])


# 输出
if env["platform"] == "macos":
    library = env.SharedLibrary(
        f"{output_bin_folder}/macos/{lib_name}.{env['platform']}.{env['target']}.framework/{lib_name}.{env['platform']}.{env['target']}",
        source=sources,
    )
else:
    library = env.SharedLibrary(
        f"{output_bin_folder}/{env['platform']}/{lib_name}{env['suffix']}{env['SHLIBSUFFIX']}",
        source=sources,
    )


platform = env["platform"]
arch = env["arch"]
compile_target = env["target"]
suffix = env.get("suffix", "")
shared_lib_suffix = env["SHLIBSUFFIX"]


def copy_file(from_path, to_path):
    if not os.path.exists(os.path.dirname(to_path)):
        os.makedirs(os.path.dirname(to_path))
    shutil.copyfile(from_path, to_path)


def update_extension_version():
    f = open(extension_file, "r", encoding="utf8")
    lines = f.readlines()
    f.close()

    for i in range(len(lines)):
        if lines[i].startswith('version = "') and lines[i].endswith('"\n'):
            lines[i] = f'version = "{build_version.version}"\n'
            break

    f = open(extension_file, "w", encoding="utf8")
    f.writelines(lines)
    f.close()


def on_complete(target, source, env):
    # 拷贝生成库的
    if platform == "macos":
        copy_file(
            f"{output_bin_folder}/macos/{lib_name}.{platform}.{compile_target}.framework/{lib_name}.{platform}.{compile_target}",
            f"{plugin_bin_folder}/macos/{lib_name}.{platform}.{compile_target}.framework/{lib_name}.{platform}.{compile_target}",
        )
    else:
        copy_file(
            f"{output_bin_folder}/{platform}/{lib_name}{suffix}{shared_lib_suffix}",
            f"{plugin_bin_folder}/{platform}/{lib_name}{suffix}{shared_lib_suffix}",
        )

    # 拷贝依赖
    if platform == "windows":
        if "64" in arch:
            shutil.rmtree(plugin_bin_folder + "/windows/x64", ignore_errors=True)
            shutil.copytree(eos_sdk_folder + "Bin/x64", plugin_bin_folder + "/windows/x64")
            copy_file(eos_sdk_folder + "Bin/EOSSDK-Win64-Shipping.dll", plugin_bin_folder + "/windows/EOSSDK-Win64-Shipping.dll")
        else:
            shutil.rmtree(plugin_bin_folder + "/windows/x86", ignore_errors=True)
            shutil.copytree(eos_sdk_folder + "Bin/x86", plugin_bin_folder + "/windows/x86")
            copy_file(eos_sdk_folder + "Bin/EOSSDK-Win32-Shipping.dll", plugin_bin_folder + "/windows/EOSSDK-Win32-Shipping.dll")

    elif platform == "linux":
        # Epic只提供了64位的so
        copy_file(eos_sdk_folder + "Bin/libEOSSDK-Linux-Shipping.so", plugin_bin_folder + "/linux/libEOSSDK-Linux-Shipping.so")

    elif platform == "macos":
        copy_file(eos_sdk_folder + "Bin/libEOSSDK-Mac-Shipping.dylib", plugin_bin_folder + "/macos/libEOSSDK-Mac-Shipping.dylib")

    # elif platform == "android":
    #     copy_file(eos_sdk_folder + f"Bin/Android/static-stdc++/libs/{eos_android_arch}/libEOSSDK.so", plugin_bin_folder + f"/android/libEOSSDK.so")

    # 更新.gdextension中的版本信息
    update_extension_version()


# Disable scons cache for source files
NoCache(sources)

complete_command = Command("complete", library, on_complete)
Depends(complete_command, library)
Default(complete_command)

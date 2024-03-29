#!/usr/bin/env python
import os
import sys
import shutil

import gd_eos.eos_code_generator as eos_code_generator

# Generate
eos_code_generator.generator_eos_interfaces()

env = SConscript("godot-cpp/SConstruct")
lib_name = "libgdeos"
plugin_bin_folder = "sample/addons/gd-eos/bin"

eos_sdk_folder = "thirdparty/eos-sdk/SDK/"

base_dir = "gd_eos/"

# For reference:
# - CCFLAGS are compilation flags shared between C and C++
# - CFLAGS are for C-specific compilation flags
# - CXXFLAGS are for C++-specific compilation flags
# - CPPFLAGS are for pre-processor flags
# - CPPDEFINES are for pre-processor defines
# - LINKFLAGS are for linking flags

# Add source files
env.Append(CPPPATH=[eos_sdk_folder + "Include/", os.path.join(base_dir, "include"), os.path.join(base_dir, "gen","include")])
sources = Glob(os.path.join(base_dir, "src", "*.cpp"))

def gather_sources_recursively(base_dir:str) -> None:
    global sources
    for f in os.listdir(base_dir):
        dir :str = os.path.join(base_dir, f)
        if os.path.isdir(dir):
            sources += Glob(os.path.join(dir, "*.cpp"))
            gather_sources_recursively(dir)

gather_sources_recursively(os.path.join(base_dir, "src"))
gather_sources_recursively(os.path.join(base_dir, "gen", "src"))



platform = env["platform"]

env.Append(CPPDEFINES=["NOT_NEED_ENUM_CALSS"])

if env.get("is_msvc", False):
    env.Append(CXXFLAGS=["/bigobj"])
env.Append(LIBPATH=[eos_sdk_folder + "Lib/"])
env.Append(LIBPATH=[eos_sdk_folder + "Bin/"])

if env["platform"] == "windows":
    # TODO: dont ignore this warning
    # this disables LINK : error LNK1218: warning treated as error;
    # so that it can build in github action with scons cache
    env.Append(LINKFLAGS=["/ignore:4099"])
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

    env.Append(LIBPATH=[eos_sdk_folder + "Bin/Android/static-stdc++/libs/" + eos_android_arch + "/"]) 
    env.Append(LIBS=["EOSSDK"])


if env["platform"] == "macos":
    library = env.SharedLibrary(
        f"{plugin_bin_folder}/macos/{lib_name}.{env['platform']}.{env['target']}.framework/{lib_name}.{env['platform']}.{env['target']}",
        source=sources,)
else:
    library = env.SharedLibrary(
        f"{plugin_bin_folder}/{env['platform']}/{lib_name}{env['suffix']}{env['SHLIBSUFFIX']}",
        source=sources,
    )

arch = env["arch"]

def copy_file(from_path, to_path):
    if not os.path.exists(os.path.dirname(to_path)):
        os.makedirs(os.path.dirname(to_path))
    shutil.copyfile(from_path, to_path)

def on_complete(target, source, env):
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

# Disable scons cache for source files
NoCache(sources)

complete_command = Command('complete', library, on_complete)
Depends(complete_command, library)
Default(complete_command)
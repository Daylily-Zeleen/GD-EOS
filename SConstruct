#!/usr/bin/env python
import os, shutil
from SCons.Variables import Variables
from SCons.Script import SConscript
from SCons.Environment import Environment
from SCons.Tool import Tool

env :Environment = SConscript("godot-cpp/SConstruct")

# 帮助
opts = Variables(None, ARGUMENTS)
gd_eos_tool = Tool("gd_eos", toolpath=["tools"])
gd_eos_tool.options(opts, env)
opts.Update(env)
Help(opts.GenerateHelpText(env))

# 提示
hint = ""
for k in ["min_field_count_to_expand_input_structs", "min_field_count_to_expand_callback_structs", "assume_only_one_local_user"]:
    if k in ARGUMENTS:
        if len(hint) > 0:
            hint += ", "
        hint += f"'{k}'"
if len(hint) > 0:
    print(f"HINT: You can ignore warnings about {hint} safely.")

gd_eos_tool.generate(env)


lib_name = "libgdeos"

eos_sdk_folder = "thirdparty/eos-sdk/SDK/"
output_bin_folder = "bin/"

base_dir = "gd_eos/"
plugin_folder = "demo/addons/gd-eos/"
extension_file = os.path.join(plugin_folder, "gdeos.gdextension")
plugin_bin_folder = os.path.join(plugin_folder, "bin")

eos_aar_dir = os.path.join(eos_sdk_folder, "Bin/Android/static-stdc++/aar/")
android_build_tmp_dir = "./.android_build_tmp/"


def _copy_file(from_path, to_path):
    if not os.path.exists(os.path.dirname(to_path)):
        os.makedirs(os.path.dirname(to_path))
    shutil.copyfile(from_path, to_path)


def _on_complete(target, source, env):
    platform = env["platform"]
    arch = env["arch"]
    compile_target = env["target"]
    suffix = env.get("suffix", "")
    shared_lib_suffix = env["SHLIBSUFFIX"]

    # 拷贝生成库的
    if platform == "macos":
        _copy_file(
            f"{output_bin_folder}/macos/{lib_name}.{platform}.{compile_target}.framework/{lib_name}.{platform}.{compile_target}",
            f"{plugin_bin_folder}/macos/{lib_name}.{platform}.{compile_target}.framework/{lib_name}.{platform}.{compile_target}".replace(".dev.", "."),
        )
    else:
        _copy_file(
            f"{output_bin_folder}/{platform}/{lib_name}{suffix}{shared_lib_suffix}",
            f"{plugin_bin_folder}/{platform}/{lib_name}{suffix}{shared_lib_suffix}".replace(".dev.", "."),
        )

    # 拷贝依赖
    if platform == "windows":
        if "64" in arch:
            shutil.rmtree(plugin_bin_folder + "/windows/x64", ignore_errors=True)
            shutil.copytree(eos_sdk_folder + "Bin/x64", plugin_bin_folder + "/windows/x64")
            _copy_file(eos_sdk_folder + "Bin/EOSSDK-Win64-Shipping.dll", plugin_bin_folder + "/windows/EOSSDK-Win64-Shipping.dll")
        else:
            shutil.rmtree(plugin_bin_folder + "/windows/x86", ignore_errors=True)
            shutil.copytree(eos_sdk_folder + "Bin/x86", plugin_bin_folder + "/windows/x86")
            _copy_file(eos_sdk_folder + "Bin/EOSSDK-Win32-Shipping.dll", plugin_bin_folder + "/windows/EOSSDK-Win32-Shipping.dll")

    elif platform == "linux":
        # Epic只提供了64位的so
        _copy_file(eos_sdk_folder + "Bin/libEOSSDK-Linux-Shipping.so", plugin_bin_folder + "/linux/libEOSSDK-Linux-Shipping.so")

    elif platform == "macos":
        _copy_file(eos_sdk_folder + "Bin/libEOSSDK-Mac-Shipping.dylib", plugin_bin_folder + "/macos/libEOSSDK-Mac-Shipping.dylib")

    elif platform == "android":
        if os.path.exists(android_build_tmp_dir):
            shutil.rmtree(android_build_tmp_dir)
    #     _copy_file(eos_sdk_folder + f"Bin/Android/static-stdc++/libs/{eos_android_arch}/libEOSSDK.so", plugin_bin_folder + f"/android/{eos_android_arch}/libEOSSDK.so")

    # 更新.gdextension
    with open(extension_file, "r", encoding="utf8") as f:
        lines = f.readlines()
        f.close()

        version: str = open("version", "r").readline().strip()

        for i in range(len(lines)):
            if lines[i].startswith('version = ') and lines[i].endswith('\n'):
                lines[i] = f'version = {version}\n'
            if lines[i].startswith("compatibility_minimum") and lines[i].endswith('\n'):
                lines[i] = f'compatibility_minimum = {_get_min_compatible_version()}\n'
                break

        with open(extension_file, "w", encoding="utf8") as f:
            f.writelines(lines)

    copied_readme_file_path = os.path.join(plugin_folder, "README.md")
    copied_readme_zh_file_path = os.path.join(plugin_folder, "README.zh.md")
    copied_license_file_path = os.path.join(plugin_folder, "LICENSE")

    _copy_file("README.md", copied_readme_file_path)
    _copy_file("README.zh.md", copied_readme_zh_file_path)
    _copy_file("LICENSE", copied_license_file_path)

    # 替换 readme 中图片的路径
    for fp in [copied_readme_file_path, copied_readme_zh_file_path]:
        with open(fp, "r", encoding="utf8") as f:
            lines = f.readlines()

            for i in range(len(lines)):
                if lines[i].count("(demo/addons/gd-eos/") > 0:
                    lines[i] = lines[i].replace("(demo/addons/gd-eos/", "(")

            with open(fp, "w", encoding="utf8") as f:
                f.writelines(lines)

    # 后处理
    env.GD_EOS_POSTPROCESS()


def _get_min_compatible_version() -> str:
    # doc (godot-cpp 4.3 以上)
    try:
        env._dict['BUILDERS']["GodotCPPDocData"]
        return '4.3'
    except Exception as e:
        return '4.2'


# 递归获取源文件
def _gather_sources_recursively(base_dir: str, sources) -> None:
    for f in os.listdir(base_dir):
        dir: str = os.path.join(base_dir, f)
        if os.path.isdir(dir):
            sources += env.Glob(os.path.join(dir, "*.cpp"))
            _gather_sources_recursively(dir, sources)


def _build_gd_eos(env: Environment):
    # 绑定生成与预处理
    _, generated_sources =  env.GD_EOS_GENERATE_BINDINGS()
    env.GD_EOS_PREPROCESS()

    # 头文件搜索路径
    env.Append(
        CPPPATH=[
            os.path.join(eos_sdk_folder, "Include"),
            os.path.join(base_dir, "include"),
            os.path.join(base_dir, "gen", "include"),
        ]
    )

    sources = env.Glob(os.path.join(base_dir, "src", "*.cpp"))
    _gather_sources_recursively(os.path.join(base_dir, "src"), sources)
    # _gather_sources_recursively(os.path.join(base_dir, "gen", "src"), sources)
    sources.extend([f for f in generated_sources if str(f).endswith(".cpp")])

    # doc (godot-cpp 4.3 以上)
    doc_data = env.GD_EOS_GENERATE_DOC_DATA()
    if len(doc_data) > 0:
        sources.append(doc_data)

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

        import zipfile

        # 查找 aar, 以兼容新旧版本的不同命名
        aar_file = ""
        for f in os.listdir(eos_aar_dir):
            if f.lower().endswith("aar"):
                aar_file = f
                break

        if aar_file == "":
            print("Can't find EOSSDK's static stdc arr file.")
            exit(1)

        # 生成暂时目录
        if not os.path.exists(android_build_tmp_dir):
            os.mkdir(android_build_tmp_dir)

        # 复制为 .zip
        copied_file = os.path.join(android_build_tmp_dir, "tmp.zip")
        shutil.copyfile(os.path.join(eos_aar_dir, aar_file), copied_file)

        # 提取 libs
        zip = zipfile.ZipFile(copied_file)
        for f in zip.namelist():
            if f.startswith("jni"):
                zip.extract(f, android_build_tmp_dir)
        zip.close()

        lib_dir = os.path.join(android_build_tmp_dir, "jni", eos_android_arch)
        env.Append(LIBPATH=[lib_dir])
        env.Append(LIBS=["EOSSDK"])

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

    # Disable scons cache for source files
    env.NoCache(sources)

    complete_command = env.Command("complete", library, _on_complete)
    env.Depends(complete_command, library)
    env.Default(complete_command)

    env.GD_EOS_ADD_CLEAN_FILES(library)
    return library


_build_gd_eos(env)

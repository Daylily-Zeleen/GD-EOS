import os

from binding_generator.config import gen_include_dir
from binding_generator.context import generate_infos, interfaces
from binding_generator.utils.naming import (
    convert_handle_class_name,
    remove_backslash_of_last_line,
)


def gen_all_in_one():
    lines: list = []
    lines.append("#pragma once")
    lines.append("")

    register_classes_lines: list = [""]

    register_classes_lines.append("namespace godot::eos {")

    register_classes_lines.append("#define REGISTER_EOS_CLASSES()\\")
    register_singleton_lines: list = ["#define REGISTER_EOS_SINGLETONS()\\"]
    unregister_singleton_lines: list = ["#define UNREGISTER_EOS_SINGLETONS()\\"]

    handle_types: list = []
    for fbn in generate_infos:
        if len(generate_infos[fbn].handles) <= 0:
            continue

        handle_class: str = ""
        for h in generate_infos[fbn].handles:
            if h in ["EOS", "EOS_HAntiCheatCommon"]:
                break
            if h.removeprefix("EOS_H") in interfaces:
                handle_class = h
                break
        if len(handle_class):
            handle_types.append(handle_class)

        if fbn in ["eos_common", "eos_anticheatcommon"]:
            continue
        if fbn == "eos_sdk":
            fbn = "eos_platform"
        lines.append(f"#include <interfaces/{fbn}_interface.h>")

    handle_types.insert(0, "EOS_HAntiCheatCommon")
    handle_types.insert(0, "EOS")

    for handle_type in handle_types:
        handle_class: str = convert_handle_class_name(handle_type)
        register_classes_lines.append(f"\tEOS_REGISTER_{handle_class}\\")

        if handle_type in ["EOS", "EOS_HAntiCheatCommon"]:
            continue
        register_singleton_lines.append(
            f"\tgodot::Engine::get_singleton()->register_singleton(godot::eos::{handle_class}::get_class_static(), godot::eos::{handle_class}::get_singleton());\\"
        )
        if handle_type == "EOS_HPlatform":
            continue
        unregister_singleton_lines.append(f"\tgodot::Engine::get_singleton()->unregister_singleton(godot::eos::{handle_class}::get_class_static());\\")
        unregister_singleton_lines.append(f"\tmemdelete(godot::eos::{handle_class}::get_singleton());\\")

    unregister_singleton_lines.append(
        f"\tgodot::Engine::get_singleton()->unregister_singleton(godot::eos::{convert_handle_class_name('EOS_HPlatform')}::get_class_static());\\"
    )
    unregister_singleton_lines.append(f"\tmemdelete(godot::eos::{convert_handle_class_name('EOS_HPlatform')}::get_singleton());\\")
    remove_backslash_of_last_line(register_classes_lines)
    remove_backslash_of_last_line(register_singleton_lines)
    remove_backslash_of_last_line(unregister_singleton_lines)

    register_singleton_lines.append("")
    unregister_singleton_lines.append("")

    register_classes_lines.append("")
    register_classes_lines.append("} // namesapce godot")
    register_classes_lines.append("")

    f = open(os.path.join(gen_include_dir, "eos_interfaces.h"), "w")
    f.write("\n".join(lines + register_classes_lines + register_singleton_lines + unregister_singleton_lines))
    f.close()

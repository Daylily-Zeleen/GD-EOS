# EOS SDK 绑定代码生成器入口

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binding_generator.config import gen_include_dir, gen_src_dir, generate_config, sdk_include_dir
from binding_generator.context import generate_infos
from binding_generator.doc.doc_processor import preprocess_docs
from binding_generator.generator.all_in_one_generator import gen_all_in_one
from binding_generator.generator.interface_generator import gen_files
from binding_generator.resolver.handle_resolver import parse_all_file


def main(argv):
    for arg in argv:
        if arg in ["-h", "--help"]:
            print_help()
            print("You can override these options like this: min_field_count_to_expand_input_structs=5")
            exit()

        splits: list[str] = arg.split("=", 1)
        if len(splits) != 2:
            print(f"[main] 不支持的选项: '{arg}' (拆分结果: {splits})")
            print('[main] 使用 "-h" 或 "--help" 获取帮助')
            exit()

        arg_key = splits[0]
        arg_value = splits[1]

        if arg_key == "min_field_count_to_expand_input_structs":
            if not arg_value.isdecimal() or int(arg_value) < 0:
                print(f"[main] 无效的值: '{arg_value}' for '{arg_key}'")
                exit()
            generate_config.min_field_count_to_expand_input_structs = int(arg_value)
        elif arg_key == "min_field_count_to_expand_callback_structs":
            if not arg_value.isdecimal() or int(arg_value) < 0:
                print(f"[main] 无效的值: '{arg_value}' for '{arg_key}'")
                exit()
            generate_config.min_field_count_to_expand_callback_structs = int(arg_value)
        elif arg_key == "assume_only_one_local_user":
            if arg_value.lower() not in ["t", "true", "f", "false"]:
                print(f"[main] 无效的值: '{arg_value}' for '{arg_key}'")
                exit()
            generate_config.assume_only_one_local_user = arg_value.lower() in ["t", "true"]
        else:
            print(f"[main] 不支持的选项: '{arg}' (拆分结果: {splits})")
            print('[main] 使用 "-h" 或 "--help" 获取帮助')
            exit()

    generate_bindings()


def print_help():
    print('min_field_count_to_expand_input_structs: The min field count to expand input Options structs (except "ApiVersion" field).')
    print("\tdefault:3")
    print("")
    print("min_field_count_to_expand_callback_structs: The min field count to expand CallbackInfo structs.")
    print("\tdefault:1")
    print("")
    print('assume_only_one_local_user: If true, the code generator will hide all "LocalUserId" filed/argument and automatically fill them internally.')
    print("\tdefault:false")
    print("")


def generate_bindings(
    p_min_field_count_to_expand_input_structs: int | None = None,
    p_min_field_count_to_expand_callback_structs: int | None = None,
    p_assume_only_one_local_user: bool | None = None,
) -> None:
    if p_min_field_count_to_expand_input_structs is not None:
        generate_config.min_field_count_to_expand_input_structs = p_min_field_count_to_expand_input_structs
    if p_min_field_count_to_expand_callback_structs is not None:
        generate_config.min_field_count_to_expand_callback_structs = p_min_field_count_to_expand_callback_structs
    if p_assume_only_one_local_user is not None:
        generate_config.assume_only_one_local_user = p_assume_only_one_local_user

    for base_dir in [gen_include_dir, gen_src_dir]:
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        if not os.path.exists(os.path.join(base_dir, "enums")):
            os.makedirs(os.path.join(base_dir, "enums"))
        if not os.path.exists(os.path.join(base_dir, "structs")):
            os.makedirs(os.path.join(base_dir, "structs"))
        if not os.path.exists(os.path.join(base_dir, "packed_results")):
            os.makedirs(os.path.join(base_dir, "packed_results"))
        if not os.path.exists(os.path.join(base_dir, "handles")):
            os.makedirs(os.path.join(base_dir, "handles"))
        if not os.path.exists(os.path.join(base_dir, "interfaces")):
            os.makedirs(os.path.join(base_dir, "interfaces"))

    print("Parsing...")
    parse_all_file()
    print("Parse finished")

    preprocess_docs()
    print("preprocess documents finished.")

    for fbn in generate_infos:
        gen_files(fbn, generate_infos[fbn])
        print("Generated:", fbn)

    gen_all_in_one()
    print("Generate Completed!")


def preprocess():
    eos_base_file = os.path.join(sdk_include_dir, "eos_base.h")
    f = open(eos_base_file, "r")

    bck = open("./.eos_base.h.bak", "w")
    bck.write(f.read())
    bck.close()

    f.seek(0)
    lines: list = f.readlines()
    f.close()

    for i in range(len(lines)):
        line = lines[i]
        if "#define EOS_HAS_ENUM_CLASS" in line and not line.startswith("//"):
            lines[i] = "//" + line

    f = open(eos_base_file, "w")
    f.write("".join(lines))
    f.close()


def postprocess():
    eos_base_file = os.path.join(sdk_include_dir, "eos_base.h")
    backup_file = "./.eos_base.h.bak"
    if os.path.exists(backup_file):
        os.remove(eos_base_file)
        os.rename(backup_file, eos_base_file)


if __name__ == "__main__":
    main(sys.argv[1:])

# 代码生成器配置

import os

# 项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sdk_include_dir = os.path.join(project_root, "thirdparty", "eos-sdk", "SDK", "Include")

# 生成代码输出目录
gen_dir = os.path.join(project_root, "gd_eos/gen/")
gen_include_dir = os.path.join(gen_dir, "include")
gen_src_dir = os.path.join(gen_dir, "src")

eos_data_class_h_file = "core/eos_data_class.h"

# 结构体展开阈值（运行时可变，通过 generate_config 对象共享）
class _GenerateConfig:
    min_field_count_to_expand_input_structs: int = 3
    min_field_count_to_expand_callback_structs: int = 1
    assume_only_one_local_user: bool = False

generate_config = _GenerateConfig()

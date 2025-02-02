#!user/bin/python
# -*- coding: utf-8 -*-

import sys, os

if __name__ == "__main__":
    args = sys.argv[1:]

    os.makedirs(args[0], 0o777, True)

    flag_count: int = 0
    flag_file = args[1] + "_built_flag.txt"
    flag_file = os.path.join(args[0], flag_file)

    open(flag_file, "w").close()

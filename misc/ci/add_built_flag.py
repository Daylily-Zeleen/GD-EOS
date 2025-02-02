#!user/bin/python
# -*- coding: utf-8 -*-

import sys, os

if __name__ == "__main__":
    args = sys.argv[1:]

    flag_count: int = 0

    os.open(os.path.join(args[0], f"{args[1]}.built_flag"))

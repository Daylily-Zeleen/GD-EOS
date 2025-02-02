#!user/bin/python
# -*- coding: utf-8 -*-
import sys, os

if __name__ == "__main__":
    args = sys.argv[1:]

    flag_count: int = 0

    for f in os.listdir(args[0]):
        if f.endswith("_built_flag.txt"):
            if len(args) > 2:
                print("===: ", f)
            flag_count += 1

    if len(args) > 2:
        print("????: ", flag_count)
    if str(args[1]) == str(flag_count):
        print("BUILD_COMPLETED=true")
    else:
        print("BUILD_COMPLETED=false")

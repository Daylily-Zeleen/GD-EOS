#!user/bin/python
# -*- coding: utf-8 -*-
import sys, os, json

if __name__ == "__main__":
    args = sys.argv[1:]

    flag_count: int = 0

    for f in os.listdir(args[0]):
        if f.endswith(".built_flag"):
            flag_count += 1

    print(len(json.loads(args[1])) == flag_count)

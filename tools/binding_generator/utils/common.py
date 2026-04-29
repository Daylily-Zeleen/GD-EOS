def print_stack_and_exit(msg: str = ""):
    import traceback

    for line in traceback.format_stack():
        print(line)

    if len(msg) > 0:
        print(f"[Error]: {msg}")

    exit(1)


def assert_condition(condition: bool, msg: str = ""):
    if condition:
        return
    import traceback

    for line in traceback.format_stack():
        print(line)
    if len(msg) > 0:
        print(f"[Error] 断言失败: {msg}")
    else:
        print("[Error] 断言失败")
    exit(1)

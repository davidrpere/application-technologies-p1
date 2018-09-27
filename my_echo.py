import sys

sys.path.append("pycharm-debug-py3k.egg")

import pydevd

pydevd.settrace('localhost', port=12345, stdoutToServer=True, stderrToServer=True)

while True:
    input_msg = input("Tell me something...")
    if (input_msg) == "END":
        print("\n")
        break
    else:
        print(input_msg)

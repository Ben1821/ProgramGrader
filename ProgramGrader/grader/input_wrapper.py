"""執行學生程式的包裝：讓 input() 不印出提示文字，測資只比對真正的輸出。"""
import builtins
import resource
import runpy
import sys

# 輸出導向檔案，用檔案大小上限防止無限輸出塞爆磁碟（僅 POSIX）
MAX_OUTPUT_BYTES = 10 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))


def _input(prompt=''):
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    return line.rstrip('\r\n')


builtins.input = _input
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')

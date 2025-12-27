import subprocess
import time
import sys

def run_aliv3():
    cmd = ["python", "AliV3.py", "10754308A", "Aa123123"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # 实时打印 AliV3.py 的输出
    for line in process.stdout:
        print(line.strip())

    process.wait()
    print("AliV3.py 运行结束，退出码:", process.returncode)


if __name__ == "__main__":
    # 第 1 次运行
    print("开始第 1 次运行")
    run_aliv3()

    # 等 30 秒
    print("等待 30 秒后进行第 2 次运行")
    time.sleep(30)

    # 第 2 次运行
    print("开始第 2 次运行")
    run_aliv3()

    # 再等 30 秒
    print("等待 10 秒后进行第 3 次运行")
    time.sleep(10)

    # 第 3 次运行
    print("开始第 3 次运行")
    run_aliv3()

    # 等 20 分钟
    print("等待 20 分钟后进行最后 1 次运行")
    time.sleep(20 * 60)

    # 第 4 次（最后一次）
    print("开始最后一次运行")
    run_aliv3()

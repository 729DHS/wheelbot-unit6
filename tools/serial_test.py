"""
serial_test.py — 串口 Shell 命令发送器

通过串口向 Unit5 固件发送 Shell 命令并读取响应。

用法:
  python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor status"
  python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "robot cali"
  python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "balance enable"

依赖: pip install pyserial
"""

import argparse
import serial
import sys
import time


def send_cmd(port: str, baud: int, cmd: str, timeout: float = 3.0) -> str:
    """发送 Shell 命令并返回响应文本。"""
    ser = serial.Serial(port, baud, timeout=timeout)
    time.sleep(0.3)  # 等待串口稳定

    # 清空缓冲区
    ser.reset_input_buffer()

    # 发送命令 (Shell 需要 \r\n 换行)
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()

    # 读取响应
    time.sleep(timeout)
    response = ""
    while ser.in_waiting > 0:
        try:
            chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
            response += chunk
        except Exception:
            break

    ser.close()
    return response


def main():
    parser = argparse.ArgumentParser(description="Unit5 Shell 命令发送器")
    parser.add_argument("--port", default="/dev/ttyACM0", help="串口设备路径")
    parser.add_argument("--baud", type=int, default=115200, help="波特率")
    parser.add_argument("--cmd", required=True, help="要执行的 Shell 命令")
    parser.add_argument("--timeout", type=float, default=3.0, help="响应等待时间(s)")
    args = parser.parse_args()

    print(f"[serial_test] 连接 {args.port} @ {args.baud}")
    print(f"[serial_test] 命令: {args.cmd}")
    print("-" * 60)

    try:
        resp = send_cmd(args.port, args.baud, args.cmd, args.timeout)
        print(resp)
    except serial.SerialException as e:
        print(f"[ERROR] 串口错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[serial_test] 用户中断")
        sys.exit(0)


if __name__ == "__main__":
    main()

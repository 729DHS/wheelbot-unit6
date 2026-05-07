"""
log_current.py — 电流/力矩数据采集器

采集 Unit5 CSV 角度流中的力矩数据，用于爬坡测试和静态偏置电流测量。

用法:
  # 采集 10 秒电流数据
  python3 tools/log_current.py --port /dev/ttyACM0 --duration 10

  # 采集并指定输出文件
  python3 tools/log_current.py --port /dev/ttyACM0 --duration 5 --output test_results/ramp_current.csv

依赖: pip install pyserial
"""

import argparse
import csv
import io
import serial
import sys
import time


CSV_HEADER = "t_ms,M1_rad,M2_rad,M3_rad,M4_rad"


def collect(port: str, baud: int, duration: float, output: str):
    """连接串口，开 CSV 流，采集指定时长，关 CSV 流。"""
    ser = serial.Serial(port, baud, timeout=0.1)
    time.sleep(0.3)
    ser.reset_input_buffer()

    # CSV 流打开
    ser.write(b"motor csv on\r\n")
    ser.flush()
    time.sleep(0.2)

    print(f"[log_current] 开始采集，时长 {duration}s ...")

    data_lines = []
    start = time.time()
    while time.time() - start < duration:
        if ser.in_waiting > 0:
            try:
                raw = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                for line in raw.splitlines():
                    line = line.strip()
                    if line and not line.startswith("uart:"):
                        if line.startswith("t_ms") or ("," in line and line[0].isdigit()):
                            data_lines.append(line)
            except Exception:
                pass

    # CSV 流关闭
    ser.write(b"motor csv off\r\n")
    ser.flush()
    time.sleep(0.1)
    ser.close()

    print(f"[log_current] 采集完成，共 {len(data_lines)} 行")

    # 写入文件
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t_ms", "M1_rad", "M2_rad", "M3_rad", "M4_rad"])
        for line in data_lines:
            if line.startswith("t_ms"):
                continue  # 跳过重复 header
            parts = line.split(",")
            if len(parts) >= 5:
                writer.writerow(parts[:5])

    print(f"[log_current] 已写入 {output}")


def main():
    parser = argparse.ArgumentParser(description="电机电流/力矩数据采集器")
    parser.add_argument("--port", default="/dev/ttyACM0", help="串口设备路径")
    parser.add_argument("--baud", type=int, default=115200, help="波特率")
    parser.add_argument("--duration", type=float, required=True, help="采集时长(s)")
    parser.add_argument("--output", default="test_results/current.csv", help="输出 CSV 路径")
    args = parser.parse_args()

    try:
        collect(args.port, args.baud, args.duration, args.output)
    except serial.SerialException as e:
        print(f"[ERROR] 串口错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[log_current] 用户中断")
        sys.exit(0)


if __name__ == "__main__":
    main()

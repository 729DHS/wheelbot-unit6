"""
test_static_tracking.py — 静态位置跟踪误差测试

执行任务 A: 在不同目标高度测试运动学逆解精度。

用法:
  python3 tools/test_static_tracking.py --port /dev/ttyACM0
  python3 tools/test_static_tracking.py --port /dev/ttyACM0 --heights 150,100
  python3 tools/test_static_tracking.py --port /dev/ttyACM0 --output test_results/2026-05-07_tracking/

依赖: pip install pyserial numpy
"""

import argparse
import csv
import math
import os
import serial
import sys
import time

# 运动学参数 (与运动学 Agent 保持一致)
L1 = 107.4  # mm, 大腿
L2 = 128.0  # mm, 小腿


def forward_kinematics(theta1: float, theta2: float) -> tuple[float, float]:
    """2R 等效正运动学: 关节角 → 末端位置 (x, y)。腿平面。"""
    x = L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    y = L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2)
    return x, y


def compute_height(theta1_L: float, theta2_L: float,
                   theta1_R: float, theta2_R: float) -> float:
    """从四条腿的关节角估算车体高度。

    简化: 取左右腿末端 y 坐标的均值作为车体高度。
    """
    _, y_L = forward_kinematics(theta1_L, theta2_L)
    _, y_R = forward_kinematics(theta1_R, theta2_R)
    return (y_L + y_R) / 2.0


def send_cmd(ser: serial.Serial, cmd: str, delay: float = 0.5):
    """通过已打开的串口发送命令。"""
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()
    time.sleep(delay)


def collect_steady_angles(ser: serial.Serial, n_frames: int = 20) -> list[list[float]]:
    """采集 n_frames 帧稳态角度数据。返回 [[t, m1, m2, m3, m4], ...]"""
    frames = []
    ser.reset_input_buffer()
    start = time.time()
    while len(frames) < n_frames and time.time() - start < 5.0:
        if ser.in_waiting > 0:
            try:
                raw = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("t_ms") or not line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 5:
                        try:
                            frames.append([float(p) for p in parts[:5]])
                        except ValueError:
                            pass
            except Exception:
                pass
    return frames


def run_test(port: str, baud: int, heights: list[int], output_dir: str):
    """执行完整静态跟踪测试。"""
    os.makedirs(output_dir, exist_ok=True)

    ser = serial.Serial(port, baud, timeout=0.1)
    time.sleep(0.3)
    ser.reset_input_buffer()

    # Step 1: 标定
    print("[test] 执行 robot cali ...")
    send_cmd(ser, "robot cali", delay=2.0)

    # Step 2: 开 CSV 流
    print("[test] 开启 CSV 流 ...")
    send_cmd(ser, "motor csv on", delay=0.3)

    results = []
    for h_target in heights:
        print(f"\n[test] 目标高度 {h_target}mm ...")
        send_cmd(ser, f"robot move_h {h_target}", delay=3.0)

        # 采集稳态角度
        frames = collect_steady_angles(ser, n_frames=20)
        if not frames:
            print(f"  [WARN] 未采集到数据，跳过 {h_target}mm")
            continue

        # 保存原始数据
        csv_path = os.path.join(output_dir, f"h_{h_target}_angles.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["t_ms", "M1_rad", "M2_rad", "M3_rad", "M4_rad"])
            writer.writerows(frames)

        # 计算实际高度
        h_actuals = []
        for frame in frames:
            _, m1, m2, m3, m4 = frame
            h_act = compute_height(m1, m2, m3, m4)
            h_actuals.append(h_act)

        h_mean = sum(h_actuals) / len(h_actuals)
        error = h_mean - h_target

        print(f"  实际高度: {h_mean:.2f}mm, 误差: {error:+.2f}mm")
        status = "PASS" if abs(error) < 3.0 else "FAIL"
        print(f"  判定: {status}")

        results.append({
            "h_target": h_target,
            "h_actual_mean": round(h_mean, 2),
            "error_mm": round(error, 2),
            "status": status,
        })

    # Step 3: 关 CSV 流
    send_cmd(ser, "motor csv off", delay=0.2)
    ser.close()

    # 写汇总报告
    report_path = os.path.join(output_dir, "error_report.md")
    with open(report_path, "w") as f:
        f.write("# 静态跟踪误差报告\n\n")
        f.write(f"| h_target (mm) | h_actual (mm) | error (mm) | 判定 |\n")
        f.write(f"|---------------|---------------|------------|------|\n")
        for r in results:
            f.write(f"| {r['h_target']} | {r['h_actual_mean']} | {r['error_mm']:+} | {r['status']} |\n")

        all_pass = all(r["status"] == "PASS" for r in results)
        if not all_pass:
            f.write("\n## ⚠️ 连杆参数需微调\n")
            f.write("通知运动学 Agent 微调 L1、L2。\n")
            for r in results:
                if r["status"] == "FAIL":
                    f.write(f"- h={r['h_target']}mm: 偏差 {r['error_mm']:+.1f}mm\n")

    print(f"\n[test] 测试完成，报告: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="静态位置跟踪误差测试 (任务 A)")
    parser.add_argument("--port", default="/dev/ttyACM0", help="串口设备路径")
    parser.add_argument("--baud", type=int, default=115200, help="波特率")
    parser.add_argument("--heights", default="150,100", help="测试高度列表 (逗号分隔, mm)")
    parser.add_argument("--output", default="test_results/tracking", help="输出目录")
    args = parser.parse_args()

    heights = [int(h) for h in args.heights.split(",")]

    try:
        run_test(args.port, args.baud, heights, args.output)
    except serial.SerialException as e:
        print(f"[ERROR] 串口错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[test] 用户中断")
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
        time.sleep(0.2)
        ser.write(b"motor csv off\r\n")
        ser.write(b"motor disable all\r\n")
        ser.close()
        sys.exit(0)


if __name__ == "__main__":
    main()

"""
stage0_mapping.py — Stage 0 冷机手推映射测试记录
用法: python3 tools/stage0_mapping.py --port /dev/ttyACM0 --duration 120

采集手推过程中的角度/力矩/h/φ 到 CSV，用于事后与数字孪生对比。
"""
import argparse, csv, math, os, re, serial, sys, time
from datetime import datetime

L1 = 107.4
L2 = 128.0


def fk(theta_a, theta_b):
    Px = L1 * math.cos(theta_a) + L2 * math.cos(theta_b)
    Py = L1 * math.sin(theta_a) + L2 * math.sin(theta_b)
    h = math.sqrt(Px * Px + Py * Py)
    phi = -math.atan2(Py, Px) - math.pi / 2.0
    return h, phi


def main():
    p = argparse.ArgumentParser(description="Stage 0 手推映射测试记录")
    p.add_argument("--port", default="/dev/ttyACM0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--duration", type=float, default=120, help="采集时长(s)")
    p.add_argument("--output", default=None)
    args = p.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = args.output or f"test_results/{ts}_stage0"
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, "mapping.csv")
    log_path = os.path.join(outdir, "stage0_log.txt")

    ser = serial.Serial(args.port, args.baud, timeout=0.05)
    time.sleep(0.3)
    ser.reset_input_buffer()

    ser.write(b"motor csv on\r\n")
    ser.flush()
    time.sleep(0.3)

    ansi = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    buf = ""
    rows = []
    t0 = None
    start = time.time()

    print("=" * 70)
    print("  Stage 0: 冷机手推映射测试")
    print(f"  采集时长: {args.duration}s | 输出: {csv_path}")
    print("=" * 70)
    print("  检查项:")
    print("    1. 压低 → h 减小")
    print("    2. 上抬 → h 增大")
    print("    3. 前倾 → phi 正值")
    print("    4. 后仰 → phi 负值")
    print("    5. 左右 h 对称差 <5mm")
    print("    6. 角度无跳变 (>0.1rad/帧)")
    print("    7. 力矩 <0.05Nm (idle)")
    print("-" * 70)

    try:
        while time.time() - start < args.duration:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    clean = ansi.sub('', line).strip()
                    clean = clean.replace('uart:~$ ', '')
                    parts = clean.split(",")
                    if len(parts) >= 9 and parts[0].lstrip().isdigit():
                        try:
                            t_ms = int(parts[0])
                            m1 = float(parts[1])
                            m2 = float(parts[2])
                            m3 = float(parts[3])
                            m4 = float(parts[4])
                            t1 = float(parts[5])
                            t2 = float(parts[6])
                            t3 = float(parts[7])
                            t4 = float(parts[8])

                            if t0 is None:
                                t0 = t_ms
                            hL, phiL = fk(m1, m2)
                            hR, phiR = fk(m4, m3)

                            row = [
                                t_ms, m1, m2, m3, m4, t1, t2, t3, t4,
                                round(hL, 2), round(phiL, 4),
                                round(hR, 2), round(phiR, 4),
                            ]
                            rows.append(row)

                            # Live check: jump detection
                            if len(rows) >= 2:
                                prev = rows[-2]
                                for i, name in [(1, "M1"), (2, "M2"), (3, "M3"), (4, "M4")]:
                                    jump = abs(row[i] - prev[i])
                                    if jump > 0.1:
                                        t = (t_ms - t0) / 1000.0
                                        print(f"  ⚠️  t={t:.1f}s {name} 跳变 {jump:+.3f}rad")

                        except (ValueError, IndexError):
                            pass
            else:
                time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n  用户中断")
    finally:
        ser.write(b"motor csv off\r\n")
        ser.flush()
        time.sleep(0.1)
        ser.close()

    # Write CSV
    header = [
        "t_ms", "M1_rad", "M2_rad", "M3_rad", "M4_rad",
        "T1_Nm", "T2_Nm", "T3_Nm", "T4_Nm",
        "hL_mm", "phiL_rad", "hR_mm", "phiR_rad",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    # Analyze
    if rows:
        hL_vals = [r[9] for r in rows]
        hR_vals = [r[11] for r in rows]
        phiL_vals = [r[10] for r in rows]
        phiR_vals = [r[12] for r in rows]
        t_vals = [r[5] + r[6] + r[7] + r[8] for r in rows]

        with open(log_path, "w") as f:
            f.write(f"Stage 0 映射测试日志 — {ts}\n")
            f.write(f"总帧数: {len(rows)}\n")
            f.write(f"hL 范围: {min(hL_vals):.1f} ~ {max(hL_vals):.1f} mm\n")
            f.write(f"hR 范围: {min(hR_vals):.1f} ~ {max(hR_vals):.1f} mm\n")
            f.write(f"φL 范围: {min(phiL_vals):.2f} ~ {max(phiL_vals):.2f} rad\n")
            f.write(f"φR 范围: {min(phiR_vals):.2f} ~ {max(phiR_vals):.2f} rad\n")
            f.write(f"平均绝对力矩: {sum(abs(v) for v in t_vals)/len(t_vals):.4f} Nm\n")

        print(f"\n  总帧数: {len(rows)}")
        print(f"  hL: {min(hL_vals):.1f} ~ {max(hL_vals):.1f} mm")
        print(f"  hR: {min(hR_vals):.1f} ~ {max(hR_vals):.1f} mm")
        print(f"  已写入: {csv_path}")
        print(f"  日志:   {log_path}")

    print("\n  请对照数字孪生检查:")
    print("    twin_display.py 中左右腿姿态是否与实际一致")
    print("    压低/上台/前倾/后仰方向是否匹配")


if __name__ == "__main__":
    main()

"""
robot_viz.py — 映射验证可视化: 角度 → h/phi 正运动学
用法: python3 tools/robot_viz.py --port /dev/ttyACM0
与固件 lk_forward() 公式一致
"""
import argparse, math, re, serial, sys, time

L1 = 107.4  # mm
L2 = 128.0  # mm

def fk(theta_a, theta_b):
    """正运动学 (与 linkage_kinematics.c lk_forward 一致)"""
    Px = L1 * math.cos(theta_a) + L2 * math.cos(theta_b)
    Py = L1 * math.sin(theta_a) + L2 * math.sin(theta_b)
    h  = math.sqrt(Px * Px + Py * Py)
    phi = -math.atan2(Py, Px) - math.pi / 2.0
    return h, phi

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/ttyACM0")
    p.add_argument("--interval", type=float, default=0.2, help="刷新间隔(s)")
    args = p.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=0.05)
    time.sleep(0.3)
    ser.reset_input_buffer()
    ser.write(b"motor csv on\r\n")
    ser.flush()
    time.sleep(0.3)

    ansi = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    buf = ""
    last_t = 0
    latest = None  # (t, m1, m2, m3, m4)

    try:
        # Print header once
        print("\033[2J\033[H", end="")
        print("=" * 78)
        print("  M1°(θaL) M2°(θbL) | M3°(θaR) M4°(θbR) |  hL mm  φL°  |  hR mm  φR°")
        print("-" * 78)

        while True:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    clean = ansi.sub('', line).strip()
                    # strip shell prompt prefix
                    clean = clean.replace('uart:~$ ', '')
                    parts = clean.split(",")
                    if len(parts) == 12 and parts[0].lstrip().isdigit():
                        try:
                            t = int(parts[0])
                            m1 = float(parts[1])
                            m2 = float(parts[2])
                            m3 = float(parts[3])
                            m4 = float(parts[4])
                            latest = (t, m1, m2, m3, m4)
                            # Update display every interval seconds
                            if (t - last_t) / 1000.0 >= args.interval:
                                last_t = t
                                hL, phiL = fk(m1, m2)
                                hR, phiR = fk(m4, m3)  # M4=θaR, M3=θbR (右腿对调)
                                phiL_deg = phiL * 180.0 / math.pi
                                phiR_deg = phiR * 180.0 / math.pi
                                m1d = m1 * 180.0 / math.pi
                                m2d = m2 * 180.0 / math.pi
                                m3d = m3 * 180.0 / math.pi
                                m4d = m4 * 180.0 / math.pi
                                print(f"\033[K {m1d:+7.1f}°{m2d:+7.1f}° |"
                                      f" {m3d:+7.1f}°{m4d:+7.1f}° |"
                                      f" {hL:6.1f} {phiL_deg:+6.1f} |"
                                      f" {hR:6.1f} {phiR_deg:+6.1f}")
                                sys.stdout.flush()
                        except (ValueError, IndexError):
                            pass
            else:
                time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        ser.write(b"motor csv off\r\n")
        ser.flush()
        time.sleep(0.1)
        ser.close()
        if latest:
            t, m1, m2, m3, m4 = latest
            hL, phiL = fk(m1, m2)
            hR, phiR = fk(m3, m4)
            print(f"\n--- 最终值 ---")
            print(f"M1={m1*180/math.pi:+.1f}° M2={m2*180/math.pi:+.1f}° M3={m3*180/math.pi:+.1f}° M4={m4*180/math.pi:+.1f}°")
            print(f"hL={hL:.1f} φL={phiL*180/math.pi:+.1f}°  hR={hR:.1f} φR={phiR*180/math.pi:+.1f}°")
            print(f"h 对称差: {abs(hL-hR):.1f}mm  φ 对称差: {abs(phiL+phiR)*180/math.pi:.1f}°")
        print("已停止")

if __name__ == "__main__":
    main()

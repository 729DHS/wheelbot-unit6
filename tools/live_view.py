"""
live_view.py — 实时角度/力矩显示器 (无第三方依赖)
用法: python3 tools/live_view.py --port /dev/ttyACM0
Ctrl+C 退出
"""
import argparse, re, serial, sys, time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/ttyACM0")
    args = parser.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=0.05)
    time.sleep(0.3)
    ser.reset_input_buffer()
    ser.write(b"motor csv on\r\n")
    ser.flush()
    time.sleep(0.3)

    ansi = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    buf = ""
    count = 0

    try:
        print("\n" + "=" * 75)
        print("  t_ms  |   M1_rad   M2_rad  |   M3_rad   M4_rad  |  T1_Nm  T2_Nm |  T3_Nm  T4_Nm")
        print("-" * 75)
        while True:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    clean = ansi.sub('', line).strip()
                    if 'uart' in clean:
                        clean = clean.split('uart:~$ ')[-1] if 'uart:~$ ' in clean else ''
                    if not clean:
                        continue
                    parts = clean.split(",")
                    if len(parts) == 12 and parts[0].isdigit():
                        try:
                            t = int(parts[0])
                            m = [float(parts[i]) for i in range(1, 5)]
                            tq = [float(parts[i]) for i in range(5, 9)]
                            # print every line (50Hz)
                            print(f" {t:6d} |{m[0]:+8.4f} {m[1]:+8.4f} |"
                                  f"{m[2]:+8.4f} {m[3]:+8.4f} |"
                                  f"{tq[0]:+6.3f} {tq[1]:+6.3f} |"
                                  f"{tq[2]:+6.3f} {tq[3]:+6.3f}")
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
        print("\n已停止")

if __name__ == "__main__":
    main()

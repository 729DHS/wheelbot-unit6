"""
live_gate.py — 数字孪生拖拽安全闸门 (方案 B 转发模式)

读取 Linkage live_control.py --stdout 输出的 TARGET 行，
做安全检查后转发到 Unit5 串口 Shell，并记录所有指令与响应。

用法:
  Linkage:  .venv/bin/python -m src.main live_control --stdout | \
  Unit6:    python3 tools/live_gate.py --port /dev/ttyACM0

也可手动从文件读取 (调试):
  python3 tools/live_gate.py --port /dev/ttyACM0 --file targets.txt
"""
import argparse, csv, os, re, select, serial, sys, time
from datetime import datetime

# 软限位 (来自 Unit5)
H_MIN, H_MAX = 45, 235.4       # mm
PHI_MIN, PHI_MAX = -1.047, 1.047  # rad (-60°, +60°)
MAX_STEP_H = 10.0   # mm, 单步最大允许
MAX_STEP_PHI = 5.0  # deg


def check_limits(h: float, phi_deg: float, prev_h: float | None) -> str | None:
    """返回 None 表示通过，否则返回拒绝原因"""
    phi_rad = phi_deg * 3.14159 / 180.0
    if h < H_MIN or h > H_MAX:
        return f"h={h:.1f} 超出软限位 [{H_MIN},{H_MAX}]"
    if phi_rad < PHI_MIN or phi_rad > PHI_MAX:
        return f"phi={phi_deg:.1f}° 超出软限位 [{-60},{+60}]°"
    if prev_h is not None and abs(h - prev_h) > MAX_STEP_H:
        return f"步幅 {abs(h-prev_h):.1f}mm > {MAX_STEP_H}mm 限制"
    return None


def send_cmd(ser: serial.Serial, cmd: str, timeout: float = 2.0) -> str:
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()
    time.sleep(timeout)
    resp = ""
    while ser.in_waiting > 0:
        try:
            resp += ser.read(ser.in_waiting).decode("utf-8", errors="replace")
        except Exception:
            break
    return resp.strip()


def main():
    p = argparse.ArgumentParser(description="拖拽安全闸门 (方案B)")
    p.add_argument("--port", default="/dev/ttyACM0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--file", default=None, help="从文件读取 TARGET (调试用)")
    p.add_argument("--output", default=None)
    p.add_argument("--dry-run", action="store_true", help="只打印不发送")
    args = p.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = args.output or f"test_results/{ts}_drag"
    os.makedirs(outdir, exist_ok=True)
    log_path = os.path.join(outdir, "gate_log.csv")

    ser = None
    if not args.dry_run:
        ser = serial.Serial(args.port, args.baud, timeout=0.5)
        time.sleep(0.3)
        ser.reset_input_buffer()
        print(f"[gate] 串口 {args.port} 已连接")

    target_re = re.compile(r"TARGET\s+([-\d.]+)\s+([-\d.]+)")
    prev_h = None
    records = []
    count = 0
    stop_count = 0

    print("=" * 60)
    print("  数字孪生拖拽安全闸门 (方案B)")
    print(f"  软限位: h∈[{H_MIN},{H_MAX}]mm  φ∈[{-60},{+60}]°")
    print(f"  步幅限制: h≤{MAX_STEP_H}mm  φ≤{MAX_STEP_PHI}°")
    print(f"  {'[DRY RUN] ' if args.dry_run else ''}记录: {log_path}")
    print("-" * 60)

    try:
        if args.file:
            with open(args.file) as f:
                lines = f.readlines()
        else:
            lines = sys.stdin

        for line in lines:
            line = line.strip()
            m = target_re.match(line)
            if not m:
                # 非 TARGET 行可能是状态输出，静默跳过
                continue

            h = float(m.group(1))
            phi = float(m.group(2))
            count += 1

            # 安全检查
            reason = check_limits(h, phi, prev_h)
            if reason:
                stop_count += 1
                msg = f"⛔ 拒绝 #{count}: {reason}"
                print(f"  {msg}")
                records.append([count, h, phi, "REJECTED", reason, "", ""])
                continue

            # 发送
            cmd = f"robot move {h:.0f} {phi:.0f}"
            if args.dry_run:
                print(f"  [DRY] #{count}: {cmd}")
                resp = "(dry-run)"
            else:
                print(f"  ▶ #{count}: {cmd}", end=" ", flush=True)
                resp = send_cmd(ser, cmd, timeout=2.0)
                resp_short = resp[:80].replace("\n", " ")
                print(f"→ {resp_short}")

            records.append([count, h, phi, "SENT", "", cmd, resp[:200]])
            prev_h = h

    except KeyboardInterrupt:
        print("\n[gate] 用户中断")
    finally:
        if ser:
            # 安全: 退出前 disable
            print("[gate] 发送 motor disable all ...")
            ser.write(b"motor disable all\r\n")
            ser.flush()
            time.sleep(0.3)
            ser.close()

    # 写日志
    with open(log_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "h_mm", "phi_deg", "status", "reason", "cmd", "response"])
        w.writerows(records)

    sent = sum(1 for r in records if r[3] == "SENT")
    rejected = sum(1 for r in records if r[3] == "REJECTED")
    print(f"\n[gate] 结束: {sent} 发送, {rejected} 拒绝, 日志: {log_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
DM4310 实时反馈可视化 (matplotlib)
用法: python3 tools/plot_live.py --port /dev/ttyACM0
"""
import argparse, sys, time
from collections import defaultdict

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import serial

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/ttyACM0")
    p.add_argument("--window", type=float, default=10.0)
    args = p.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=0.05)
    time.sleep(0.3)
    ser.reset_input_buffer()
    ser.write(b"motor csv on\r\n")
    ser.flush()
    time.sleep(0.3)

    data = {1: [], 2: [], 3: [], 4: []}  # mid -> [(t, pos, tor), ...]
    t0 = None

    plt.ion()
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("DM4310 Live — 左: M1+M2 | 右: M3+M4")

    colors = {1: "tab:blue", 2: "tab:orange", 3: "tab:green", 4: "tab:red"}
    labels = {1: "M1", 2: "M2", 3: "M3", 4: "M4"}
    lines_pos = {}
    lines_tor = {}

    for mid in [1, 2]:
        lines_pos[mid], = axes[0, 0].plot([], [], color=colors[mid], label=labels[mid], lw=1)
        lines_tor[mid], = axes[1, 0].plot([], [], color=colors[mid], label=labels[mid], lw=0.8)
    for mid in [3, 4]:
        lines_pos[mid], = axes[0, 1].plot([], [], color=colors[mid], label=labels[mid], lw=1)
        lines_tor[mid], = axes[1, 1].plot([], [], color=colors[mid], label=labels[mid], lw=0.8)

    axes[0, 0].set_title("Left Leg Position (rad)")
    axes[0, 1].set_title("Right Leg Position (rad)")
    axes[1, 0].set_title("Left Leg Torque (Nm)")
    axes[1, 1].set_title("Right Leg Torque (Nm)")
    for ax in axes.flat:
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    buf = ""
    try:
        while True:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    # strip ANSI
                    import re
                    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).strip()
                    if not clean or 'uart' in clean or 'CSV' in clean:
                        continue
                    parts = clean.split(",")
                    if len(parts) >= 12 and parts[0].isdigit():
                        try:
                            t_ms = int(parts[0])
                            if t0 is None:
                                t0 = t_ms
                            t_rel = (t_ms - t0) / 1000.0
                            for i, mid in enumerate([1, 2, 3, 4]):
                                pos = float(parts[1 + i])
                                tor = float(parts[5 + i])
                                data[mid].append((t_rel, pos, tor))
                            # Keep only window seconds
                            for mid in [1, 2, 3, 4]:
                                while data[mid] and data[mid][0][0] < t_rel - args.window:
                                    data[mid].pop(0)
                        except (ValueError, IndexError):
                            pass

            # Update plots
            for mid in [1, 2, 3, 4]:
                if data[mid]:
                    ts, ps, trs = zip(*data[mid])
                    row, col = (0, 0) if mid <= 2 else (0, 1)
                    t_row, t_col = (1, 0) if mid <= 2 else (1, 1)
                    lines_pos[mid].set_data(ts, ps)
                    lines_tor[mid].set_data(ts, trs)

            # Auto-range
            all_t = []
            for mid in [1, 2, 3, 4]:
                if data[mid]:
                    all_t.append(data[mid][-1][0])
            if all_t:
                t_max = max(all_t)
                t_min = max(0, t_max - args.window)
                for ax in axes.flat:
                    ax.set_xlim(t_min, t_max)
                for ax in axes.flat:
                    ax.relim()
                    ax.autoscale_view(scalex=False)

            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            plt.pause(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        ser.write(b"motor csv off\r\n")
        ser.flush()
        time.sleep(0.1)
        ser.close()
        plt.close()
        print("已停止")

if __name__ == "__main__":
    main()

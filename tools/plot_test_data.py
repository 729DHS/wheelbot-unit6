"""
plot_test_data.py — 测试数据可视化

绘制 CSV 测试数据的角度或力矩波形。

用法:
  python3 tools/plot_test_data.py --file test_results/tracking/h_150_angles.csv
  python3 tools/plot_test_data.py --file test_results/current.csv --mode torque
"""

import argparse
import csv
import sys

import matplotlib.pyplot as plt
import numpy as np


def plot_angles(csv_path: str):
    """绘制角度波形 (4 台电机)。"""
    t, m1, m2, m3, m4 = [], [], [], [], []
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) < 5:
                continue
            try:
                t.append(float(row[0]) / 1000.0)  # ms → s
                m1.append(float(row[1]))
                m2.append(float(row[2]))
                m3.append(float(row[3]))
                m4.append(float(row[4]))
            except ValueError:
                continue

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, data, label in [
        (axes[0, 0], m1, "M1 (CAN1/左前)"),
        (axes[0, 1], m2, "M2 (CAN1/左后)"),
        (axes[1, 0], m3, "M3 (CAN2/右前)"),
        (axes[1, 1], m4, "M4 (CAN2/右后)"),
    ]:
        ax.plot(t, data, linewidth=0.8)
        ax.set_title(label)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Angle (rad)")
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"Angle Data: {csv_path}")
    plt.tight_layout()
    plt.show()


def plot_torque(csv_path: str):
    """绘制力矩波形 (角度变化率 = 速度 ≈ 力矩参考)。"""
    t, m1, m2, m3, m4 = [], [], [], [], []
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) < 5:
                continue
            try:
                t.append(float(row[0]) / 1000.0)
                m1.append(float(row[1]))
                m2.append(float(row[2]))
                m3.append(float(row[3]))
                m4.append(float(row[4]))
            except ValueError:
                continue

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, data, label in [
        (axes[0, 0], m1, "M1"),
        (axes[0, 1], m2, "M2"),
        (axes[1, 0], m3, "M3"),
        (axes[1, 1], m4, "M4"),
    ]:
        ax.plot(t, data, linewidth=0.8)
        ax.set_title(label)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Angle (rad)")
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"Torque Reference: {csv_path}")
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="测试数据可视化")
    parser.add_argument("--file", required=True, help="CSV 文件路径")
    parser.add_argument("--mode", choices=["angle", "torque"], default="angle", help="绘图模式")
    args = parser.parse_args()

    if args.mode == "torque":
        plot_torque(args.file)
    else:
        plot_angles(args.file)


if __name__ == "__main__":
    main()

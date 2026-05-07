# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Unit6 — DM4310 双足机器人单测验证项目。** 本项目是测试 Agent，不包含固件代码。核心职责是验证【运动学 Agent (Linkage)】的逆解精度和【控制 Agent (Unit5)】的驱动稳定性。

**被测对象:**
- **控制 Agent (Unit5)**: `/home/huiming/Desktop/Projects/Unit5` — DM4310 电机固件，运行于 STM32F407IG，通过串口 Shell + GDB 交互控制电机
- **运动学 Agent (Linkage, 同事 AI)**: 负责五连杆正逆运动学解算，提供 `robot cali`、`robot move_h` 等命令

**通信方式:**
- 通过 Unit5 串口 Shell 发出 `motor`/`balance`/`robot` 命令
- 通过 Unit5 GDB 批处理工具 (`tools/gdb_motor.py`) 读取状态
- CSV 角度流用于实时数据采集

## 串口参数

- **设备**: `/dev/ttyACM0` (CMSIS-DAP) 或 `/dev/ttyUSB0` (CH340)
- **波特率**: 115200, 8N1
- **换行符**: `\r\n` (CRLF) — 所有 Shell 命令必须以 `\r\n` 结尾
- **互斥**: 同一时刻只能有一个进程连接串口 (Shell 交互和 CSV 流互斥)

## 核心任务

### 任务 A: 静态位置跟踪误差测试 (Static Tracking Test)
验证运动学 Agent 的逆解精度。
- 操作: `robot move_h 150` → `robot move_h 100`
- 观察: 测量实际高度 h，与指令值对比
- 判定: 若偏差 >3mm，连杆长度参数 L1/L2 有偏置，需通知运动学 Agent 微调

### 任务 B: KP 爬坡稳定性测试 (The "Hum" Test)
验证控制 Agent 的驱动稳定性。
- 操作: `balance enable`，手扶机器人
- 观察: 500ms 爬坡过程中电机是否有高频啸叫
- 判定: 若啸叫，KP=80 太硬，记录临界 KP 值

### 任务 C: Pitch 触发保护测试 (Safety Trigger)
验证安全保护逻辑。
- 操作: enable 状态下，手动倾斜车体 >30°
- 观察: 电机是否瞬间 DISABLE（变软）
- 注意: 未断电严禁落地！

## 经理指令清单

| # | 指令 | 工具 | 状态 |
|---|------|------|------|
| 1 | 验证 `robot cali` 能否正确消除安装误差 | serial_test.py + CSV 对比 | ⬜ 待执行 |
| 2 | 平衡爬坡期间的电流跳变检查 | log_current.py | ⬜ 待执行 |
| 3 | elbow-down 模式下连杆干涉验证 | test_static_tracking.py + h=30mm | ⬜ 待执行 |
| 4 | 不同 h 下的静态偏置电流记录 | log_current.py + 多高度循环 | ⬜ 待执行 |

## 与被测系统的接口

### Unit5 串口 Shell 命令

```
motor enable <1-4|all>    使能电机
motor disable <1-4|all>   失能电机
motor zero <1-4|all>      设置零点
motor csv on/off/once     角度流开关
motor status              电机状态
motor kp <1-4> <v>        KP 增益
motor kd <1-4> <v>        KD 增益
balance enable [ticks]    平衡爬坡
balance pitch_zero [rad]  IMU 零位
robot cali                标定零点
robot move_h <mm>         目标高度
```

### GDB 批处理 (Unit5 tools/gdb_motor.py)

```bash
# 在 Unit5 目录下执行
python3 tools/gdb_motor.py status        # 全部状态
python3 tools/gdb_motor.py enable 1      # 使能 M1
python3 tools/gdb_motor.py kp 1 80       # 设置 M1 KP=80
python3 tools/gdb_motor.py stop          # 紧急停止
```

### 串口 CSV 角度流

```
t_ms,M1_rad,M2_rad,M3_rad,M4_rad
12345,0.1234,-0.2345,0.4567,-0.7890
```

## 测试工具

```bash
# 连接 Unit5 串口
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor status"

# 采集电流数据
python3 tools/log_current.py --port /dev/ttyACM0 --duration 10 --output test_results/current.csv

# 静态跟踪测试
python3 tools/test_static_tracking.py --port /dev/ttyACM0 --heights 150,100

# 数据绘图
python3 tools/plot_test_data.py --file test_results/*.csv
```

**Python 依赖**: `pyserial`, `numpy`, `matplotlib`

## 测试结果目录

所有测试数据存入 `test_results/`，按日期+任务命名:

```
test_results/
  2026-05-07_cali/          # 标定验证
    cali_log.txt
    offset_before.csv
    offset_after.csv
  2026-05-07_tracking/      # 跟踪测试
    h_150_angles.csv
    h_100_angles.csv
    error_report.md
  2026-05-07_ramp/          # KP 爬坡
    ramp_current.csv
    critical_kp.txt
  2026-05-07_safety/        # 安全触发
    trigger_log.txt
  2026-05-07_bias/          # 静态偏置电流
    bias_vs_h.csv
```

## 与其他 Agent 的协作

| Agent | 角色 | 接口 |
|-------|------|------|
| Unit5 控制 Agent | 电机驱动固件 | 串口 Shell / GDB |
| Linkage 运动学 Agent | 运动学解算 | `robot move_h` / `robot cali` |
| 数字经理 | 需求与决策 | 通过 `/init` 下达指令 |

### Agent 间通信格式

向同事/经理发送消息时，开头标记:

```
linkage → 经理 & Unit5:
<纯文本内容，紧凑无空行>
```

## 关键参数

| 参数 | 值 | 来源 |
|------|-----|------|
| L1 (大腿) | 107.4 mm | test_static_tracking.py / 运动学 Agent |
| L2 (小腿) | 128.0 mm | test_static_tracking.py / 运动学 Agent |
| 工作空间半径 | 20.6 ~ 235.4 mm | motion_kinematics |
| 默认 KP (idle) | 0.01 | Unit5 |
| 默认 KD (idle) | 0.001 | Unit5 |
| 平衡 KP 目标 | 80 | Unit5 (dm4310_balance_enable) |
| 平衡 KD 目标 | 1.5 | Unit5 |
| KP 爬坡时长 | 500 ms (默认 100 ticks × 5ms) | Unit5 |
| Pitch 保护阈值 | 30° (±0.5236 rad) | shell_commands.c |
| 电机扭矩常数 Kt | ~1.0 Nm/A | DM4310 datasheet |
| 单腿电机数 | 2 (M1+M2 左, M3+M4 右) | — |
| CAN 总线 | CAN1: M1+M2, CAN2: M3+M4 | — |

## 注意事项

- Unit5 串口一次只能连接一个进程 (Shell 或 CSV 流互斥)
- 电机测试前务必确认 `motor enable` 成功 (看 status)
- 安全测试 (任务 C) 需要两人操作: 一人倾斜机器人，一人盯串口
- 电流数据通过电机反馈帧的力矩字段反算 (torque_nm / Kt)
- 所有测试数据默认存入 `test_results/`，不要混入仓库根目录
- `robot cali` 会覆盖 `g_dm_offset[]`，执行前确认运动学 Agent 知情
- 紧急停止: `python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor disable all"`
- 标定前确保 4 台电机全部在线，否则离线电机不会被标定

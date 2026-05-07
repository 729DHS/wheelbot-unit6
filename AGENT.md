# Unit6 — DM4310 双足机器人单测验证

## 项目定位

**机器人单测验证 Agent。** 验证运动学 Agent 的逆解精度和控制 Agent (Unit5) 的驱动稳定性。通过 Unit5 串口 Shell 下发指令、采集 CSV 数据流，记录测试结果并反馈给运动学 Agent 和项目经理。

## 被测系统

```
┌──────────────────────────────────────────────┐
│  Unit5 控制 Agent (STM32F407IG)               │
│  ├── DM4310 × 4 (CAN1: M1+M2 / CAN2: M3+M4)  │
│  ├── Shell 命令 (motor/balance/robot)          │
│  ├── CSV 角度流 (100Hz)                        │
│  └── GDB 调试接口                              │
├──────────────────────────────────────────────┤
│  运动学 Agent (五连杆 2R 等效模型)              │
│  ├── robot cali  (标定)                        │
│  ├── robot move_h <mm> (目标高度)              │
│  └── L1=107.4mm, L2=128.0mm                    │
└──────────────────────────────────────────────┘
```

## 硬件接线 (同 Unit5)

- **MCU**: STM32F407IG (DJI RoboMaster Type-C 板)
- **电机**: DM-J4310-2EC × 4 (CAN1: M1+M2 左腿, CAN2: M3+M4 右腿)
- **调试器**: Horco CMSIS-DAP v0.2 (SWD+串口合一, /dev/ttyACM0)
- **串口**: 板子丝印 UART1 (3-pin) = USART6 (PG14 TX / PG9 RX), 115200 8N1
- **供电**: 24V (电机) + USB (MCU)

## 快速开始

```bash
cd /home/huiming/Desktop/Projects/Unit6

# 1. 确认 Unit5 串口连接
ls /dev/ttyACM* /dev/ttyUSB*

# 2. 查看电机状态
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor status"

# 3. 执行标定验证 (经理指令 #1)
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "robot cali"

# 4. 执行静态跟踪测试 (任务 A)
python3 tools/test_static_tracking.py --port /dev/ttyACM0

# 5. 采集电流数据 (经理指令 #2)
python3 tools/log_current.py --port /dev/ttyACM0 --duration 10

# 6. 紧急停止
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor disable all"
```

## 测试任务详解

### 任务 A: 静态位置跟踪误差测试

**目的:** 验证运动学逆解精度，检测连杆长度参数偏置。

**步骤:**
1. `robot cali` — 零点标定
2. `motor csv on` — 开始采集角度
3. `robot move_h 150` — 指令高度 150mm (约 elbow_up)
4. 等待稳态 → 记录 4 台电机角度
5. 通过运动学正解算实际高度 h_actual
6. `robot move_h 100` — 指令高度 100mm (约 elbow_down)
7. 等待稳态 → 记录角度 → 正解算 h_actual
8. `motor csv off`

**判定标准:**
- |h_actual - h_target| < 3mm → PASS
- |h_actual - h_target| ≥ 3mm → 通知运动学 Agent 微调 L1/L2

### 任务 B: KP 爬坡稳定性测试

**目的:** 验证 KP 爬坡无阶跃冲击、无高频啸叫。

**步骤:**
1. 启动 CSV 流采集电流 (力矩)
2. `balance enable` — 开始 KP 爬坡 (KP: 0.01→80, 默认 500ms)
3. 手扶机器人，保持水平
4. 监听电机声音 / 观察电流曲线
5. 若啸叫 → 降低 KP 重试，记录临界值
6. `motor disable all` — 安全停止

**判定标准:**
- 电流曲线平滑无阶跃 → PASS
- 无高频啸叫 → PASS
- 有啸叫 → 记录临界 KP，报告控制 Agent

### 任务 C: Pitch 触发保护测试

**目的:** 验证 >30° 倾斜触发 DISABLE。

**步骤:**
1. `balance enable` — 使能平衡
2. 机器人悬空或手扶
3. 缓慢倾斜车体，观察角度变化
4. 超过 30° 时，观察电机是否瞬间 DISABLE
5. 记录触发角度和响应时间

**安全注意:**
- 未断电严禁落地
- 需两人操作
- 随时准备 `motor disable all`

## 经理指令执行状态

| # | 指令 | 工具 | 状态 |
|---|------|------|------|
| 1 | 验证 `robot cali` | serial_test.py + CSV 对比 | ⬜ 待执行 |
| 2 | 平衡爬坡电流跳变 | log_current.py | ⬜ 待执行 |
| 3 | elbow-down 连杆干涉 | test_static_tracking.py + h=20mm | ⬜ 待执行 |
| 4 | 静态偏置电流 vs h | log_current.py + 多高度循环 | ⬜ 待执行 |

## 与其他 Agent 通信协议

### → 控制 Agent (Unit5)
发送 Shell 命令，接收状态文本 + CSV 角度流。
- 格式: 直接通过串口发送 Shell 命令 (需附带换行符 `\r\n`)
- 示例: `motor status\r\n`

### → 运动学 Agent
汇报逆解误差和连杆标定需求。
- 格式: Markdown 报告，包含 (h_target, h_actual, joint_angles, delta)
- 存放: `test_results/<date>_tracking/error_report.md`

### → 项目经理
汇报测试结果和阻塞项。
- 格式: 简短文本总结
- 包含: 通过/失败项、根因分析、建议措施

## 关键参数

| 参数 | 值 | 来源 |
|------|-----|------|
| L1 (大腿) | 107.4 mm | 运动学 Agent |
| L2 (小腿) | 128.0 mm | 运动学 Agent |
| 工作空间半径 | 20.6 ~ 235.4 mm | motion_kinematics |
| 默认 KP (idle) | 0.01 | Unit5 |
| 默认 KD (idle) | 0.001 | Unit5 |
| 平衡 KP 目标 | 80 | Unit5 (dm4310_balance_enable) |
| 平衡 KD 目标 | 1.5 | Unit5 |
| KP 爬坡时长 | 500 ms (默认) | Unit5 |
| Pitch 保护阈值 | 30° (±0.5236 rad) | shell_commands.c |
| 电机扭矩常数 Kt | ~1.0 Nm/A | DM4310 datasheet |

## 项目结构

```
Unit6/
  CLAUDE.md                       # Claude Code 开发引导 (本项目)
  AGENT.md                        # 完整项目说明 (本文件)
  README.md                       # 项目简介
  .gitignore
  docs/
    test-protocol.md              # 完整测试协议 (任务 A/B/C)
    calibration-protocol.md       # 标定验证协议
    balance-ramp-test.md          # KP 爬坡测试细节
    safety-trigger-test.md        # 安全触发测试细节
  tools/
    serial_test.py                # 串口 Shell 命令发送器
    log_current.py                # 电流数据采集
    test_static_tracking.py       # 静态跟踪误差测试
    plot_test_data.py             # 测试数据可视化
  scripts/
    connect_unit5.sh              # 连接 Unit5 串口
    quick_status.sh               # 快速状态检查
  test_results/                   # 测试结果存档
  memory/                         # Agent 记忆系统
```

## 已知依赖

- **Python 3.8+**: pyserial, numpy, matplotlib
- **Unit5 项目**: `/home/huiming/Desktop/Projects/Unit5`
- **串口设备**: `/dev/ttyACM0` (CMSIS-DAP) 或 `/dev/ttyUSB0` (CH340)

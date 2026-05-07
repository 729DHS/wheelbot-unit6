# Unit6: DM4310 双足机器人单测验证

> 验证运动学 Agent 逆解精度 + 控制 Agent (Unit5) 驱动稳定性。

## 定位

**单测验证 Agent。** 通过 Unit5 串口 Shell 下发测试指令，采集 CSV 角度/电流数据，验证机器人运动学和控制的正确性与稳定性。

## 被测系统

- **控制 Agent (Unit5)**: `/home/huiming/Desktop/Projects/Unit5` — STM32F407IG 电机固件
- **运动学 Agent**: 五连杆正逆运动学解算 (同事 AI)

## 快速开始

```bash
# 连接串口查看状态
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor status"

# 执行标定验证
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "robot cali"

# 静态跟踪测试 (任务 A)
python3 tools/test_static_tracking.py --port /dev/ttyACM0

# 电流采集 (经理指令 #2)
python3 tools/log_current.py --port /dev/ttyACM0 --duration 10

# 紧急停止
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor disable all"
```

## 测试任务

| 任务 | 内容 | 判定标准 |
|------|------|----------|
| A - 静态跟踪 | robot move_h 精度 | Δh < 3mm |
| B - KP 爬坡 | balance enable 稳定性 | 无啸叫、无阶跃 |
| C - 安全触发 | >30° 倾斜保护 | 即时 DISABLE |

## 更多文档

- `AGENT.md` — 完整项目说明
- `CLAUDE.md` — Claude Code 开发引导
- `docs/test-protocol.md` — 详细测试协议

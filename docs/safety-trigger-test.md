# 安全触发测试细节

## 前置条件

- 固件中包含 `g_pitch_angle_rad` 全局变量 (IMU 读取)
- `shell_commands.c` 中安全阈值: `#define BALANCE_PITCH_LIMIT_RAD 0.5236f` (30°)
- 电机已使能，平衡模式激活

## 测试原理

当 `balance enable` 激活后，主循环 (或独立安全线程) 检测 `g_pitch_angle_rad`:
- 若 `|g_pitch_angle_rad| > 0.5236` → 调用 `dm4310_stop_all()` → 全部电机 DISABLE
- 安全触发后无自动恢复，需重新 `balance enable`

## 测试数据采集

### 方法 1: GDB 直接读内存 (最可靠)

```bash
# 在 Unit5 目录下
python3 tools/gdb_motor.py status     # 看电机是否 DISABLE
arm-zephyr-eabi-gdb -batch \
  -ex "target extended-remote localhost:3333" \
  -ex "monitor reset init" \
  -ex "p g_pitch_angle_rad"          # 当前 Pitch 角
```

### 方法 2: 串口 CSV 流检测

电机 DISABLE 后 CSV 流中角度不再更新 (hold 为零)，可通过 `log_current.py` 检测到异常。

## 判定脚本 (伪代码)

```python
def check_safety_trigger():
    pitch_start = read_pitch()
    tilt_robot_slowly()          # 手动操作
    time.sleep(0.5)

    pitch_current = read_pitch()
    motors_enabled = read_motor_state()

    if pitch_current > 30 and motors_enabled:
        print("❌ FAIL: 超出 30° 但电机未 DISABLE")
        emergency_stop()
    elif pitch_current > 30 and not motors_enabled:
        print(f"✅ PASS: 在 {pitch_current:.1f}° 触发 DISABLE")
```

## 安全预案

| 情况 | 响应 |
|------|------|
| 电机 DISABLE 正常 | 记录数据，测试通过 |
| 电机未 DISABLE, 已达 35° | 立即 `motor disable all`，报告控制 Agent |
| 机器人开始失稳 | 立即 `motor disable all`，手扶住 |
| 机器人落地 | 立即断电 (拔 24V)，检查硬件 |

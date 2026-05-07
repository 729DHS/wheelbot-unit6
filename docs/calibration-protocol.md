# 标定验证协议 (经理指令 #1)

## `robot cali` 工作原理

`robot cali` 命令将当前电机角度存入 `g_dm_offset[]` 数组，后续 `robot move_h` 会减去该偏移量作为零位参考。

```
shell_commands.c: cmd_robot_cali()
  → dm4310_zero_motor(i)  // 逐台置零 (写 ZERO 命令 + 清零 pos_offset)
  → g_dm_offset[i] = dm4310.status[i].pos_rad  // 保存当前位置为零位
```

## 验证步骤

### 1. 准备

```bash
# 使能全部电机
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor enable all"

# 将机器人摆到已知机械零位
# 例如: 大腿垂直地面, 小腿水平
```

### 2. 首次标定

```bash
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "robot cali"
```

### 3. 读取标定值 (GDB)

```bash
# 在 Unit5 目录执行
python3 tools/gdb_motor.py status  # 查看电机角度 (应为 0)
```

### 4. 动腿验证

```bash
# 任意移动机器人 → 再放回原位
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor status"
# 记录当前角度: 即安装误差
```

### 5. 再次标定 + 验证归零

```bash
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "robot cali"
python3 tools/serial_test.py --port /dev/ttyACM0 --cmd "motor status"
# 期望: 全部角度为 0 (或 <0.01 rad)
```

## 判定

| 条件 | 结果 |
|------|------|
| 标定后角度 < 0.01 rad | ✅ PASS |
| 标定后角度 0.01-0.05 rad | ⚠️ 机械回差，可接受 |
| 标定后角度 > 0.05 rad | ❌ FAIL — 检查 `g_dm_offset[]` 逻辑 |
| 两次标定结果不一致 | ❌ FAIL — 传感器噪声或 CAN 丢帧 |

## 数据输出

```
test_results/<date>_cali/
  cali_before.csv      # 标定前角度
  cali_after.csv       # 标定后角度
  cali_log.txt         # 操作日志
```

## 注意事项

- `robot cali` 会覆盖 `g_dm_offset[]`，如果运动学 Agent 依赖该值，需同步通知
- 标定时确保 4 台电机全部在线，否则只有在线的电机会被标定
- 标定后建议立即 `motor csv once` 确认零点

# 完整测试协议

## 前置条件

- Unit5 固件已烧录，上电 bringup 完成
- 4 台电机全部在线 (`motor status` 确认)
- 串口连接正常 (/dev/ttyACM0 或 /dev/ttyUSB0)
- 机器人悬挂或手扶，不落地

---

## 任务 A: 静态位置跟踪误差测试

### 目的
验证运动学 Agent 的 `robot move_h` 逆解精度，确认连杆参数 L1/L2 无偏置。

### 原理
五连杆机构通过运动学逆解将目标高度 h 映射为 4 个关节角度。若 L1/L2 存在偏置，指令高度和实际高度之间会出现系统性偏差。

### 步骤

1. **标定零点**
   ```
   motor enable all
   robot cali
   ```
   等待 2 秒，确保标定完成。

2. **启动数据采集**
   ```
   motor csv on
   ```

3. **高度 150mm 测试 (elbow_up)**
   ```
   robot move_h 150
   ```
   等待 3 秒到达稳态，记录最后 20 帧 (0.2s) 的关节角度。

4. **高度 100mm 测试 (elbow_down)**
   ```
   robot move_h 100
   ```
   等待 3 秒到达稳态，记录最后 20 帧。

5. **停止采集**
   ```
   motor csv off
   ```

6. **数据分析**
   - 对每帧计算实际高度 h_actual = lk_forward(θ1, θ2, θ3, θ4)
   - 取 20 帧均值，与指令值对比
   - 若 |Δh| ≥ 3mm，说明 L1/L2 需要标定

### 输出
```
test_results/<date>_tracking/
  h150_angles.csv      # 150mm 时的角度数据
  h100_angles.csv      # 100mm 时的角度数据
  error_report.md      # 误差报告 (含 L1/L2 修正建议)
```

### 判定
- |Δh| < 3mm: ✅ PASS — 运动学参数正确
- |Δh| ≥ 3mm: ❌ FAIL — 通知运动学 Agent 微调 L1, L2

---

## 任务 B: KP 爬坡稳定性测试 (The "Hum" Test)

### 目的
验证 `balance enable` 的 KP 爬坡过程无阶跃冲击、无高频啸叫。

### 原理
`balance enable` 在 500ms 内将 KP 从 0.01 线性爬升至 80。爬升过快或 KP 过高会导致电流阶跃或机械谐振 (高频啸叫)。

### 步骤

1. **启动数据采集**
   ```
   motor csv on
   ```

2. **执行平衡爬坡**
   ```
   balance enable
   ```
   立即手扶机器人，保持水平姿态。

3. **监听 + 观察**
   - 用耳朵贴近电机，监听 500ms 内是否有高频啸叫声
   - 若有啸叫，立即 `motor disable all`

4. **爬坡完成后保持 5 秒**
   观察稳态电流是否稳定、无振荡。

5. **停止**
   ```
   motor disable all
   motor csv off
   ```

6. **数据分析**
   - 绘制 4 台电机的力矩/电流曲线
   - 检查是否有 >0.5Nm 的阶跃跳变 (正常应在 0.2Nm 以内平滑过渡)
   - 若有啸叫，记录当时的 KP 值

### 输出
```
test_results/<date>_ramp/
  ramp_current.csv        # 爬坡期间力矩/电流数据
  critical_kp.txt         # 若啸叫，记录临界 KP 值
  ramp_analysis.md        # 分析报告
```

### 判定
- 电流曲线平滑、无啸叫: ✅ PASS
- 电流波动 >0.5Nm 或有啸叫: ❌ FAIL — 通知控制 Agent 降低目标 KP

---

## 任务 C: Pitch 触发保护测试 (Safety Trigger)

### 目的
验证 `balance enable` 状态下，Pitch >30° 时电机自动 DISABLE。

### 原理
`shell_commands.c` 中的安全逻辑检测陀螺仪 Pitch 角，超过 ±30° 阈值则调用 `dm4310_stop_all()`。

### ⚠️ 安全警告
- 此测试有摔机风险
- 必须两人操作: 一人倾斜机器人，一人盯串口/准备急停
- 若保护未触发，立即 `motor disable all`
- 严禁在保护失效时让机器人落地

### 步骤

1. **确认安全**
   - 机器人悬空或牢固手扶
   - 第二人准备随时执行 `motor disable all`

2. **启动平衡**
   ```
   balance enable
   ```

3. **缓慢倾斜 Pitch**
   - 以约 5°/s 速率缓慢增加 Pitch
   - 持续读取角度 (`motor csv on` 或 `motor status`)

4. **观察触发**
   - 达到 30° 附近时，观察电机是否瞬间 DISABLE
   - 记录实际触发角度和电机响应时间

5. **若未触发**
   - 达到 35° 仍未触发 → 立即 `motor disable all`
   - ❌ FAIL — 安全保护失效

### 输出
```
test_results/<date>_safety/
  trigger_log.txt    # 触发角度、响应时间
  safety_report.md   # 安全验证报告
```

### 判定
- 30° ± 2° 范围内触发 DISABLE: ✅ PASS
- 超过 35° 仍未触发: ❌ FAIL — 通知控制 Agent 排查安全逻辑

---

## 经理指令 #1: robot cali 标定验证

### 步骤
1. 使能全部电机，人为将机器人摆到已知姿态
2. 执行 `robot cali`
3. 读取 `g_dm_offset[]` (通过 GDB: `p g_dm_offset`)
4. 记录标定前后角度差
5. 验证: 再次 `robot cali` 后偏移量应为 0

### 判定
- 标定后角度差归零: ✅ PASS
- 标定后仍有残余偏移: ❌ FAIL

---

## 经理指令 #2: 平衡爬坡电流跳变

### 步骤
1. 以 200Hz+ 采样率采集 torque_nm 数据
2. `balance enable` 触发爬坡
3. 分析爬坡前 200ms / 爬坡中 500ms / 爬坡后 500ms 三段的电流
4. 检查段间过渡是否有阶跃 (>0.3Nm 突变)

### 判定
- 所有段间过渡平滑: ✅ PASS
- 存在阶跃: ❌ FAIL — 爬坡算法需加平滑过渡

---

## 经理指令 #3: elbow-down 连杆干涉测试

### 步骤
1. `robot move_h 30` — 极限收缩
2. 目视检查连杆是否碰撞
3. 读取电机力矩: 若力矩异常增大 (>2Nm) 说明有机械干涉
4. 逐步增加 h (30 → 40 → 50...) 找到无干涉的最小安全高度

### 判定
- 目标高度可达到且无干涉: ✅ PASS
- 发生碰撞或无法到达: ❌ FAIL — 需要限制工作空间

---

## 经理指令 #4: 静态偏置电流测量

### 步骤
1. 机器人悬挂/手扶，在多个高度保持静止
2. 对每个高度 (30, 50, 80, 100, 120, 150mm):
   - `robot move_h <h>`
   - 等待 3 秒稳态
   - 记录 1 秒 (100 帧) 的力矩数据
   - 计算均值作为该高度的重力偏置电流

### 输出
| h (mm) | M1_torque (Nm) | M2_torque (Nm) | M3_torque (Nm) | M4_torque (Nm) |
|--------|----------------|----------------|----------------|----------------|
| 30     |                |                |                |                |
| 50     |                |                |                |                |
| ...    |                |                |                |                |

此表交付给控制 Agent 用于平衡环的重力补偿前馈。

# KP 爬坡稳定性测试细节

## 前置条件

- Unit5 中 `dm4310_balance_enable()` 实现 KP 线性爬坡 (0.01 → 80, 默认 500ms)
- 爬坡期间 KD 同步爬升 (0.001 → 1.5)
- 电机已 bringup 完成，在线

## `balance enable` 命令参数

```
balance enable [ramp_ticks]
```
- `ramp_ticks`: 爬坡持续 tick 数，默认 100 (500ms, 每 tick 5ms)
- 每个 tick: `KP += (80 - 0.01) / ramp_ticks`

## 啸叫检测

### 人耳检测 (主)
- 在安静环境中，耳朵靠近电机
- 高频啸叫通常 >2kHz，与正常 PWM 声音不同
- 正常: 低沉嗡嗡声 (200Hz PWM 基频)
- 异常: 尖锐啸叫 (KP 过高导致的机械谐振)

### 电流频谱检测 (辅)
```python
# 对力矩数据做 FFT，检测高频分量
import numpy as np
torque = load_csv("ramp_current.csv", col="torque")
freq = np.fft.fft(torque)
# 若 2-5kHz 频段能量 > 阈值 → 啸叫
```

## 临界 KP 测定步骤

1. `balance enable` (默认 KP=80)
2. 若有啸叫 → `motor disable all`
3. 重试: 修改 `dm4310_balance_enable()` 的 `kp_target`
   - KP=60 → 测试
   - KP=40 → 测试
   - ...
   - 二分搜索找到无啸叫的最大 KP
4. 记录临界值到 `test_results/<date>_ramp/critical_kp.txt`

## 数据示例

```
test_results/2026-05-07_ramp/
  kp80_ramp.csv        # KP=80 爬坡数据 (有啸叫)
  kp60_ramp.csv        # KP=60 爬坡数据 (临界)
  kp40_ramp.csv        # KP=40 爬坡数据 (正常)
  critical_kp.txt      # 内容: "临界 KP = 62"
```

## 判定

- KP=80 无啸叫: ✅ 默认值安全
- KP=60-80 有啸叫: ⚠️ 记录临界值
- KP<60 有啸叫: ❌ 可能电路/机械问题，排查

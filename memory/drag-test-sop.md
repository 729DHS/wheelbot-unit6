---
name: drag-test-sop
description: 数字孪生拖拽实机验证 — 四阶段测试 SOP
type: project
---

## 经理指令: Digital Twin 拖拽实机验证 (2026-05-09)

目标: 用户在上位机 Linkage 数字孪生中拖动 P7，真实小车腿部跟随小范围运动。
目的: 确认数字孪生和真实机构一致。

### Stage 0: 冷机手推映射 (disable, 手推)
- 验证 h/φ/M1-M4 读数方向正确、无跳变、左右对称
- 数据源: robot_viz.py + live_view.py

### Stage 1: 空载小步 target (enable, 架空)
- motor enable all → robot cali → 发送 x/y 各 ±2mm 单步
- 一次只动一个方向

### Stage 2: 数字孪生拖拽 (enable, 架空)
- Linkage 拖拽 P7，每次 2-5mm，限制频率
- 禁止: 连续快速拖、大幅拖、靠近限位、靠近奇异区

### Stage 3: 双腿同步 (enable, 架空)
- 双腿同时下压/上抬/前摆/后摆
- 验证左右对称一致性

### 停止条件
- 立即停止: 角度跳变>0.5rad、力矩>1Nm、碰撞、啸叫
- 暂停排查: 方向反、左右不对称>10mm、孪生偏差>5mm、branch跳变
- 通信异常: Shell无响应>3s、stop延迟>500ms

### 优先级
先单腿→后双腿, 先命令行→后拖拽, 先 x/y→后 h/φ

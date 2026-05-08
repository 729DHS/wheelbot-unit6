---
name: agent-roles
description: 三个 Agent 的角色分工、接口与当前对齐状态
type: project
---

## 三个 Agent 分工

### Unit5 (固件/MCU)
- STM32F407 + Zephyr RTOS
- 4×DM4310 (CAN1: M1+M2, CAN2: M3+M4) + 2×M3508 轮毂电机 (待接入)
- BMI088 IMU (SPI, 待接入)
- 500Hz 控制循环 + 运动学 (IK/FK)
- Shell 命令行调试接口

运动学链路: (h,φ) → leg_move_all(h,φ) → lk_inverse(h,φ,elbow=-1) → lk_theta_a_to_m1/4, lk_theta_b_to_m2/3 → dm4310_set_pos_with_offset → MIT CAN 帧

软限位: h∈[45,235.4]mm, φ∈[-1.047,+1.047]rad, θa∈[-π,+0.349]rad, θb∈[-2.094,+0.524]rad
Elbow=-1 (elbow-down, Ascento 站立)

### Linkage (运动学/数字孪生)
- FK: θa/θb → 全部杆位置 P1-P7
- IK: 轮毂目标 (x,y) → θa/θb (闭式余弦定理, elbow±1)
- 数字孪生渲染: PyQt6 twin_display.py, UDP 实时接收编码器角度
- 工作空间: h∈[20.6, 235.4]mm, 奇异在 θb-θa≈0 或 π
- 4 种装配分支 (branch_d=±1 × branch_f=±1), 默认凸四边形

编码器→机构帧: 左腿 θa=-(enc_M1)+(-162.4°), θb=-(enc_M2)+(-10.0°); 右腿 θa=+(enc_M3)+(-162.4°), θb=+(enc_M4)+(-10.0°)

### Unit6 (测试/验证 — 本项目)
- 串口 Shell 命令发送、CSV 数据采集、可视化、测试执行与记录

## 当前待对齐项 (2026-05-09)

1. 电机方向验证: M1 正向→P1 旋转方向
2. cali 姿态实测: 零位编码器值对比
3. 编码器限位值最终确认
4. 右腿 x 镜像确认
5. Linkage 拖拽→Unit5 通信路径 (x/y 目标如何下发)
6. Unit5 是否有直接接收 x/y 目标的 Shell 命令

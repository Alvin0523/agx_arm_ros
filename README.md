# 🦾 agx_arm_ros — Piper Arm ROS2 + MoveIt2 Workspace

[![Docs](https://img.shields.io/badge/Docs-Zensical-blue?logo=readthedocs)](https://alvin0523.github.io/agx_arm_ros/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Jetson%20AGX%20Orin-76b900?logo=nvidia)](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-agx-orin/)
[![Pixi](https://img.shields.io/badge/Pixi-Package%20Manager-brightgreen?logo=conda-forge)](https://pixi.sh)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-22314E?logo=ros)](https://docs.ros.org/en/humble/)
[![Robot](https://img.shields.io/badge/Robot-AgileX%20PIPER-0ea5e9)](https://github.com/agilexrobotics)
[![Sensor](https://img.shields.io/badge/Sensor-Acconeer%20A121-ff6b35)](https://www.acconeer.com/)

> ROS2 + MoveIt2 workspace for the AgileX PIPER arm — pick-and-place chess demo with Acconeer A121 radar-triggered gesture interrupts.

[![Read the Docs](https://img.shields.io/badge/📖%20Read%20the%20Docs-Operation%20Guide%20%26%20Reference-blue?style=for-the-badge)](https://alvin0523.github.io/agx_arm_ros/)

---

## 📖 About

This workspace provides a full ROS2 Humble + MoveIt2 setup for the AgileX PIPER arm on Jetson AGX Orin. It includes a chess pick-and-place demo driven by an Acconeer A121 mmWave radar sensor — when a human is detected, the arm pauses and executes a gesture sequence before resuming.

| Component | Role |
|-----------|------|
| `agx_arm_ctrl` | ROS2 arm driver — CAN bus control + joint feedback |
| `agx_arm_moveit` | MoveIt2 configuration — OMPL planning, IK, execution |
| `ai_film/` | Task scripts — chess pick-place, gesture interrupt, sensor node |
| `ai_film/config/` | All tuneable YAML configs — poses, planner, gestures |

---

## 📁 Project Structure

```
agx_arm_ros/
├── ai_film/
│   ├── main.py              # orchestrator — chess loop + gesture interrupt
│   ├── pick_place.py        # PickPlaceNode utility (MoveIt motion + gripper)
│   ├── detector_ros.py      # Acconeer A121 → /detector ROS2 publisher
│   └── config/
│       ├── moveit.yaml      # robot frames, planner, tolerances, gripper
│       ├── chess.yaml       # board poses, hover offsets, sequences
│       └── gestures.yaml    # gesture waypoints, interrupt sequence
├── docs/                    # documentation site (Zensical)
│   ├── index.md
│   ├── quick-start.md
│   ├── operation.md
│   ├── teaching.md
│   ├── sensor.md
│   └── tuning.md
├── src/
│   ├── agx_arm_ctrl/        # ROS2 arm driver package
│   ├── agx_arm_moveit/      # MoveIt2 config package
│   ├── agx_arm_description/ # URDF / xacro
│   └── agx_arm_msgs/        # custom message types
├── scripts/                 # CAN activation helpers
├── pixi.toml                # Pixi task definitions & dependencies
└── zensical.toml            # Zensical docs site config
```

---

## 🚀 Quick Start

**1. Install [Pixi](https://pixi.sh) (one-time):**

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

**2. Install Python SDK:**

```bash
git clone https://github.com/Alvin0523/pyAgxArm.git
cd pyAgxArm
pixi install
```

**3. Clone and build:**

```bash
mkdir -p ~/agx_arm_ws/src
cd ~/agx_arm_ws/src
git clone -b ros2 --recurse-submodules https://github.com/Alvin0523/agx_arm_ros.git
cd agx_arm_ros/
git submodule update --remote --recursive
pixi install
pixi run build
```

**4. Run:**

```bash
pixi run can       # Terminal 1 — CAN bus
pixi run moveit    # Terminal 2 — MoveIt + arm control
pixi run detect    # Terminal 3 — Acconeer radar detector
pixi run main      # Terminal 4 — chess loop + gesture interrupt
```

👉 For full setup, teaching positions, sensor config, and tuning — see the **[Documentation](https://alvin0523.github.io/agx_arm_ros/)**.

| Language | Full README |
|----------|-------------|
| 中文 | [docs/README_CN.md](docs/README_CN.md) |
| English | [docs/README_EN.md](docs/README_EN.md) |

---

## 👥 Credits

**Original ROS2 driver & MoveIt2 packages:**  
[AgileX Robotics](https://github.com/agilexrobotics) — [`agx_arm_ros`](https://github.com/agilexrobotics/agx_arm_ros) · [`pyAgxArm`](https://github.com/agilexrobotics/pyAgxArm) · [`agx_arm_urdf`](https://github.com/agilexrobotics/agx_arm_urdf)

**AI Film demo (sensor integration + pick-place orchestration):** 

[<img src="https://github.com/Alvin0523.png" width="80" style="border-radius:50%">](https://github.com/Alvin0523)
[<img src="https://github.com/frieddeli.png" width="80" style="border-radius:50%">](https://github.com/frieddeli)
[<img src="https://github.com/HappyEthan.png" width="80" style="border-radius:50%">](https://github.com/HappyEthan)

| Name | GitHub |
|------|--------|
| Wong Wei Ming | [@Alvin0523](https://github.com/Alvin0523) |
| Shao Ying Zhan | [@frieddeli](https://github.com/frieddeli) |
| Chen Yusen | [@HappyEthan](https://github.com/HappyEthan) |


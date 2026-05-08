# agx_arm_ros — Piper Arm ROS2 Workspace

| Language | Link |
|----------|------|
| 中文 | [docs/README_CN.md](docs/README_CN.md) |
| English | [docs/README_EN.md](docs/README_EN.md) |

---

## Installation

### 1. Install Python SDK

```bash
git clone https://github.com/Alvin0523/pyAgxArm.git
cd pyAgxArm
```

### 2. Install ROS2 Driver

Create workspace:
```bash
mkdir -p ~/agx_arm_ws/src
cd ~/agx_arm_ws/src
```

Clone repository:
```bash
git clone -b ros2 --recurse-submodules https://github.com/Alvin0523/agx_arm_ros.git
cd agx_arm_ros/
git submodule update --remote --recursive
```

Install dependencies and build (pixi handles everything):
```bash
pixi install
pixi run build
```

---

## Documentation

See **[docs/index.md](docs/index.md)** — it tells you exactly which file to read for each topic.

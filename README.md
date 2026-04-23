# agx_arm_ros — Piper Arm ROS2 Workspace

## Quick Start

```bash
# Terminal 1: activate CAN, then launch MoveIt
pixi run can
pixi run piper_moveit

# Terminal 2: run task
pixi run chess
```

---

## Workflow

### 1. Activate CAN
```bash
pixi run can
```
Must be run first before any arm launch. Brings up `can2` interface.

### 2. Launch the Arm
Choose one depending on what you need:

| Task | Command | Use when |
|------|---------|----------|
| ROS only | `pixi run arm` | Just need ROS feedback, no control |
| RViz control | `pixi run piper_control` | Manual control via RViz |
| MoveIt | `pixi run piper_moveit` | Motion planning + task execution |

### 3. Run Task (separate terminal)
```bash
pixi run chess
```

---

## Teaching Positions

To get a new position for the config file:

1. Press the **teach mode button** on the Piper arm
2. Physically move the arm to the desired pose
3. Read the current TCP pose:
   ```bash
   pixi run pose
   ```
4. Copy the `position` and `orientation` values into `test/ai_film/config.yaml`

### Example Poses

**Pick position 1**
```
position:    x: 0.425614  y: 0.184159   z: 0.127559
orientation: x: 0.02974   y: 0.99327    z: 0.04344   w: 0.10313
```

**Pick position 2**
```
position:    x: 0.222914  y: -0.130998  z: 0.133609
orientation: x: 0.02753   y: 0.99869    z: 0.00170   w: -0.04321
```

**Clock position 1**
```
position:    x: 0.354933  y: 0.24336    z: 0.340826
orientation: x: -0.50840  y: 0.51010    z: 0.47510   w: 0.50558
```

**Clock position 2**
```
position:    x: 0.349323  y: 0.239749   z: 0.333570
orientation: x: -0.51507  y: -0.48446   z: -0.51507  w: 0.48446
```

---

## Gripper Control

Gripper hold timer position: **0.0539**

Open/close gripper manually:
```bash
ros2 topic pub --once /gripper_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  "{
    joint_names: [gripper_joint1, gripper_joint2],
    points: [{
      positions: [0.03, 0.03],
      velocities: [0.0, 0.0],
      time_from_start: {sec: 1, nanosec: 0}
    }]
  }"
```

---

## Utilities

```bash
pixi run home    # send arm to home position
pixi run pose    # print current TCP pose
pixi run down    # disable arm torque (safe shutdown)
pixi run build   # rebuild ROS workspace after code changes
```

---

## Disable Arm
Always disable torque before powering off:
```bash
pixi run down
# or
ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: false}"
```
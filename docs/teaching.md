# Teaching Positions

How to record a new TCP pose and add it to the config.

---

## Steps

1. Start the arm (after `pixi run can` in another terminal):
   ```bash
   pixi run arm
   ```
2. Press the **teach mode button** on the Piper arm to enter compliant mode.
3. Physically move the arm to the desired pose.
4. Read the current TCP pose:
   ```bash
   pixi run pose
   ```
5. Copy the `position` and `orientation` values into `ai_film/config/chess.yaml` under `poses:`.

---

## Config file locations

| File | What to edit |
|------|-------------|
| `ai_film/config/chess.yaml` | Board slot poses, hover offsets, sequences |
| `ai_film/config/moveit.yaml` | Planner settings, constraint tolerances, gripper timing |
| `ai_film/config/gestures.yaml` | Gesture waypoints, interrupt sequence |

---

## Example Poses

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

Open/close gripper manually via ROS topic:
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

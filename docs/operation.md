# Operation Guide

Step-by-step for running the AI Film demo.

---

## Chess loop (no sensor)

Runs the pick-place sequence on loop. Press ENTER to start, ENTER again to stop.

```bash
# Terminal 1
pixi run can

# Terminal 2
pixi run moveit

# Terminal 3
pixi run chess
```

---

## Sensor-driven mode (chess + gesture interrupt)

Same as above but adds the radar detector. When a human is detected after any
pick-place step, the arm pauses and executes the gesture sequence before
continuing.

```bash
# Terminal 1
pixi run can

# Terminal 2
pixi run moveit

# Terminal 3
pixi run detect

# Terminal 4
pixi run main
```

See [sensor.md](sensor.md) for sensor hardware setup.

---

## Utility commands

```bash
pixi run home    # move arm to home position
pixi run pose    # print current TCP pose (useful when teaching)
pixi run down    # disable arm torque (run before powering off)
pixi run build   # rebuild ROS workspace after code changes
```

---

## Config files

All tuneable parameters live in `ai_film/config/`. Edit these — not the Python source.

| File | Contents |
|------|----------|
| `moveit.yaml` | Robot frames, planner settings, constraint tolerances, gripper |
| `chess.yaml` | Board slot poses, hover offsets, pick-place sequences |
| `gestures.yaml` | Gesture poses, gesture tolerances, interrupt sequence |

For tuning guidance see [tuning.md](tuning.md).

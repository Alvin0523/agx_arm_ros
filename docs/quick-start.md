# Quick Start

Four terminals in order:

```bash
# Terminal 1 — CAN bus
pixi run can

# Terminal 2 — MoveIt + arm control
pixi run moveit

# Terminal 3 — Acconeer radar detector (sensor-driven mode only)
pixi run detect

# Terminal 4 — Task
pixi run chess        # chess loop, no sensor
pixi run ai_film      # chess loop + sensor gesture interrupt
```

---

## pixi Tasks Reference

| Task | What it does |
|------|-------------|
| `pixi run can` | Bring up `can2` CAN interface (run first, always) |
| `pixi run moveit` | Launch arm control + MoveIt + RViz |
| `pixi run rviz` | Launch arm + RViz only (no MoveIt, no planning) |
| `pixi run arm` | Launch arm ROS node only (no visualisation) |
| `pixi run chess` | Run chess pick-place loop (no sensor) |
| `pixi run ai_film` | Run chess loop with radar-triggered gesture interrupt |
| `pixi run detect` | Start Acconeer A121 detector → publishes `/detector` |
| `pixi run home` | Send arm to home position |
| `pixi run pose` | Print current TCP pose |
| `pixi run down` | Disable arm torque (safe shutdown) |
| `pixi run build` | Rebuild ROS workspace after code changes |

---

## Disable Arm

Always disable torque before powering off:

```bash
pixi run down
# or
ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: false}"
```

# Sensor Setup — Acconeer A121 Radar

> `acconeer-exptool` is already included in the pixi environment — no extra install needed.

---

## 1. Connect the sensor

Use a **USB-C cable** to plug the A121 into the host machine.

Verify it appears as a serial device:
```bash
ls /dev/ttyACM*
```

---

## 2. Add udev rules (one-time setup)

Give your user permission to access the device without `sudo`:
```bash
sudo usermod -a -G dialout $USER
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then **reboot** for the group change to take effect.

---

## 3. Run the detector

The detector runs as a separate process and publishes `/detector` (std_msgs/Bool) over ROS2:
```bash
pixi run detect
```

It only publishes **on state change** — True when a human appears, False when they leave.

---

## How detection drives the arm

```
Idle (waiting for human)
  │
  └── /detector = True  (human appears)
        │
        ▼
   Running pick-place sequence...
        │  (after each pick-place step, check latched flag)
        ├── not detected → continue next step
        └── detected     → run gesture interrupt → clear flag → continue next step
```

Or as a state diagram:
```
IDLE ──(sensor True)──▶ RUNNING ──(pick-place step done)──▶ check /detector
                                                                    │
                              ┌─────────── not detected ───────────┤
                              │                                     │
                              ▼                              detected│
                       next step / loop                             │
                                                                    ▼
                                                          GESTURE INTERRUPT
                                                          (arm waves, then
                                                           resumes sequence)
```

### Implementation notes

- **`detector_ros.py`** — polls the radar and publishes `/detector` only on state change. Run via `pixi run detect`.
- **`DetectorNode` in `main.py`** — subscribes to `/detector` on its own `SingleThreadedExecutor` in a background thread, so it receives messages even while the robot is mid-motion.
- **Latch behaviour** — `_on_detector` only sets the flag on True. A False message mid-motion does not clear it. `clear_detected()` is called manually after the gesture completes.

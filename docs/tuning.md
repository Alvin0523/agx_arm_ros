# Tuning for Reliability & Speed

All settings are in `ai_film/config/moveit.yaml`. Work through these steps in
order — only move to the next step once the current one is stable.

---

## 1. Workspace

Defines the bounding box (in `base_link` frame) where OMPL searches for solutions.

```yaml
workspace:
  min: [ 0.10, -0.20, 0.10]
  max: [ 0.55,  0.25, 0.40]
```

Each value is a distance in metres from the arm's base bolt:

```
  [0]  x  →  how far FORWARD from the base  (+ = away from base)
  [1]  y  →  how far LEFT/RIGHT              (+ = left,  - = right)
  [2]  z  →  how far UP/DOWN                 (+ = up)
```

Visual layout:
```
  Side view (x vs z):          Top view (x vs y):
                                        left +y
  z=0.40 ┌──────────┐           ┌──────────────────┐ x=0.55
         │          │     slots→│  r1   r2   r3    │
  z=0.10 └──────────┘           └──────────────────┘ x=0.10
         x=0.10   x=0.55       right -y
```

Slot poses (x: 0.246–0.376, y: -0.040–0.090, z: 0.149 + hover) all fit
comfortably inside the default box.

---

## 2. Constraint tolerances

The IK sampler must find a joint config where the TCP lands inside this
acceptance bubble. Too tight → `error_code=99999`. Too loose → imprecise placement.

```yaml
constraints:
  position_tolerance:    0.005   # metres — start here, tighten toward 0.002 once stable
  orientation_tolerance: 0.05    # radians — don't go below 0.03 or IK sampling breaks
```

**Tighten `position_tolerance` gradually** (0.005 → 0.003 → 0.002) only after
zero planning failures.  
Keep `orientation_tolerance` ≥ 0.03 — the arm's IK solver needs slack,
especially at far reaches.

---

## 3. Planning time & attempts

```yaml
num_planning_attempts: 3     # retries with a new random seed on timeout
allowed_planning_time: 5.0   # seconds per attempt
```

How it works:
```
attempt 1 → solves in <1 s normally → executes immediately ✓
attempt 1 → times out at 5 s → attempt 2 (new seed) → attempt 3 → all fail → error 99999
```

- Reduce `allowed_planning_time` first (15 → 10 → 5) once tolerances are stable.
- Reduce `num_planning_attempts` last (10 → 5 → 3).
- Worst case wait on failure = `attempts × planning_time` (e.g. 3 × 5 s = 15 s).

---

## 4. Speed

Only tune this after steps 1–3 are stable.

```yaml
max_velocity_scaling_factor:     0.6   # % of URDF joint speed limits
max_acceleration_scaling_factor: 0.5   # % of URDF acceleration limits
```

Raise gradually (0.6 → 0.8 → 1.0). If the arm starts failing or slipping, step back.  
Also reduce `gripper.move_time` (1.0 → 0.5) to save ~1 s per pick-place step.

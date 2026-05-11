#!/usr/bin/env python3
"""
main.py — AI Film main loop.

Runs the pick-and-place chess sequence and handles /detector interrupt
for arm gestures when a human is detected.

Terminals:
  1: pixi run can
  2: pixi run moveit
  3: pixi run detect        # detector_ros.py — publishes /detector Bool topic
  4: pixi run ai_film       # this script

Config files (edit these, not this script):
  ai_film/config/moveit.yaml   — robot, planner, constraint tolerances, gripper
  ai_film/config/chess.yaml    — board poses, offsets, sequences
  ai_film/config/gestures.yaml — gesture waypoints, loose tolerances, interrupt sequence

Import layout:
  pick_place.py   — PickPlaceNode (motion), load_config, get_offset  (utility module)
  detector_ros.py — standalone /detector publisher (separate process, pixi run detect)
  main.py         — DetectorNode subscriber + interrupt logic + sequence runner

Detection / interrupt flow
──────────────────────────

  Idle (waiting for /detector = True)
    │
    └── sensor publishes True
          │
          ▼
     DetectorNode latches _detected = True in background thread
     (flag persists even while arm is mid-motion)
          │
          ▼
     pick-place step completes
          │
          ├── _detected == False → continue to next step
          │
          └── _detected == True
                │
                ▼
           _run_gesture_sequence(robot, gesture_cfg)
                │  arm waves / looks around
                ▼
           detector.clear_detected()   ← reset latch
                │
                ▼
           continue to next pick-place step

Note: detector_ros.py only publishes on *state change* (True = human appeared,
False = human left). The subscriber ignores False messages to prevent a
transient clear from erasing a detection that happened mid-motion.
"""

import argparse
import random
import threading

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool

from pick_place import (
    load_config,
    get_offset,
    PickPlaceNode,
)


# ─── Gesture executor ────────────────────────────────────────────────────────

def _run_gesture_sequence(robot: PickPlaceNode, gesture_cfg: dict):
    """Execute a randomly chosen gesture sequence. Arm only — no gripper."""
    poses     = gesture_cfg["poses"]
    seq_names = list(gesture_cfg["sequences"].keys())
    chosen    = random.choice(seq_names)
    cons      = gesture_cfg.get("constraints", {})
    pos_tol   = cons.get("position_tolerance", None)
    ori_tol   = cons.get("orientation_tolerance", None)
    log = robot.get_logger().info

    log(f"=== gesture interrupt start — running '{chosen}' ===")
    for pose_name in gesture_cfg["sequences"][chosen]:
        robot.go(poses[pose_name], pos_tol=pos_tol, ori_tol=ori_tol)
    log(f"=== gesture interrupt done ===")


# ─── Detector subscriber node ────────────────────────────────────────────────

class DetectorNode(Node):
    """
    Subscribes to /detector (std_msgs/Bool) published by detector_ros.py.
    Tracks the latest presence state in a thread-safe flag.
    """

    def __init__(self):
        super().__init__("ai_film_detector_node")
        self._detected = False
        self._lock     = threading.Lock()
        self.create_subscription(Bool, "/detector", self._on_detector, 10)
        self.get_logger().info("Subscribed to /detector")

    def _on_detector(self, msg: Bool):
        if msg.data:  # only latch True — False is ignored (cleared manually after gesture)
            with self._lock:
                self._detected = True
        self.get_logger().info(f"/detector → {msg.data}")

    def is_detected(self) -> bool:
        with self._lock:
            return self._detected

    def clear_detected(self):
        with self._lock:
            self._detected = False


# ─── Sequence runner with interrupt check ────────────────────────────────────

def _run_steps(robot: PickPlaceNode,
               detector: DetectorNode,
               cfg: dict,
               gesture_cfg: dict,
               steps: list):
    """
    Execute one pass through all steps.
    After every step, flush /detector callbacks and — if presence was detected —
    pause to run the gesture interrupt sequence before continuing.
    """
    poses = cfg["poses"]
    for step in steps:
        if step["type"] == "home":
            robot.go_home()

        elif step["type"] == "gesture":
            seq_names = list(gesture_cfg["sequences"].keys())
            chosen    = step.get("name", random.choice(seq_names))
            g_poses   = gesture_cfg["poses"]
            cons      = gesture_cfg.get("constraints", {})
            pos_tol   = cons.get("position_tolerance", None)
            ori_tol   = cons.get("orientation_tolerance", None)
            robot.get_logger().info(f"=== gesture step: running '{chosen}' ===")
            print(f"\n[GESTURE] Running gesture sequence: '{chosen}'\n")
            for pose_name in gesture_cfg["sequences"][chosen]:
                robot.go(g_poses[pose_name], pos_tol=pos_tol, ori_tol=ori_tol)
            robot.get_logger().info(f"=== gesture step '{chosen}' done ===")

        elif step["type"] == "pick_place":
            pick_pose  = poses[step["pick"]]
            place_pose = poses[step["place"]]
            pick_off   = get_offset(cfg, step["pick_offset"])
            place_off  = get_offset(cfg, step["place_offset"])
            robot.pick_and_place(pick_pose, place_pose, pick_off, place_off)

            # ── interrupt check after each pick_place ─────────────────────────
            # DetectorNode is spun on its own executor in a background thread,
            # so _detected is always up to date regardless of blocking motion.
            if detector.is_detected():
                print("\n[DETECTOR] Human presence detected — executing gesture interrupt\n")
                robot.get_logger().info("Human detected — running gesture interrupt")
                _run_gesture_sequence(robot, gesture_cfg)
                detector.clear_detected()

        else:
            robot.get_logger().warn(f"Unknown step type: {step['type']!r}")


def run_sequence(robot: PickPlaceNode,
                 detector: DetectorNode,
                 cfg: dict,
                 gesture_cfg: dict,
                 sequence_name: str):
    """Run the named sequence, looping if loop=true in config."""
    seq   = cfg["sequences"][sequence_name]
    steps = seq["steps"]
    loop  = seq.get("loop", False)

    print(f"\nSequence '{sequence_name}' — {len(steps)} step(s), "
          f"loop={'yes' if loop else 'no'}.")

    if loop:
        input("Press ENTER to start... ")
        stop_flag = threading.Event()

        def _wait_for_stop():
            input("Press ENTER to stop...\n")
            stop_flag.set()

        t = threading.Thread(target=_wait_for_stop, daemon=True)
        t.start()

        try:
            while not stop_flag.is_set():
                _run_steps(robot, detector, cfg, gesture_cfg, steps)
        except KeyboardInterrupt:
            print("\nStopped.")

        print("\nLoop ended.")

    else:
        input("Press ENTER to run once... ")
        try:
            _run_steps(robot, detector, cfg, gesture_cfg, steps)
        except KeyboardInterrupt:
            print("\nStopped.")
        print("\nDone.")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Film main loop")
    parser.add_argument("--config",
                        nargs="+",
                        default=["ai_film/config/moveit.yaml",
                                 "ai_film/config/chess.yaml"],
                        help="One or more YAML config files merged in order "
                             "(default: config/moveit.yaml config/chess.yaml)")
    parser.add_argument("--gestures",
                        default="ai_film/config/gestures.yaml",
                        help="Gesture YAML config (default: config/gestures.yaml)")
    parser.add_argument("--sequence",
                        default=None,
                        help="Sequence name from config. If omitted, an interactive menu is shown.")
    args = parser.parse_args()

    cfg         = load_config(*args.config)
    gesture_cfg = load_config(args.gestures)

    # ── Interactive sequence picker ───────────────────────────────────────────
    if args.sequence is None:
        seq_names = list(cfg["sequences"].keys())
        print("\n" + "═" * 50)
        print("  Select a sequence to run:")
        print("═" * 50)
        separator_shown = False
        for i, name in enumerate(seq_names, 1):
            seq   = cfg["sequences"][name]
            label = seq.get("label", name)
            if not separator_shown and "(test)" in label:
                print("  " + "─" * 46)
                separator_shown = True
            print(f"  [{i:2d}] {label}")
        print("═" * 50)
        while True:
            raw = input("  Enter number or name: ").strip()
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(seq_names):
                    args.sequence = seq_names[idx]
                    break
                print(f"  Invalid number — enter 1–{len(seq_names)}")
            elif raw in seq_names:
                args.sequence = raw
                break
            else:
                print(f"  Unknown sequence '{raw}' — try again")

    rclpy.init()
    robot    = PickPlaceNode(cfg)
    detector = DetectorNode()

    # Give the detector its own executor in a background thread so it
    # receives /detector messages continuously — even while the main thread
    # is blocked inside rclpy.spin_until_future_complete() during motion.
    # Using a separate SingleThreadedExecutor avoids conflicts with the
    # robot node's default executor.
    _det_executor = SingleThreadedExecutor()
    _det_executor.add_node(detector)
    threading.Thread(target=_det_executor.spin, daemon=True).start()

    print("\n[READY] Stand clear.")
    input("Press ENTER to go HOME... ")
    robot.go_home()

    run_sequence(robot, detector, cfg, gesture_cfg, args.sequence)

    rclpy.shutdown()


if __name__ == "__main__":
    main()


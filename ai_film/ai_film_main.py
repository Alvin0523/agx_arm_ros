#!/usr/bin/env python3
"""
AI Film Main — Sensor-driven robot arm controller.

State machine:
  IDLE    : waiting for /detector == True
  RUNNING : executing the arm sequence (sensor ignored)
  COOLDOWN: sequence done, waiting for /detector == False before re-arming

Terminals:
  1: pixi run can
  2: pixi run piper_moveit
  3: pixi run detect         (in a separate terminal)
  4: python3 ai_film/ai_film_main.py --config ai_film/config.yaml

Or add a pixi task and run it directly.
"""

import argparse
import enum
import threading
import time

import rclpy
import yaml
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Bool

from geometry_msgs.msg import Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    BoundingVolume,
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    OrientationConstraint,
    PlanningOptions,
    PositionConstraint,
    WorkspaceParameters,
)
from shape_msgs.msg import SolidPrimitive
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration


# ──────────────────────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────────────────────

class State(enum.Enum):
    IDLE     = "IDLE"       # arm ready, waiting for sensor True
    RUNNING  = "RUNNING"    # arm executing sequence
    COOLDOWN = "COOLDOWN"   # sequence done, waiting for sensor False


# ──────────────────────────────────────────────────────────────────────────────
# Config helpers  (copied from pick_place.py)
# ──────────────────────────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def get_offset(cfg: dict, name: str) -> dict:
    raw = cfg["offsets"].get(name, {})
    return {
        "x_offset": raw.get("x_offset", 0.0),
        "y_offset": raw.get("y_offset", 0.0),
        "z_offset": raw.get("z_offset", 0.0),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Motion helpers (copied from pick_place.py)
# ──────────────────────────────────────────────────────────────────────────────

def _make_pose(pos: dict,
               x_override=None,
               y_override=None,
               z_override=None) -> Pose:
    p = Pose()
    p.position.x = x_override if x_override is not None else pos["x"]
    p.position.y = y_override if y_override is not None else pos["y"]
    p.position.z = z_override if z_override is not None else pos["z"]
    p.orientation.x = pos["qx"]
    p.orientation.y = pos["qy"]
    p.orientation.z = pos["qz"]
    p.orientation.w = pos["qw"]
    return p


def _pose_constraints(pose: Pose, base_frame: str, eef_link: str,
                      pos_tol: float, ori_tol: float) -> Constraints:
    pc = PositionConstraint()
    pc.header.frame_id = base_frame
    pc.link_name = eef_link
    bv = BoundingVolume()
    sp = SolidPrimitive()
    sp.type = SolidPrimitive.SPHERE
    sp.dimensions = [pos_tol]
    bv.primitives = [sp]
    bv.primitive_poses = [pose]
    pc.constraint_region = bv
    pc.weight = 1.0

    oc = OrientationConstraint()
    oc.header.frame_id = base_frame
    oc.link_name = eef_link
    oc.orientation = pose.orientation
    oc.absolute_x_axis_tolerance = ori_tol
    oc.absolute_y_axis_tolerance = ori_tol
    oc.absolute_z_axis_tolerance = ori_tol
    oc.weight = 1.0

    c = Constraints()
    c.position_constraints = [pc]
    c.orientation_constraints = [oc]
    return c


def _joint_constraints(joint_positions: dict) -> Constraints:
    c = Constraints()
    for name, value in joint_positions.items():
        jc = JointConstraint()
        jc.joint_name = name
        jc.position = value
        jc.tolerance_above = 0.01
        jc.tolerance_below = 0.01
        jc.weight = 1.0
        c.joint_constraints.append(jc)
    return c


# ──────────────────────────────────────────────────────────────────────────────
# Main node
# ──────────────────────────────────────────────────────────────────────────────

class AiFilmNode(Node):
    """
    Subscribes to /detector (Bool).
    State machine:
      IDLE     → (True)  → RUNNING  (start arm sequence in background thread)
      RUNNING  → (done)  → COOLDOWN
      COOLDOWN → (False) → IDLE
    """

    def __init__(self, cfg: dict, sequence_name: str):
        super().__init__("ai_film_node")

        self._cfg           = cfg
        self._sequence_name = sequence_name
        self._robot_cfg     = cfg["robot"]
        self._planner_cfg   = cfg["planner"]
        self._cons_cfg      = cfg["constraints"]
        self._gripper_cfg   = cfg["gripper"]

        # State
        self._state      = State.IDLE
        self._state_lock = threading.Lock()

        # Arm action client
        self._client = ActionClient(self, MoveGroup, "/move_action")
        self._gripper_pub = self.create_publisher(
            JointTrajectory, "/gripper_controller/joint_trajectory", 10)

        # Subscribe to sensor
        self.create_subscription(Bool, "/detector", self._on_detector, 10)

        # Connect to move_group and home in a background thread
        # (executor must be spinning before futures can resolve)
        threading.Thread(target=self._connect_and_home, daemon=True).start()

    # ── Startup (background thread) ──────────────────────────────────────────

    def _connect_and_home(self):
        """Runs in a background thread after executor has started."""
        self.get_logger().info("Waiting for /move_action server...")
        self._client.wait_for_server()
        self.get_logger().info("Connected to move_group.")
        time.sleep(1.0)
        self.get_logger().info("Going to home position...")
        self._go_home()
        self.get_logger().info(
            f"[{State.IDLE.value}] Waiting for sensor signal on /detector ...")

    # ── Sensor callback ───────────────────────────────────────────────────────

    def _on_detector(self, msg: Bool):
        with self._state_lock:
            state = self._state

        if state == State.IDLE and msg.data:
            self.get_logger().info("Sensor TRUE → starting arm sequence.")
            self._set_state(State.RUNNING)
            t = threading.Thread(target=self._run_sequence_thread, daemon=True)
            t.start()

        elif state == State.COOLDOWN and not msg.data:
            self.get_logger().info(
                "Sensor FALSE → arm re-armed, back to IDLE.")
            self._set_state(State.IDLE)

        elif state == State.RUNNING:
            # Ignore sensor changes while arm is busy
            pass

    # ── State helper ──────────────────────────────────────────────────────────

    def _set_state(self, new_state: State):
        with self._state_lock:
            self._state = new_state
        self.get_logger().info(f"State → [{new_state.value}]")

    # ── Sequence execution (runs in background thread) ────────────────────────

    def _run_sequence_thread(self):
        try:
            seq   = self._cfg["sequences"][self._sequence_name]
            steps = seq["steps"]
            loop  = seq.get("loop", False)

            count = seq.get("count", 0)  # 0 = infinite
            mode = "once" if not loop else (f"loop×{count}" if count > 0 else "loop∞")
            self.get_logger().info(
                f"=== sequence '{self._sequence_name}' start ({mode}) ===")

            iteration = 0
            while rclpy.ok():
                iteration += 1
                if loop:
                    self.get_logger().info(f"--- loop iteration {iteration} ---")
                self._run_steps(steps)
                if not loop:
                    break
                if count > 0 and iteration >= count:
                    break

        except Exception as e:
            self.get_logger().error(f"Sequence error: {e}")
        finally:
            self.get_logger().info(
                "Sequence done. Waiting for sensor to go FALSE before re-arming.")
            self._set_state(State.COOLDOWN)

    def _run_steps(self, steps: list):
        poses = self._cfg["poses"]
        for step in steps:
            if step["type"] == "home":
                self._go_home()
            elif step["type"] == "pick_place":
                pick_pose  = poses[step["pick"]]
                place_pose = poses[step["place"]]
                pick_off   = get_offset(self._cfg, step["pick_offset"])
                place_off  = get_offset(self._cfg, step["place_offset"])
                self._pick_and_place(pick_pose, place_pose, pick_off, place_off)
            else:
                self.get_logger().warn(f"Unknown step type: {step['type']!r}")

    # ── Future wait (thread-safe, no double-spin) ─────────────────────────────

    @staticmethod
    def _wait_future(future):
        """Block the calling thread until *future* is done without spinning."""
        event = threading.Event()
        future.add_done_callback(lambda _: event.set())
        event.wait()

    # ── Motion primitives ─────────────────────────────────────────────────────

    def _send_goal(self, constraints: Constraints) -> bool:
        p      = self._planner_cfg
        ws_min = p["workspace"]["min"]
        ws_max = p["workspace"]["max"]

        req = MotionPlanRequest()
        req.group_name                      = self._robot_cfg["planning_group"]
        req.num_planning_attempts           = p["num_planning_attempts"]
        req.allowed_planning_time           = p["allowed_planning_time"]
        req.max_velocity_scaling_factor     = p["max_velocity_scaling_factor"]
        req.max_acceleration_scaling_factor = p["max_acceleration_scaling_factor"]
        req.goal_constraints                = [constraints]
        req.start_state.is_diff             = True

        ws = WorkspaceParameters()
        ws.header.frame_id                  = self._robot_cfg["base_frame"]
        ws.min_corner.x, ws.min_corner.y, ws.min_corner.z = ws_min
        ws.max_corner.x, ws.max_corner.y, ws.max_corner.z = ws_max
        req.workspace_parameters            = ws

        opts = PlanningOptions()
        opts.plan_only   = False
        opts.look_around = False
        opts.replan      = False

        goal_msg = MoveGroup.Goal()
        goal_msg.request          = req
        goal_msg.planning_options = opts

        future = self._client.send_goal_async(goal_msg)
        self._wait_future(future)
        handle = future.result()

        if not handle.accepted:
            self.get_logger().error("Goal rejected")
            return False

        result_future = handle.get_result_async()
        self._wait_future(result_future)
        result = result_future.result().result

        if result.error_code.val != 1:
            self.get_logger().error(
                f"Motion failed, error_code={result.error_code.val}")
            return False
        return True

    def _go(self, pos: dict,
            x_override=None, y_override=None, z_override=None) -> bool:
        x = x_override if x_override is not None else pos["x"]
        y = y_override if y_override is not None else pos["y"]
        z = z_override if z_override is not None else pos["z"]
        self.get_logger().info(f"  go → ({x:.3f}, {y:.3f}, {z:.3f})")
        pose = _make_pose(pos, x_override, y_override, z_override)
        return self._send_goal(
            _pose_constraints(
                pose,
                base_frame=self._robot_cfg["base_frame"],
                eef_link=self._robot_cfg["eef_link"],
                pos_tol=self._cons_cfg["position_tolerance"],
                ori_tol=self._cons_cfg["orientation_tolerance"],
            )
        )

    def _go_home(self) -> bool:
        self.get_logger().info("  go → home")
        home = {f"joint{i}": 0.0 for i in range(1, 7)}
        return self._send_goal(_joint_constraints(home))

    def _gripper_set(self, width: float):
        g = self._gripper_cfg
        msg = JointTrajectory()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.joint_names = ["gripper_joint1", "gripper_joint2"]
        pt = JointTrajectoryPoint()
        pt.positions = [float(width), float(width)]
        pt.velocities = [0.0, 0.0]
        pt.time_from_start = Duration(sec=1, nanosec=0)
        msg.points = [pt]
        for _ in range(3):
            self._gripper_pub.publish(msg)
            time.sleep(0.1)
        time.sleep(g["move_time"])

    def _pick_and_place(self, pick: dict, place: dict,
                        pick_offset: dict, place_offset: dict):
        log = self.get_logger().info
        log("=== pick & place start ===")
        g = self._gripper_cfg

        pick_hover  = (pick["x"]  + pick_offset["x_offset"],
                       pick["y"]  + pick_offset["y_offset"],
                       pick["z"]  + pick_offset["z_offset"])
        place_hover = (place["x"] + place_offset["x_offset"],
                       place["y"] + place_offset["y_offset"],
                       place["z"] + place_offset["z_offset"])

        self._gripper_set(g["open_width"])
        self._go(pick,  *pick_hover)
        self._go(pick)
        self._gripper_set(g["close_width"])
        self._go(pick,  *pick_hover)
        self._go(place, *place_hover)
        self._go(place)
        self._gripper_set(g["open_width"])
        self._go(place, *place_hover)

        log("=== done ===")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Film — sensor-driven arm")
    parser.add_argument("--config",   default="ai_film/config.yaml",
                        help="Path to YAML config (default: ai_film/config.yaml)")
    parser.add_argument("--sequence", default="chess_loop",
                        help="Sequence name in config (default: chess_loop)")
    args = parser.parse_args()

    cfg = load_config(args.config)

    rclpy.init()
    node = AiFilmNode(cfg, args.sequence)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Pick & place using the /move_action action client.
Talks to the already-running move_group (pixi run piper_moveit).

Terminals:
  1: pixi run can
  2: pixi run piper_moveit
  3: python3 pick_place.py [--config config.yaml] [--sequence chess_loop]

All tunable parameters (poses, offsets, gripper widths, planner settings,
sequence steps) live in config.yaml — edit that file, not this one.
"""

import argparse
import time
import threading

import rclpy
import yaml
from rclpy.node import Node
from rclpy.action import ActionClient

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


# ─── Config loading ───────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def get_offset(cfg: dict, name: str) -> dict:
    """Return offset dict always containing x/y/z keys (missing ones → 0.0)."""
    raw = cfg["offsets"].get(name, {})
    return {
        "x_offset": raw.get("x_offset", 0.0),
        "y_offset": raw.get("y_offset", 0.0),
        "z_offset": raw.get("z_offset", 0.0),
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


def _pose_constraints(pose: Pose,
                      base_frame: str,
                      eef_link: str,
                      pos_tol: float,
                      ori_tol: float) -> Constraints:
    """Build Constraints (position + orientation) for a Cartesian goal."""
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
    """Build Constraints for named joint positions (e.g. home)."""
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


# ─── Node ────────────────────────────────────────────────────────────────────

class PickPlaceNode(Node):

    def __init__(self, cfg: dict):
        super().__init__("pick_place_node")
        self._cfg         = cfg
        self._robot       = cfg["robot"]
        self._planner     = cfg["planner"]
        self._cons        = cfg["constraints"]
        self._gripper_cfg = cfg["gripper"]

        self._client = ActionClient(self, MoveGroup, "/move_action")
        self._gripper_pub = self.create_publisher(
            JointTrajectory, "/gripper_controller/joint_trajectory", 10)

        self.get_logger().info("Waiting for /move_action server...")
        self._client.wait_for_server()
        self.get_logger().info("Connected to move_group.")
        time.sleep(1.0)

    # ── Motion ───────────────────────────────────────────────────────────────

    def _send_goal(self, constraints: Constraints) -> bool:
        p      = self._planner
        ws_min = p["workspace"]["min"]
        ws_max = p["workspace"]["max"]

        req = MotionPlanRequest()
        req.group_name                      = self._robot["planning_group"]
        req.num_planning_attempts           = p["num_planning_attempts"]
        req.allowed_planning_time           = p["allowed_planning_time"]
        req.max_velocity_scaling_factor     = p["max_velocity_scaling_factor"]
        req.max_acceleration_scaling_factor = p["max_acceleration_scaling_factor"]
        req.goal_constraints                = [constraints]
        req.start_state.is_diff             = True

        ws = WorkspaceParameters()
        ws.header.frame_id                  = self._robot["base_frame"]
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
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()

        if not handle.accepted:
            self.get_logger().error("Goal rejected")
            return False

        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result

        if result.error_code.val != 1:
            self.get_logger().error(
                f"Motion failed, error_code={result.error_code.val}")
            return False
        return True

    def go(self, pos: dict,
           x_override=None,
           y_override=None,
           z_override=None) -> bool:
        x = x_override if x_override is not None else pos["x"]
        y = y_override if y_override is not None else pos["y"]
        z = z_override if z_override is not None else pos["z"]
        self.get_logger().info(f"  go → ({x:.3f}, {y:.3f}, {z:.3f})")
        pose = _make_pose(pos, x_override, y_override, z_override)
        return self._send_goal(
            _pose_constraints(
                pose,
                base_frame=self._robot["base_frame"],
                eef_link=self._robot["eef_link"],
                pos_tol=self._cons["position_tolerance"],
                ori_tol=self._cons["orientation_tolerance"],
            )
        )

    def go_home(self) -> bool:
        self.get_logger().info("  go → home")
        home = {f"joint{i}": 0.0 for i in range(1, 7)}
        return self._send_goal(_joint_constraints(home))

    # ── Gripper ──────────────────────────────────────────────────────────────

    def gripper_set(self, width: float):
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

    # ── Pick & place ─────────────────────────────────────────────────────────

    def pick_and_place(self, pick: dict, place: dict,
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

        self.gripper_set(g["open_width"])
        self.go(pick,  *pick_hover)
        self.go(pick)
        self.gripper_set(g["close_width"])
        self.go(pick,  *pick_hover)
        self.go(place, *place_hover)
        self.go(place)
        self.gripper_set(g["open_width"])
        self.go(place, *place_hover)

        log("=== done ===")


# ─── Sequence runner ─────────────────────────────────────────────────────────

def _run_steps(robot: PickPlaceNode, cfg: dict, steps: list):
    """Execute one pass through all steps in the list."""
    poses = cfg["poses"]
    for step in steps:
        if step["type"] == "home":
            robot.go_home()

        elif step["type"] == "pick_place":
            pick_pose   = poses[step["pick"]]
            place_pose  = poses[step["place"]]
            pick_off    = get_offset(cfg, step["pick_offset"])
            place_off   = get_offset(cfg, step["place_offset"])
            robot.pick_and_place(pick_pose, place_pose, pick_off, place_off)

        else:
            robot.get_logger().warn(f"Unknown step type: {step['type']!r}")


def run_sequence(robot: PickPlaceNode, cfg: dict, sequence_name: str):
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
                _run_steps(robot, cfg, steps)
        except KeyboardInterrupt:
            print("\nStopped.")

        print("\nLoop ended.")

    else:
        input("Press ENTER to run once... ")
        try:
            _run_steps(robot, cfg, steps)
        except KeyboardInterrupt:
            print("\nStopped.")
        print("\nDone.")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pick & place runner")
    parser.add_argument("--config",   default="config.yaml",
                        help="Path to YAML config (default: config.yaml)")
    parser.add_argument("--sequence", default="chess_loop",
                        help="Sequence name from config (default: chess_loop)")
    args = parser.parse_args()

    cfg = load_config(args.config)

    rclpy.init()
    robot = PickPlaceNode(cfg)

    print("\n[READY] Stand clear.")
    input("Press ENTER to go HOME... ")
    robot.go_home()

    run_sequence(robot, cfg, args.sequence)

    rclpy.shutdown()


if __name__ == "__main__":
    main()
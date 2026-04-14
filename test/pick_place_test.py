#!/usr/bin/env python3
"""
Pick & place using the /move_action action client.
Talks to the already-running move_group (pixi run piper_moveit).

Terminals:
  1: pixi run can
  2: pixi run piper_moveit
  3: python3 test/pick_place_test.py
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import Pose
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest, Constraints,
    PositionConstraint, OrientationConstraint,
    BoundingVolume, WorkspaceParameters,
    PlanningOptions, JointConstraint,
)
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import time

# ─── Measured TCP poses (/feedback/tcp_pose --once) ──────────────────────────
POS1 = dict(x=0.425614, y=0.184159,  z=0.127559,
            qx=0.02974, qy=0.9933,   qz=0.04344, qw=0.10313)
POS2 = dict(x=0.222914, y=-0.130998, z=0.133609,
            qx=0.02753, qy=0.9987,   qz=0.00170, qw=-0.04321)

Z_HOVER_OFFSET      = 0.08   # metres added above measured z for safe travel
GRIPPER_OPEN_WIDTH  = 0.03   # confirmed: enough to open
GRIPPER_CLOSE_WIDTH = 0.018  # confirmed: grips item
GRIPPER_JOINTS      = ["gripper_joint1", "gripper_joint2"]

PLANNING_GROUP = "arm"
EEF_LINK       = "tcp_link"
BASE_FRAME     = "base_link"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_pose(pos: dict, z_override=None) -> Pose:
    p = Pose()
    p.position.x = pos["x"]
    p.position.y = pos["y"]
    p.position.z = z_override if z_override is not None else pos["z"]
    p.orientation.x = pos["qx"]
    p.orientation.y = pos["qy"]
    p.orientation.z = pos["qz"]
    p.orientation.w = pos["qw"]
    return p


def _pose_constraints(pose: Pose, pos_tol=0.001, ori_tol=0.003) -> Constraints:
    """Build Constraints (position + orientation) for a Cartesian goal."""
    pc = PositionConstraint()
    pc.header.frame_id = BASE_FRAME
    pc.link_name = EEF_LINK
    bv = BoundingVolume()
    sp = SolidPrimitive()
    sp.type = SolidPrimitive.SPHERE
    sp.dimensions = [pos_tol]
    bv.primitives = [sp]
    bv.primitive_poses = [pose]
    pc.constraint_region = bv
    pc.weight = 1.0

    oc = OrientationConstraint()
    oc.header.frame_id = BASE_FRAME
    oc.link_name = EEF_LINK
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

class PickPlaceTest(Node):

    def __init__(self):
        super().__init__("pick_place_test")

        self._client = ActionClient(self, MoveGroup, "/move_action")
        self._gripper_pub = self.create_publisher(
            JointTrajectory, "/gripper_controller/joint_trajectory", 10)

        self.get_logger().info("Waiting for /move_action server...")
        self._client.wait_for_server()
        self.get_logger().info("Connected to move_group.")
        time.sleep(1.0)

    # ── Motion ───────────────────────────────────────────────────────────────

    def _send_goal(self, constraints: Constraints) -> bool:
        req = MotionPlanRequest()
        req.group_name = PLANNING_GROUP
        req.num_planning_attempts = 5
        req.allowed_planning_time = 10.0
        req.max_velocity_scaling_factor = 0.3
        req.max_acceleration_scaling_factor = 0.3
        req.goal_constraints = [constraints]
        req.start_state.is_diff = True

        ws = WorkspaceParameters()
        ws.header.frame_id = BASE_FRAME
        ws.min_corner.x = -1.0; ws.min_corner.y = -1.0; ws.min_corner.z = -0.5
        ws.max_corner.x =  1.0; ws.max_corner.y =  1.0; ws.max_corner.z =  2.0
        req.workspace_parameters = ws

        opts = PlanningOptions()
        opts.plan_only = False
        opts.look_around = False
        opts.replan = False

        goal_msg = MoveGroup.Goal()
        goal_msg.request = req
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

    def go(self, pos: dict, z_override=None) -> bool:
        z = z_override if z_override is not None else pos["z"]
        self.get_logger().info(
            f"  go → ({pos['x']:.3f}, {pos['y']:.3f}, z={z:.3f})")
        pose = _make_pose(pos, z_override)
        return self._send_goal(_pose_constraints(pose))

    def go_home(self) -> bool:
        self.get_logger().info("  go → home")
        home = {f"joint{i}": 0.0 for i in range(1, 7)}
        return self._send_goal(_joint_constraints(home))

    # ── Gripper ──────────────────────────────────────────────────────────────

    def gripper_set(self, width: float):
        msg = JointTrajectory()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.joint_names = GRIPPER_JOINTS
        pt = JointTrajectoryPoint()
        pt.positions = [float(width), float(width)]
        pt.velocities = [0.0, 0.0]
        pt.time_from_start = Duration(sec=1, nanosec=0)
        msg.points = [pt]
        for _ in range(3):
            self._gripper_pub.publish(msg)
            time.sleep(0.1)
        time.sleep(1.0)  # wait for gripper to move

    # ── Pick & place ─────────────────────────────────────────────────────────

    def pick_and_place(self, pick: dict, place: dict):
        log = self.get_logger().info
        log("=== pick & place start ===")

        self.gripper_set(GRIPPER_OPEN_WIDTH)
        self.go(pick,  z_override=pick["z"]  + Z_HOVER_OFFSET)
        self.go(pick)
        self.gripper_set(GRIPPER_CLOSE_WIDTH)
        self.go(pick,  z_override=pick["z"]  + Z_HOVER_OFFSET)
        self.go(place, z_override=place["z"] + Z_HOVER_OFFSET)
        self.go(place)
        self.gripper_set(GRIPPER_OPEN_WIDTH)
        self.go(place, z_override=place["z"] + Z_HOVER_OFFSET)

        log("=== done ===")


# ─── Entry point ─────────────────────────────────────────────────────────────

# def main():
#     rclpy.init()
#     robot = PickPlaceTest()

#     print("\n[READY] Stand clear.")
#     input("Press ENTER to go HOME... ")
#     robot.go_home()

#     print("Press ENTER each step. Ctrl+C to quit.\n")
#     try:
#         while True:
#             input("Press ENTER to run pick-and-place (POS1 → POS2)... ")
#             robot.pick_and_place(POS1, POS2)

#             input("Press ENTER to return HOME... ")
#             robot.go_home()
#     except KeyboardInterrupt:
#         print("\nStopped.")

#     rclpy.shutdown()



def main():              
      rclpy.init()                                                             
      robot = PickPlaceTest()

      print("\n[READY] Stand clear.")                                           
      input("Press ENTER to go HOME... ")
      robot.go_home()                                                           
                  
      print("Press ENTER to start loop. Press ENTER again to stop.\n")          
      input("Press ENTER to start... ")
                                                                                
      import threading
      stop_flag = threading.Event()                                             
                                                                                
      def wait_for_enter():
          input("Press ENTER to stop...\n")                                     
          stop_flag.set()

      t = threading.Thread(target=wait_for_enter, daemon=True)                  
      t.start()
                                                                                
      try:        
          while not stop_flag.is_set():
              robot.pick_and_place(POS1, POS2)
              if stop_flag.is_set(): break
              robot.go_home()                                                   
              if stop_flag.is_set(): break
              robot.pick_and_place(POS2, POS1)                                  
              if stop_flag.is_set(): break
              robot.go_home()                                                   
      except KeyboardInterrupt:
          print("\nStopped.")                                                   
                  
      print("\nLoop ended.")
      rclpy.shutdown()



if __name__ == "__main__":
    main()

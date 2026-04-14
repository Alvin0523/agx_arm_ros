import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from moveit.planning import MoveItPy
from agx_arm_chess.board import get_square_xy, Z_HOVER, Z_PICK
from agx_arm_chess.scene_manager import SceneManager
from agx_arm_chess.board import INITIAL_PIECES
import time

class ChessPlayer(Node):
    def __init__(self):
        super().__init__('chess_player')

        # MoveIt2
        self.moveit = MoveItPy(node_name="chess_moveit")
        self.arm = self.moveit.get_planning_component("arm")
        self.gripper_pub = self.create_publisher(
            JointState, '/control/joint_states', 10)

        # Scene
        self.scene = SceneManager(self)
        time.sleep(1.0)

        # Setup board
        self.scene.add_board()
        self._board_state = {}
        self.setup_initial_pieces()

    def setup_initial_pieces(self):
        for square, name in INITIAL_PIECES.items():
            x, y = get_square_xy(square)
            self.scene.add_piece(name, x, y)
            self._board_state[square] = name
        time.sleep(1.0)

    def go(self, x, y, z):
        pose = PoseStamped()
        pose.header.frame_id = "base_link"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pose.pose.orientation.w = 1.0

        self.arm.set_goal_state(
            pose_stamped_msg=pose,
            pose_link="tcp_link")
        result = self.arm.plan()
        if result:
            self.moveit.execute(result.trajectory)
            return True
        self.get_logger().error(f"Planning failed for {x},{y},{z}")
        return False

    def gripper_open(self):
        msg = JointState()
        msg.name = ['gripper']
        msg.position = [0.08]
        msg.effort = [1.0]
        self.gripper_pub.publish(msg)
        time.sleep(1.0)

    def gripper_close(self):
        msg = JointState()
        msg.name = ['gripper']
        msg.position = [0.01]
        msg.effort = [2.0]
        self.gripper_pub.publish(msg)
        time.sleep(1.0)

    def move_piece(self, from_sq, to_sq):
        self.get_logger().info(f"Moving {from_sq} -> {to_sq}")

        fx, fy = get_square_xy(from_sq)
        tx, ty = get_square_xy(to_sq)

        # Remove piece from collision scene so arm can grab it
        piece_name = self._board_state.get(from_sq)
        if piece_name:
            self.scene.remove_piece(piece_name)

        # Remove captured piece if any
        captured = self._board_state.get(to_sq)
        if captured:
            self.scene.remove_piece(captured)

        # Execute pick and place
        self.gripper_open()
        self.go(fx, fy, Z_HOVER)
        self.go(fx, fy, Z_PICK)
        self.gripper_close()
        self.go(fx, fy, Z_HOVER)
        self.go(tx, ty, Z_HOVER)
        self.go(tx, ty, Z_PICK)
        self.gripper_open()
        self.go(tx, ty, Z_HOVER)

        # Update board state and collision scene
        if piece_name:
            self.scene.add_piece(piece_name, tx, ty)
            self._board_state[to_sq] = piece_name
            del self._board_state[from_sq]

    def go_home(self):
        self.arm.set_goal_state(configuration_name="home")
        result = self.arm.plan()
        if result:
            self.moveit.execute(result.trajectory)

def main():
    rclpy.init()
    robot = ChessPlayer()

    print("Scene ready. ARM WILL MOVE TO HOME POSITION.")
    input("Press ENTER when safe to proceed...")

    robot.go_home()

    print("ARM WILL START CHESS MOVES.")
    input("Press ENTER to start...")

    moves = [
        ('e2', 'e4'),
        ('d2', 'd4'),
        ('f1', 'c4'),
    ]

    for from_sq, to_sq in moves:
        robot.move_piece(from_sq, to_sq)
        time.sleep(1.0)

    robot.go_home()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
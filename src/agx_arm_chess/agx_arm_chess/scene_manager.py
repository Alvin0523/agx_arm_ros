from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose
from agx_arm_chess.board import PIECE_HEIGHT, PIECE_RADIUS, BOARD_Z

class SceneManager:
    def __init__(self, node):
        self.node = node
        self.scene_pub = node.create_publisher(
            PlanningScene, '/planning_scene', 10)
        self.pieces = {}  # track piece positions

    def add_piece(self, name, x, y):
        obj = CollisionObject()
        obj.id = name
        obj.header.frame_id = "base_link"

        shape = SolidPrimitive()
        shape.type = SolidPrimitive.CYLINDER
        shape.dimensions = [PIECE_HEIGHT, PIECE_RADIUS]

        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = BOARD_Z + PIECE_HEIGHT / 2
        pose.orientation.w = 1.0

        obj.primitives = [shape]
        obj.primitive_poses = [pose]
        obj.operation = CollisionObject.ADD

        scene = PlanningScene()
        scene.world.collision_objects.append(obj)
        scene.is_diff = True
        self.scene_pub.publish(scene)
        self.pieces[name] = (x, y)

    def remove_piece(self, name):
        obj = CollisionObject()
        obj.id = name
        obj.header.frame_id = "base_link"
        obj.operation = CollisionObject.REMOVE

        scene = PlanningScene()
        scene.world.collision_objects.append(obj)
        scene.is_diff = True
        self.scene_pub.publish(scene)
        if name in self.pieces:
            del self.pieces[name]

    def add_board(self):
        """Add the chess board itself as a flat collision box"""
        obj = CollisionObject()
        obj.id = "chess_board"
        obj.header.frame_id = "base_link"

        shape = SolidPrimitive()
        shape.type = SolidPrimitive.BOX
        shape.dimensions = [0.36, 0.36, 0.02]  # 360x360x20mm

        from agx_arm_chess.board import A1_X, A1_Y, SQUARE_SIZE
        pose = Pose()
        pose.position.x = A1_X + 3.5 * SQUARE_SIZE  # center
        pose.position.y = A1_Y + 3.5 * SQUARE_SIZE
        pose.position.z = BOARD_Z - 0.01
        pose.orientation.w = 1.0

        obj.primitives = [shape]
        obj.primitive_poses = [pose]
        obj.operation = CollisionObject.ADD

        scene = PlanningScene()
        scene.world.collision_objects.append(obj)
        scene.is_diff = True
        self.scene_pub.publish(scene)
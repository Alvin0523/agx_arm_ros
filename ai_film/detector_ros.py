import time

from acconeer.exptool import a121
from acconeer.exptool.a121.algo.presence import Detector, DetectorConfig
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool


def open_client_with_retry(port="/dev/ttyACM0", retries=5, delay=1.5):
    last_exception = None

    for attempt in range(1, retries + 1):
        try:
            print(f"Connecting to {port} (attempt {attempt}/{retries})...")
            client = a121.Client.open(serial_port=port)
            print("Connected successfully.")
            return client
        except Exception as e:
            print(f"Connection failed: {e}")
            last_exception = e
            time.sleep(delay)

    raise last_exception


def main():
    rclpy.init()
    node = Node("acconeer_presence_detector")
    pub = node.create_publisher(Bool, "/detector", 10)

    client = open_client_with_retry("/dev/ttyACM0")

    detector = Detector(
        client=client,
        sensor_id=1,
        detector_config=DetectorConfig(
            start_m=0.1,
            end_m=0.2,
            intra_detection_threshold=1.8,
            inter_detection_threshold=1.5,
            inter_frame_presence_timeout=1,
        ),
    )

    detector.start()
    last_state = None

    try:
        while rclpy.ok():
            result = detector.get_next()
            state = int(result.presence_detected)

            if state != last_state:
                msg = Bool()
                msg.data = bool(state)
                pub.publish(msg)
                node.get_logger().info(f"/detector -> {msg.data}")
                last_state = state

            rclpy.spin_once(node, timeout_sec=0.0)

    except KeyboardInterrupt:
        node.get_logger().info("Quit.")
    finally:
        detector.stop()
        client.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

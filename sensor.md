# Sensor 集成变更记录

---

## 1. 安装 acconeer-exptool

在 Pixi 环境中通过 PyPI 安装传感器依赖：

```toml
# pixi.toml [pypi-dependencies]
acconeer-exptool = ">=7.2.0, <8"
```

执行命令：
```bash
pixi add --pypi acconeer-exptool
```

---

## 2. NumPy 版本约束（兼容性修复）

**问题：** `acconeer-exptool` 使用了 `np.complex_`，该符号在 NumPy 2.0 中已移除，导致运行时报错：
```
AttributeError: `np.complex_` was removed in the NumPy 2.0 release. Use `np.complex128` instead.
```

**修复：** 在 `pixi.toml` 中限制 NumPy 版本：
```toml
# pixi.toml [dependencies]
numpy = "<2"
```

执行命令：
```bash
pixi add "numpy<2"
```

**后续：** 待 `acconeer-exptool` 发布兼容 NumPy 2.x 的版本后可移除此约束。

---

## 3. 新增传感器联动主程序

新建 `ai_film/ai_film_main.py`，实现传感器驱动机械臂的三状态机：

```
IDLE ──(传感器 True)──▶ RUNNING ──(sequence执行完)──▶ COOLDOWN
  ▲                                                         │
  └──────────────(传感器 False)────────────────────────────┘
```

- **IDLE**：订阅 `/detector`，等待传感器返回 `True`
- **RUNNING**：后台线程执行机械臂 sequence，期间忽略传感器信号
- **COOLDOWN**：任务完成后等待传感器变 `False` 再重新待命

新增 Pixi 任务：
```toml
# pixi.toml [tasks]
ai_film = { cmd = "python3 ai_film/ai_film_main.py --config ai_film/config.yaml --sequence chess_loop", description = "sensor-driven arm: detect human → run sequence" }
```

使用方式（四个终端）：
```bash
pixi run can          # 1. CAN 总线
pixi run piper_moveit # 2. MoveIt
pixi run detect       # 3. 传感器
pixi run ai_film      # 4. 主程序联动
```

---

## 4. 修复 pixi PATH 问题

pixi 安装在 `~/.pixi/bin/pixi`，但系统 PATH 未包含该目录，导致 `pixi: command not found`。

**修复：** 在 `~/.bashrc` 末尾添加：
```bash
export PATH="/home/orin0/.pixi/bin:$PATH"
```

---

## 5. 重建 ROS 工作空间

项目从旧路径 `/home/orin0/tf_card/dev_dir/agx_arm_ros/` 移动到新路径后，`build/`、`install/` 目录内有大量硬编码旧路径，导致 `piper_moveit` 等任务失败。

**修复：** 清除旧产物并重新编译：
```bash
rm -rf build/ install/ log/
pixi run build
```

---

## 6. pixi.toml tasks 变更汇总

### 6.1 `chess` 任务路径修复

原路径 `test/ai_film/pick_place.py` 文件不存在，修正为：
```toml
chess = { cmd = "python3 ai_film/pick_place.py --config ai_film/config.yaml", description = "play chess" }
```

### 6.2 `piper_moveit` 改为 MoveIt launch + 夹爪参数

原来使用 `start_single_agx_arm_rviz.launch.py`（无 MoveIt，`/move_action` 永远不可用），改为：
```toml
piper_moveit = {cmd = "ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can2 arm_type:=piper effector_type:=agx_gripper follow:=true control:=true", description = "real arm control and follow"}
```

关键变更：
- launch 文件：`start_single_agx_arm_rviz` → `start_single_agx_arm_moveit`
- 新增 `effector_type:=agx_gripper`（启用夹爪驱动，否则夹爪不响应）

### 6.3 新增 `piper_rviz` 任务

保留原来仅 RViz（无 MoveIt）的启动方式：
```toml
piper_rviz = {cmd = "ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can2 arm_type:=piper follow:=true control:=true", description = "arm with rviz (no MoveIt)"}
```

### 6.4 当前完整 tasks 一览

```toml
[tasks]
build        = {cmd = "colcon build --symlink-install"}
arm          = {cmd = "ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can2 arm_type:=piper effector_type:=agx_gripper tcp_offset:='[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]'"}
piper_moveit = {cmd = "ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can2 arm_type:=piper effector_type:=agx_gripper follow:=true control:=true"}
piper_rviz   = {cmd = "ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py can_port:=can2 arm_type:=piper follow:=true control:=true"}
chess        = {cmd = "python3 ai_film/pick_place.py --config ai_film/config.yaml"}
ai_film      = {cmd = "python3 ai_film/ai_film_main.py --config ai_film/config.yaml --sequence chess_loop"}
can          = {cmd = "bash scripts/can_activate_can2.sh"}
home         = {cmd = "ros2 service call /move_home std_srvs/srv/Empty"}
down         = {cmd = "ros2 service call /enable_agx_arm std_srvs/srv/SetBool \"{data: false}\""}
pose         = {cmd = "ros2 topic echo /feedback/tcp_pose --once"}
detect       = {cmd = "python3 /home/orin0/tf_card/ai_film/agx_arm_ros/ai_film/detector_ros.py"}
```

---

## 7. ai_film_main.py 架构与 bug 修复

### 7.1 执行器改为 MultiThreadedExecutor

原来 `rclpy.spin()` 使用单线程执行器，后台线程调用 `rclpy.spin_until_future_complete()` 会与主线程争用执行器，导致 `"generator already executing"` 报错。

**修复：**
```python
from rclpy.executors import MultiThreadedExecutor
executor = MultiThreadedExecutor()
executor.add_node(node)
executor.spin()
```

### 7.2 Future 等待改为 threading.Event

摒弃 `rclpy.spin_until_future_complete()`，改用不阻塞执行器的等待方式：
```python
@staticmethod
def _wait_future(future):
    event = threading.Event()
    future.add_done_callback(lambda _: event.set())
    event.wait()
```

### 7.3 启动时 home 动作死锁修复

`__init__` 在 `executor.spin()` 之前执行，直接调用 `_go_home()` 会死锁（future 回调永远触发不了）。

**修复：** 在后台线程中完成连接和回原点：
```python
# __init__ 里只启动线程
threading.Thread(target=self._connect_and_home, daemon=True).start()

# 后台线程在 executor spin 之后才真正执行
def _connect_and_home(self):
    self._client.wait_for_server()
    self._go_home()
    # → 打印 [IDLE] 等待传感器
```

### 7.4 支持 loop 和 count 控制循环次数

`config.yaml` 的 sequence 支持两个字段：

```yaml
chess_loop:
  loop: true    # true = 循环执行；false = 只执行一遍
  count: 0      # 0 = 无限循环；正整数 = 执行指定次数后进入 COOLDOWN
  steps: [...]
```

| `loop` | `count` | 行为 |
|--------|---------|------|
| `false` | 任意 | 执行一遍 |
| `true` | `0` | 无限循环 |
| `true` | `3` | 循环 3 次后结束 |

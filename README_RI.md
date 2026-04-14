To run
```bash
pixi run can
pixi run piper_moveit
```

ros2 service call /enable_agx_arm std_srvs/srv/SetBool "{data: false}"


pos1
(agx_arm_ros) orin0@orin0:~/tf_card/dev_dir/agx_arm_ros$ pixi run ros2 topic echo /feedback/tcp_pose --once
header:
  stamp:
    sec: 1774943094
    nanosec: 40847778
  frame_id: ''
pose:
  position:
    x: 0.425614
    y: 0.184159
    z: 0.127559
  orientation:
    x: 0.02974049252236509
    y: 0.9932734457662312
    z: 0.04344249368401573
    w: 0.10313154116330818



pos2
(agx_arm_ros) orin0@orin0:~/tf_card/dev_dir/agx_arm_ros$ pixi run ros2 topic echo /feedback/tcp_pose --once
header:
  stamp:
    sec: 1774943148
    nanosec: 38975238
  frame_id: ''
pose:
  position:
    x: 0.222914
    y: -0.130998
    z: 0.133609
  orientation:
    x: 0.027525213858530656
    y: 0.9986851460654061
    z: 0.0016959618107422192
    w: -0.04321417989383892
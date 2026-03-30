#!/bin/bash

# 示例：sudo bash can_activate_can2.sh 1000000

# 1. 配置参数（可修改波特率，默认 1000000）
TARGET_CAN="can2"  
DEFAULT_BITRATE="${1:-1000000}"  #

# 2. 加载 gs_usb 驱动（USB-CAN 必需）
echo "加载 gs_usb 驱动..."
sudo modprobe gs_usb
if [ $? -ne 0 ]; then
    echo "错误: 无法加载 gs_usb 模块，请先确认驱动已编译安装。"
    exit 1
fi

# 3. 检查 can2 是否存在
if ! ip link show "$TARGET_CAN" >/dev/null 2>&1; then
    echo "错误: 未检测到 $TARGET_CAN 接口，请确认 USB-CAN 适配器已插入并识别。"
    echo "提示：可通过 'ip link show type can' 查看所有可用CAN口。"
    exit 1
fi

# 4. 获取 can2 当前状态
echo "检查 $TARGET_CAN 当前状态..."
# 检查是否已激活
IS_LINK_UP=$(ip link show "$TARGET_CAN" | grep -q "UP" && echo "yes" || echo "no")
# 获取当前波特率
CURRENT_BITRATE=$(ip -details link show "$TARGET_CAN" | grep -oP 'bitrate \K\d+' || echo "0")

# 5. 配置并激活 can2
if [ "$IS_LINK_UP" = "yes" ] && [ "$CURRENT_BITRATE" -eq "$DEFAULT_BITRATE" ]; then
    echo "✅ $TARGET_CAN 已激活，波特率为 $DEFAULT_BITRATE（无需修改）。"
else
    echo "配置 $TARGET_CAN 波特率为 $DEFAULT_BITRATE 并激活..."
    # 先关闭接口
    sudo ip link set "$TARGET_CAN" down
    # 设置波特率
    sudo ip link set "$TARGET_CAN" type can bitrate "$DEFAULT_BITRATE"
    # 激活接口
    sudo ip link set "$TARGET_CAN" up
    
    # 验证是否成功
    if ip link show "$TARGET_CAN" | grep -q "UP"; then
        echo "✅ $TARGET_CAN 激活成功！当前波特率：$DEFAULT_BITRATE"
    else
        echo "❌ $TARGET_CAN 激活失败，请检查硬件或驱动。"
        exit 1
    fi
fi

echo "===== 操作完成 ====="
# 输出 can2 最终状态
ip link show "$TARGET_CAN" | grep -E "state|bitrate"

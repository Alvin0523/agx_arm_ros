#!/bin/bash
# Activate the robot-arm CAN adapter as "can2".
# Dynamically finds the USB port of the single connected CAN adapter.

BITRATE="${1:-1000000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Count how many CAN interfaces are present
CAN_IFACES=($(ip -br link show type can | awk '{print $1}'))
COUNT=${#CAN_IFACES[@]}

if [ "$COUNT" -eq 0 ]; then
    echo "❌ No CAN adapter detected. Is it plugged in?"
    exit 1
fi

if [ "$COUNT" -gt 1 ]; then
    echo "⚠️  Multiple CAN interfaces found: ${CAN_IFACES[*]}"
    echo "   Plug in only the robot-arm CAN adapter, or pass the USB port explicitly:"
    echo "   sudo bash can_activate.sh can2 1000000 <USB_PORT>"
    exit 1
fi

IFACE="${CAN_IFACES[0]}"
USB_PORT=$(sudo ethtool -i "$IFACE" | grep "bus-info" | awk '{print $2}')

if [ -z "$USB_PORT" ]; then
    echo "❌ Could not read USB port for interface $IFACE."
    exit 1
fi

echo "Found CAN adapter: $IFACE → USB port $USB_PORT"
echo "Activating as can2 at bitrate $BITRATE…"
sudo bash "$SCRIPT_DIR/can_activate.sh" can2 "$BITRATE" "$USB_PORT"

#!/usr/bin/env bash
set -e

echo "========================================="
echo " Installing Hexapod Autonomous Control   "
echo "========================================="

# 1. Install System Dependencies
echo "[1/4] Installing dependencies..."
sudo apt update -y
sudo apt install -y python3-pip python3-opencv network-manager

# 2. Install Python Packages
echo "[2/4] Setting up Python dependencies..."
pip3 install flask opencv-python --break-system-packages 2>/dev/null || pip3 install flask opencv-python

# 3. Configure Hotspot Profile via NetworkManager
echo "[3/4] Configuring Hotspot fallback network..."
SSID=$(python3 -c "import config; print(config.HOTSPOT_SSID)")
PASS=$(python3 -c "import config; print(config.HOTSPOT_PASSWORD)")

sudo nmcli connection delete Hexapod-Hotspot 2>/dev/null || true
sudo nmcli connection add type wifi ifname wlan0 mode ap con-name Hexapod-Hotspot ssid "$SSID" autoconnect yes
sudo nmcli connection modify Hexapod-Hotspot 802-11-wireless.band bg
sudo nmcli connection modify Hexapod-Hotspot 802-11-wireless.channel 1
sudo nmcli connection modify Hexapod-Hotspot 802-11-wireless-security.key-mgmt wpa-psk
sudo nmcli connection modify Hexapod-Hotspot 802-11-wireless-security.psk "$PASS"
sudo nmcli connection modify Hexapod-Hotspot wifi-sec.pmf 1
sudo nmcli connection modify Hexapod-Hotspot ipv4.method shared
sudo nmcli connection modify Hexapod-Hotspot ipv4.addresses 192.168.4.1/24
sudo nmcli connection modify Hexapod-Hotspot connection.autoconnect-priority 1

# 4. Generate & Enable Systemd Service
echo "[4/4] Registering background system service..."
CURRENT_DIR=$(pwd)

sudo bash -c "cat << SERVICE_EOF > /etc/systemd/system/hexapod.service
[Unit]
Description=Hexapod Pilot Flask Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${CURRENT_DIR}
ExecStart=/usr/bin/python3 ${CURRENT_DIR}/pi_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF"

sudo systemctl daemon-reload
sudo systemctl enable hexapod.service
sudo systemctl restart hexapod.service

echo "========================================="
echo " Setup Complete! Service is live.        "
echo " Access at: http://192.168.4.1:5000      "
echo "========================================="

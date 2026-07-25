Centralized Omni-platform Robotic Executer,
S1X-C.O.R.E. is a lightweight control server and background daemon engineered for the Freenove Hexapod Robot Kit on Raspberry Pi OS.

It replaces the default desktop GUI with a headless Flask web dashboard, low-latency Picamera2 live video streaming, and automatic fallback networking so the robot can be controlled outdoors without a router or monitor.

Technical Highlights
Automatic Network Fallback: Uses NetworkManager priorities to try connecting to your home Wi-Fi on boot. If out of range, it spins up an offline Access Point (Hexapod-Net) so phones or Steam Decks can connect directly.

Service Management: Runs headlessly via a systemd background service (hexapod.service). Boots automatically on power-up and auto-restarts if a process crashes.

Hardware Safe Modes: Implements an auto-sleep timer that disables active PWM signals to the servos after 5 seconds of inactivity to eliminate idle jitter and prevent coil burnout.

Responsive Dashboard: Dark industrial UI built with plain CSS grid and vanilla JS. Fully playable via touchscreen or physical keyboard keys (WASD for translation, Arrow keys for pitch, Q/E for rotation, Space to stand).

File Structure
Plaintext
s1x-core/
├── config.py          # Central hardware, network, and camera settings
├── pi_server.py       # Main Flask app, telemetry stream, and hardware execution thread
├── setup.sh           # Automated installer (systemd + nmcli hotspot profile)
├── control.py         # Hardware driver interface for leg kinematics
├── servo.py           # PCA9685 PWM servo board driver
└── adc.py             # PCF8591 ADC voltage monitor driver
Installation & Setup
Prerequisites
Raspberry Pi 3B / 4B / 5 running Raspberry Pi OS (Bookworm or Bullseye).

Freenove Big Hexapod kit fully assembled and calibrated.

Quick Start
Clone the repository and run the setup script with root privileges:

Bash
git clone https://github.com/Connor-Brinkley/s1x-core.git
cd s1x-core
chmod +x setup.sh
sudo ./setup.sh
setup.sh will handle apt dependencies, create the systemd unit file, enable autostart on boot, and register the fallback hotspot connection.

Usage Guide
1. Home Wi-Fi Mode
When powered on within range of your home network, the Pi joins your local Wi-Fi. Access the control panel at:

Plaintext
http://<raspberrypi-local-ip>:5000
2. Offline / Outdoor Hotspot Mode
If no known Wi-Fi networks are found within ~30 seconds:

The Pi automatically broadcasts the Hexapod-Net Wi-Fi network.

Connect your phone or Steam Deck to Hexapod-Net (Default password: hexapodpass).

Open your web browser and navigate to:

Plaintext
http://192.168.4.1:5000
Configuration (config.py)
You can modify system behavior by editing config.py directly without touching server logic:

Python
# Network & Server
SERVER_PORT = 5000          # Web interface port
HOTSPOT_SSID = "Hexapod-Net" # Offline AP name
HOTSPOT_PASSWORD = "hexapodpass" # Must be at least 8 characters

# Camera Settings
CAMERA_WIDTH = 480
CAMERA_HEIGHT = 360
JPEG_QUALITY = 40           # Lower value reduces stream latency over Wi-Fi

# Kinematics & Timing
DEFAULT_WALK_SPEED = 6
WALK_DURATION = 2.5
BODY_LEAN_ANGLE = 20
AUTO_SLEEP_TIMEOUT = 5.0     # Delay (in seconds) before relaxing servos
Service Management & Debugging
Since the server runs via systemd, you can monitor, control, and debug the background process using standard Linux system tools.

1. Service Controls
Check live status:

Bash
sudo systemctl status hexapod.service
View real-time logs & debug errors:

Bash
sudo journalctl -u hexapod.service -f
Restart server (after editing config.py):

Bash
sudo systemctl restart hexapod.service
Stop server:

Bash
sudo systemctl stop hexapod.service
2. Troubleshooting Common Issues
Camera feed not loading:

Ensure no other process (like mjpg-streamer or libcamera-hello) is locking the camera module.

Verify picamera2 is installed properly by testing python3 -c "import picamera2".

Servos twitching or losing power:

Verify the 18650 battery pack is fully charged; low voltage causes PCA9685 brownouts.

Adjust AUTO_SLEEP_TIMEOUT in config.py if servos relax too quickly during pauses.

Hotspot not broadcasting outdoors:

Check network profile status using nmcli connection show.

Force-start the hotspot manually for testing:

Bash
sudo nmcli connection up Hexapod-Hotspot

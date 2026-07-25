# ==========================================
# HEXAPOD PILOT CONTROL CONFIGURATION
# ==========================================

# Server Network Settings
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000

# Access Point (Hotspot) Setup
HOTSPOT_SSID = "Hexapod-Net"
HOTSPOT_PASSWORD = "hexapodpass"

# Video Stream Configuration
CAMERA_WIDTH = 480
CAMERA_HEIGHT = 360
JPEG_QUALITY = 40

# Hardware & Gait Tuning
DEFAULT_WALK_SPEED = 6
WALK_DURATION = 2.5
BODY_LEAN_ANGLE = 20
AUTO_SLEEP_TIMEOUT = 5.0  # Seconds before powering off servos to save power

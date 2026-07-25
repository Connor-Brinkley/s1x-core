import os
import time
import threading
import cv2
from flask import Flask, request, jsonify, Response, render_template_string

# Import centralized configuration
import config

# --- 1. HARDWARE DRIVER INITIALIZATION ---
control_driver = None
try:
    from control import Control
    control_driver = Control()
    control_driver.condition_thread.start()
    if hasattr(control_driver, 'servo_power_disable'):
        control_driver.servo_power_disable.on()
    print("[SYSTEM] Freenove Control driver online.")
except Exception as err:
    print(f"[WARN] Hardware control driver offline: {err}")

# --- 2. SERVO POWER & SLEEP MANAGEMENT ---
servo_timer = None
servo_lock = threading.Lock()

def wake_servos():
    global servo_timer
    with servo_lock:
        if servo_timer is not None:
            servo_timer.cancel()
            servo_timer = None
        if control_driver:
            if hasattr(control_driver, 'servo_power_disable'):
                control_driver.servo_power_disable.off()
            control_driver.relax(False)

def sleep_servos():
    print("[POWER] Idle timeout reached. Disabling servo power.")
    if control_driver:
        if hasattr(control_driver, 'relax'):
            control_driver.relax(True)
        if hasattr(control_driver, 'servo_power_disable'):
            control_driver.servo_power_disable.on()

def schedule_auto_sleep(timeout=config.AUTO_SLEEP_TIMEOUT):
    global servo_timer
    with servo_lock:
        if servo_timer is not None:
            servo_timer.cancel()
        servo_timer = threading.Timer(timeout, sleep_servos)
        servo_timer.start()

# --- 3. CAMERA STREAMING ---
picam2 = None
try:
    from picamera2 import Picamera2
    picam2 = Picamera2()
    cam_config = picam2.create_video_configuration(
        main={"size": (config.CAMERA_WIDTH, config.CAMERA_HEIGHT)}
    )
    picam2.configure(cam_config)
    picam2.start()
    print("[SYSTEM] Picamera2 initialized.")
except Exception as err:
    print(f"[WARN] Camera feed offline: {err}")

def generate_frames():
    while True:
        if picam2 is None:
            time.sleep(0.05)
            continue
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ret, buffer = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

app = Flask(__name__)

# --- 4. EXECUTION PIPELINE ---
def send_freenove_cmd(cmd_list):
    if control_driver:
        control_driver.command_queue = cmd_list
        control_driver.timeout = time.time()

def walk_and_stop(cmd_list, duration):
    wake_servos()
    send_freenove_cmd(cmd_list)
    time.sleep(duration)
    send_freenove_cmd(['CMD_MOVE', '1', '0', '0', str(config.DEFAULT_WALK_SPEED), '0'])
    if control_driver:
        control_driver.move_position(0, 0, 30)
    schedule_auto_sleep()

def lean_robot(y_angle):
    wake_servos()
    if control_driver:
        control_driver.move_position(0, y_angle, 30)
    schedule_auto_sleep()

def execute_action(action_name, speed=config.DEFAULT_WALK_SPEED, duration=config.WALK_DURATION):
    action = action_name.upper().strip()
    speed_str = str(speed)

    if action == "FORWARD":
        cmd = ['CMD_MOVE', '1', '0', '25', speed_str, '0']
        threading.Thread(target=walk_and_stop, args=(cmd, duration)).start()
    elif action == "BACKWARD":
        cmd = ['CMD_MOVE', '1', '0', '-25', speed_str, '0']
        threading.Thread(target=walk_and_stop, args=(cmd, duration)).start()
    elif action == "STRAFE_LEFT":
        cmd = ['CMD_MOVE', '1', '-25', '0', speed_str, '0']
        threading.Thread(target=walk_and_stop, args=(cmd, duration)).start()
    elif action == "STRAFE_RIGHT":
        cmd = ['CMD_MOVE', '1', '25', '0', speed_str, '0']
        threading.Thread(target=walk_and_stop, args=(cmd, duration)).start()
    elif action == "ROTATE_LEFT":
        cmd = ['CMD_MOVE', '1', '0', '0', speed_str, '20']
        threading.Thread(target=walk_and_stop, args=(cmd, duration)).start()
    elif action == "ROTATE_RIGHT":
        cmd = ['CMD_MOVE', '1', '0', '0', speed_str, '-20']
        threading.Thread(target=walk_and_stop, args=(cmd, duration)).start()
    elif action == "LEAN_FORWARD":
        lean_robot(config.BODY_LEAN_ANGLE)
    elif action == "LEAN_BACKWARD":
        lean_robot(-config.BODY_LEAN_ANGLE)
    elif action == "STAND":
        wake_servos()
        send_freenove_cmd(['CMD_MOVE', '1', '0', '0', str(config.DEFAULT_WALK_SPEED), '0'])
        if control_driver:
            control_driver.move_position(0, 0, 35)
        schedule_auto_sleep()
    elif action == "DANCE":
        def dance_routine():
            wake_servos()
            if control_driver:
                for _ in range(int(duration)):
                    control_driver.move_position(0, 20, 30); time.sleep(0.3)
                    control_driver.move_position(0, -20, 10); time.sleep(0.3)
                    control_driver.move_position(20, 0, 25); time.sleep(0.3)
                    control_driver.move_position(-20, 0, 25); time.sleep(0.3)
                control_driver.move_position(0, 0, 30)
            schedule_auto_sleep()
        threading.Thread(target=dance_routine).start()
    elif action == "SLEEP":
        sleep_servos()

# --- 5. CLEAN INDUSTRIAL FRONTEND UI ---
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hexapod Interface</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        :root {
            --bg-primary: #121417;
            --bg-panel: #1b1e23;
            --bg-button: #282d35;
            --btn-hover: #343a44;
            --accent-blue: #2b5b84;
            --accent-teal: #1b6b63;
            --accent-green: #2d6a4f;
            --accent-red: #8b263e;
            --text-main: #e1e4e8;
            --text-muted: #8b949e;
            --border-color: #30363d;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body { 
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-primary); 
            color: var(--text-main); 
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: clamp(12px, 2vw, 24px);
        }
        
        header {
            text-align: center;
            margin-bottom: 12px;
        }

        header h1 { 
            font-size: clamp(18px, 2.2vw, 24px); 
            font-weight: 600;
            letter-spacing: 0.5px;
            color: var(--text-main);
        }

        .dashboard-grid { 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            gap: clamp(12px, 2.5vw, 28px); 
            flex-wrap: wrap; 
            width: 100%;
            max-width: 1100px; 
            margin: 0 auto; 
        }

        .control-panel { 
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            display: flex; 
            flex-direction: column; 
            gap: 12px; 
            align-items: center; 
            flex: 1 1 200px;
            max-width: 260px;
        }

        .control-panel h2 {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        .video-container {
            flex: 2 1 340px;
            max-width: 520px;
            width: 100%;
            display: flex;
            justify-content: center;
        }

        .video-container img { 
            width: 100%; 
            height: auto;
            max-height: 55vh;
            object-fit: contain;
            border-radius: 8px; 
            border: 1px solid var(--border-color); 
            background: #000;
        }

        .pad-grid { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 6px; 
            width: 100%;
        }

        button { 
            background-color: var(--bg-button); 
            color: var(--text-main); 
            border: 1px solid var(--border-color); 
            padding: clamp(10px, 2vw, 14px) 4px; 
            font-size: clamp(11px, 1.2vw, 13px); 
            font-weight: 500; 
            border-radius: 6px; 
            cursor: pointer; 
            touch-action: manipulation;
            user-select: none;
            transition: background 0.1s ease;
        }

        button:hover { background-color: var(--btn-hover); }
        button:active { transform: translateY(1px); }

        .btn-move { background-color: var(--accent-blue); border-color: var(--accent-blue); }
        .btn-rotate { background-color: var(--accent-teal); border-color: var(--accent-teal); }
        .btn-stand { background-color: var(--accent-green); border-color: var(--accent-green); }
        .btn-danger { background-color: var(--accent-red); border-color: var(--accent-red); }

        .action-bar {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 14px;
        }

        .action-bar button {
            padding: 10px 20px;
            font-size: 13px;
        }

        footer { 
            font-size: 12px; 
            color: var(--text-muted); 
            text-align: center;
            margin-top: 12px; 
        }

        @media (max-width: 640px) {
            .dashboard-grid { flex-direction: column; }
            .video-container { order: -1; }
            .control-panel { max-width: 100%; }
        }
    </style>
</head>
<body>

    <header>
        <h1>Hexapod Telemetry & Control</h1>
    </header>

    <div class="dashboard-grid">
        <div class="control-panel">
            <h2>Translation</h2>
            <div class="pad-grid">
                <div></div>
                <button class="btn-move" onclick="sendCmd('FORWARD')">Forward<br><small>(W)</small></button>
                <div></div>

                <button class="btn-move" onclick="sendCmd('STRAFE_LEFT')">Left<br><small>(A)</small></button>
                <button class="btn-stand" onclick="sendCmd('STAND')">Stand<br><small>(Space)</small></button>
                <button class="btn-move" onclick="sendCmd('STRAFE_RIGHT')">Right<br><small>(D)</small></button>

                <div></div>
                <button class="btn-move" onclick="sendCmd('BACKWARD')">Reverse<br><small>(S)</small></button>
                <div></div>
            </div>
        </div>

        <div class="video-container">
            <img src="/video_feed" alt="Realtime Video Feed">
        </div>

        <div class="control-panel">
            <h2>Rotation & Pitch</h2>
            <div class="pad-grid">
                <div></div>
                <button class="btn-rotate" onclick="sendCmd('LEAN_FORWARD')">Pitch Up<br><small>(&#8593;)</small></button>
                <div></div>

                <button class="btn-rotate" onclick="sendCmd('ROTATE_LEFT')">Turn L<br><small>(Q / &#8592;)</small></button>
                <button class="btn-stand" onclick="sendCmd('STAND')">Reset<br><small>(R)</small></button>
                <button class="btn-rotate" onclick="sendCmd('ROTATE_RIGHT')">Turn R<br><small>(E / &#8594;)</small></button>

                <div></div>
                <button class="btn-rotate" onclick="sendCmd('LEAN_BACKWARD')">Pitch Dn<br><small>(&#8595;)</small></button>
                <div></div>
            </div>
        </div>
    </div>

    <div class="action-bar">
        <button onclick="sendCmd('DANCE')">Sequence Routine</button>
        <button class="btn-danger" onclick="sendCmd('SLEEP')">Servo Sleep (X)</button>
    </div>

    <footer>
        Keyboard Shortcuts Enabled | Dual-Pad Control Mode
    </footer>

    <script>
        function sendCmd(action) {
            fetch('/cmd', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({text: action}) 
            }).catch(err => console.error("Transmission error:", err));
        }

        document.addEventListener('keydown', function(event) {
            const key = event.key;
            const keyLower = key.toLowerCase();
            if (keyLower === 'w') sendCmd('FORWARD');
            else if (keyLower === 's') sendCmd('BACKWARD');
            else if (keyLower === 'a') sendCmd('STRAFE_LEFT');
            else if (keyLower === 'd') sendCmd('STRAFE_RIGHT');
            else if (keyLower === 'q' || key === 'ArrowLeft') sendCmd('ROTATE_LEFT');
            else if (keyLower === 'e' || key === 'ArrowRight') sendCmd('ROTATE_RIGHT');
            else if (key === 'ArrowUp') sendCmd('LEAN_FORWARD');
            else if (key === 'ArrowDown') sendCmd('LEAN_BACKWARD');
            else if (key === ' ' || keyLower === 'r') sendCmd('STAND');
            else if (keyLower === 'x') sendCmd('SLEEP');
        });
    </script>
</body>
</html>
"""

# --- 6. API ENDPOINTS ---
@app.route('/')
def dashboard():
    return render_template_string(HTML_DASHBOARD)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cmd', methods=['POST'])
def receive_command():
    data = request.get_json()
    command = "STAND"
    speed = config.DEFAULT_WALK_SPEED
    duration = config.WALK_DURATION
    
    if data and "text" in data:
        parts = data["text"].strip().split()
        if len(parts) >= 1: command = parts[0]
        if len(parts) >= 2: speed = int(parts[1])
        if len(parts) >= 3: duration = float(parts[2])
        
    execute_action(command, speed, duration)
    return jsonify({"status": "success", "command": command})

if __name__ == '__main__':
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, threaded=True)


from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import serial, threading, time, json, sqlite3, csv, os

app = Flask(__name__)
app.config["SECRET_KEY"] = "exam-iot-secret"
socketio = SocketIO(app)

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
DB_FILE = "archive.db"
CSV_FILE = "archive.csv"

serial_connection = None
reader_thread = None
thread_running = False
system_opened = False
monitoring = False
current_session = 0

parameters = {
    "sensitivity": 1.0,
    "brightness": 200,
    "mode": "Sound monitor"
}

def init_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT,
            sound REAL,
            normalized_sound REAL,
            freq REAL,
            mode INTEGER,
            brightness INTEGER,
            on_state INTEGER,
            sensitivity REAL,
            web_mode TEXT
        )
    """)
    conn.commit()
    conn.close()

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id","session_id","timestamp","sound","normalized_sound","freq","mode","brightness","on_state","sensitivity","web_mode"])

def next_csv_id():
    if not os.path.exists(CSV_FILE):
        return 1
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if len(rows) <= 1:
        return 1
    try:
        return int(rows[-1][0]) + 1
    except:
        return 1

def save_to_database(d):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO measurements (
            session_id,timestamp,sound,normalized_sound,freq,mode,brightness,on_state,sensitivity,web_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        d["session_id"], d["timestamp"], d["sound"], d["normalized_sound"], d["freq"],
        d["mode"], d["brightness"], d["on"], parameters["sensitivity"], parameters["mode"]
    ))
    conn.commit()
    conn.close()

def save_to_csv(d):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            next_csv_id(), d["session_id"], d["timestamp"], d["sound"], d["normalized_sound"],
            d["freq"], d["mode"], d["brightness"], d["on"], parameters["sensitivity"], parameters["mode"]
        ])

def send_command(cmd):
    global serial_connection
    try:
        if serial_connection and serial_connection.is_open:
            serial_connection.write((cmd + "\n").encode("utf-8"))
            return True
    except:
        pass
    return False

def serial_reader():
    global thread_running, serial_connection, monitoring, current_session
    while thread_running:
        try:
            if serial_connection is None or not serial_connection.is_open:
                time.sleep(0.2)
                continue

            line = serial_connection.readline().decode(errors="ignore").strip()
            if not line:
                continue

            try:
                arduino = json.loads(line)
            except:
                continue

            if "sound" not in arduino:
                continue

            sound = float(arduino.get("sound", 0))
            freq = float(arduino.get("freq", 0))
            mode = int(arduino.get("mode", 0))
            brightness = int(arduino.get("brightness", parameters["brightness"]))
            on_state = int(arduino.get("on", 1))
            normalized = sound * float(parameters["sensitivity"])

            data = {
                "session_id": current_session,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sound": round(sound, 2),
                "normalized_sound": round(normalized, 2),
                "freq": round(freq, 2),
                "mode": mode,
                "brightness": brightness,
                "on": on_state,
                "sensitivity": parameters["sensitivity"],
                "web_mode": parameters["mode"]
            }

            if monitoring:
                save_to_database(data)
                save_to_csv(data)
                socketio.emit("newdata", data)

        except Exception as e:
            socketio.emit("system_message", {"message": "Serial error: " + str(e)})
            time.sleep(0.5)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status")
def status():
    return jsonify({
        "opened": system_opened,
        "monitoring": monitoring,
        "session_id": current_session,
        "port": SERIAL_PORT,
        "parameters": parameters
    })

@app.route("/open", methods=["POST"])
def open_system():
    global serial_connection, reader_thread, thread_running, system_opened
    if system_opened:
        return jsonify({"ok": True, "message": "System is already opened"})
    try:
        serial_connection = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        thread_running = True
        reader_thread = threading.Thread(target=serial_reader)
        reader_thread.daemon = True
        reader_thread.start()
        system_opened = True
        send_command("OPEN")
        return jsonify({"ok": True, "message": "OPEN: Arduino connected on " + SERIAL_PORT})
    except Exception as e:
        return jsonify({"ok": False, "message": "Open error: " + str(e)})

@app.route("/start", methods=["POST"])
def start():
    global monitoring, current_session
    if not system_opened:
        return jsonify({"ok": False, "message": "First press Open"})
    current_session += 1
    monitoring = True
    send_command("START")
    socketio.emit("new_session", {"session_id": current_session})
    return jsonify({"ok": True, "message": "START: monitoring session " + str(current_session)})

@app.route("/stop", methods=["POST"])
def stop():
    global monitoring
    monitoring = False
    send_command("STOP")
    return jsonify({"ok": True, "message": "STOP: monitoring stopped"})

@app.route("/close", methods=["POST"])
def close_system():
    global monitoring, system_opened, thread_running, serial_connection
    monitoring = False
    if system_opened:
        send_command("CLOSE")
    time.sleep(0.2)
    thread_running = False
    try:
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
    except:
        pass
    system_opened = False
    return jsonify({"ok": True, "message": "CLOSE: serial connection closed"})

@app.route("/parameters", methods=["POST"])
def set_parameters():
    data = request.get_json()
    try:
        parameters["sensitivity"] = float(data.get("sensitivity", parameters["sensitivity"]))
        parameters["brightness"] = int(data.get("brightness", parameters["brightness"]))
        parameters["mode"] = str(data.get("mode", parameters["mode"]))
        send_command("BRIGHTNESS:" + str(parameters["brightness"]))
        send_command("MODE:" + parameters["mode"])
        return jsonify({"ok": True, "message": "Parameters saved", "parameters": parameters})
    except Exception as e:
        return jsonify({"ok": False, "message": "Parameter error: " + str(e)})

@app.route("/sessions")
def sessions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT session_id, COUNT(*), MIN(timestamp), MAX(timestamp)
        FROM measurements GROUP BY session_id ORDER BY session_id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return jsonify([{"session_id": r[0], "count": r[1], "start": r[2], "end": r[3]} for r in rows])

@app.route("/session/<int:sid>")
def session_db(sid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp,sound,normalized_sound,freq,mode,brightness,on_state,sensitivity,web_mode
        FROM measurements WHERE session_id=? ORDER BY id ASC
    """, (sid,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return jsonify({"ok": False, "message": "Database session not found"})
    data = []
    for i, r in enumerate(rows):
        data.append({
            "x": i, "timestamp": r[0], "sound": r[1], "normalized_sound": r[2],
            "freq": r[3], "mode": r[4], "brightness": r[5], "on": r[6],
            "sensitivity": r[7], "web_mode": r[8]
        })
    return jsonify({"ok": True, "session_id": sid, "data": data})

@app.route("/csv_session/<int:sid>")
def session_csv(sid):
    if not os.path.exists(CSV_FILE):
        return jsonify({"ok": False, "message": "CSV file not found"})
    data = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["session_id"]) == sid:
                data.append({
                    "x": len(data),
                    "timestamp": row["timestamp"],
                    "sound": float(row["sound"]),
                    "normalized_sound": float(row["normalized_sound"]),
                    "freq": float(row["freq"]),
                    "mode": int(row["mode"]),
                    "brightness": int(row["brightness"]),
                    "on": int(row["on_state"]),
                    "sensitivity": float(row["sensitivity"]),
                    "web_mode": row["web_mode"]
                })
    if not data:
        return jsonify({"ok": False, "message": "CSV session not found"})
    return jsonify({"ok": True, "session_id": sid, "data": data})

if __name__ == "__main__":
    init_database()
    init_csv()
    socketio.run(app, host="0.0.0.0", port=5000)

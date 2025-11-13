from flask import Flask, request, jsonify, render_template
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# --- USE WRITABLE PATH FOR RAILWAY ---
DB_PATH = "/tmp/locations.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# --- CREATE TABLE ON STARTUP ---
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Locations (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID TEXT,
            Latitude REAL,
            Longitude REAL,
            Timestamp TEXT
        );
    """)
    conn.commit()
    conn.close()


# Run DB initialization when the module is imported
init_db()


@app.route('/add_location', methods=['POST'])
def add_location():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'no data'}), 400

    user_id = data.get('user_id', 'user1')
    lat = data.get('lat')
    lng = data.get('lng')
    timestamp = data.get('timestamp')

    try:
        ts_str = timestamp.replace('Z', '') if timestamp else datetime.now().isoformat()
    except:
        ts_str = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Locations (UserID, Latitude, Longitude, Timestamp)
        VALUES (?, ?, ?, ?)
    """, (user_id, lat, lng, ts_str))

    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/get_locations/<user_id>', methods=['GET'])
def get_locations(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Latitude, Longitude, Timestamp
        FROM Locations
        WHERE UserID = ?
        ORDER BY Timestamp
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {'lat': r['Latitude'], 'lng': r['Longitude'], 'timestamp': r['Timestamp']}
        for r in rows
    ])


@app.route('/map')
def map_view():
    return render_template('map.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

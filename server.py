from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DB_NAME = "locations.db"

# Create DB & table if not exists
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Locations (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID TEXT,
            Latitude REAL,
            Longitude REAL,
            Timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

@app.route('/add_location', methods=['POST'])
def add_location():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'no data'}), 400

    user_id = data.get('user_id', 'user1')
    lat = data.get('lat')
    lng = data.get('lng')
    timestamp = data.get('timestamp')

    # Convert timestamp
    try:
        clean_ts = timestamp.replace('Z', '')
        ts_obj = datetime.fromisoformat(clean_ts)
        ts_str = ts_obj.isoformat()
    except Exception:
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
        WHERE UserID=?
        ORDER BY Timestamp
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {'lat': r[0], 'lng': r[1], 'timestamp': r[2]}
        for r in rows
    ])

@app.route('/map')
def map_view():
    return render_template('map.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)

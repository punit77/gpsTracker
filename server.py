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

@app.route('/get_locations', methods=['GET'])
def get_locations():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    # optional filters
    start = request.args.get("start")
    end = request.args.get("end")
    after_ts = request.args.get("after_ts")
    after_id = request.args.get("after_id")

    # pagination / protection
    MAX_LIMIT = 5000
    default_limit = None  # keep None meaning "no explicit limit" (but client can request)
    limit = request.args.get("limit", default_limit)
    offset = request.args.get("offset")

    # Validate limit and offset if provided
    limit_param = None
    offset_param = None
    if limit is not None:
        try:
            limit_param = int(limit)
            if limit_param <= 0:
                return jsonify({'error': 'limit must be a positive integer'}), 400
            if limit_param > MAX_LIMIT:
                limit_param = MAX_LIMIT  # cap it
        except ValueError:
            return jsonify({'error': 'limit must be an integer'}), 400

    if offset is not None:
        try:
            offset_param = int(offset)
            if offset_param < 0:
                return jsonify({'error': 'offset must be >= 0'}), 400
        except ValueError:
            return jsonify({'error': 'offset must be an integer'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Build the base query and params
    query = """
        SELECT ID, Latitude, Longitude, Timestamp
        FROM Locations
        WHERE UserID = ?
    """
    params = [user_id]

    if start:
        query += " AND Timestamp >= ?"
        params.append(start)

    if end:
        query += " AND Timestamp <= ?"
        params.append(end)

    if after_ts:
        query += " AND Timestamp > ?"
        params.append(after_ts)

    if after_id:
        # after_id should be numeric; simple validation
        try:
            _ = int(after_id)
            query += " AND ID > ?"
            params.append(after_id)
        except ValueError:
            conn.close()
            return jsonify({'error': 'after_id must be an integer'}), 400

    # Always order by ID ascending (oldest -> newest)
    query += " ORDER BY ID ASC"

    # Apply LIMIT / OFFSET if provided (parameters appended after existing params)
    if limit_param is not None:
        query += " LIMIT ?"
        params.append(limit_param)
        if offset_param is not None:
            query += " OFFSET ?"
            params.append(offset_param)
    elif offset_param is not None:
        # offset without limit is ambiguous; reject to avoid accidental full scan
        conn.close()
        return jsonify({'error': 'offset requires limit to be set'}), 400

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except Exception as e:
        conn.close()
        return jsonify({'error': 'database error', 'details': str(e)}), 500

    conn.close()

    return jsonify([
        {
            'id': r['ID'],
            'lat': r['Latitude'],
            'lng': r['Longitude'],
            'timestamp': r['Timestamp']
        }
        for r in rows
    ])


@app.route('/map')
def map_view():
    return render_template('map.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


# --- CREATE TABLE ON STARTUP ---
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # LOCATIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            timestamp TIMESTAMP,
            api_source TEXT
        );
    """)

    # JOBSITES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobsites (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            customer_name TEXT,
            jobsite_name TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            api_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()

# Run DB initialization when the module is imported
try:
    init_db()
    print("DB initialized")
except Exception as e:
    print("DB init failed:", e)

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
        ts = datetime.fromisoformat(timestamp.replace('Z', '')) if timestamp else datetime.now()
    except:
        ts = datetime.now()

    conn = get_connection()
    cursor = conn.cursor()
    api_source = data.get('api_source', 'unknown')

    cursor.execute("""
        INSERT INTO locations (user_id, latitude, longitude, timestamp, api_source)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, lat, lng, ts, api_source))

    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/get_locations', methods=['GET'])
def get_locations():
    user_id = request.args.get("user_id")
    limit = request.args.get("limit", type=int)
    after_id = request.args.get("after_id", type=int)

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, latitude, longitude, timestamp, api_source
        FROM locations
        WHERE user_id = %s
    """
    params = [user_id]

    if after_id:
        query += " AND id > %s"
        params.append(after_id)

    query += " ORDER BY id ASC"

    if limit:
        query += " LIMIT %s"
        params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    # FIX FIELD NAMES HERE
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "lat": r["latitude"],   # FIX
            "lng": r["longitude"],  # FIX
            "timestamp": str(r["timestamp"]),
            "api_source": r["api_source"]
        })

    return jsonify(result)

@app.route('/add_jobsite', methods=['POST'])
def add_jobsite():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'no data'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobsites (
            user_id, customer_name, jobsite_name,
            latitude, longitude, api_source
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        data['user_id'],
        data['customer'],
        data['jobsite'],
        data['lat'],
        data['lng'],
        data['api_source']
    ))

    conn.commit()
    conn.close()

    return jsonify({'status': 'jobsite added'})

@app.route('/get_jobsites', methods=['GET'])
def get_jobsites():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM jobsites
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify(rows)

@app.route('/delete_jobsite', methods=['POST'])
def delete_jobsite():
    data = request.get_json()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM jobsites
        WHERE user_id = %s
        AND customer_name = %s
        AND jobsite_name = %s
        AND latitude = %s
        AND longitude = %s
    """, (
        data['user_id'],
        data['customer'],
        data['jobsite'],
        data['lat'],
        data['lng']
    ))

    conn.commit()
    conn.close()

    return jsonify({'status': 'deleted'})

@app.route('/map')
def map_view():
    return render_template('map.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

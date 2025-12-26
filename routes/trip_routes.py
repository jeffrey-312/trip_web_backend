from flask import Blueprint, request, jsonify
from database import get_db_connection
import mysql.connector

trip_bp = Blueprint('trip_bp', __name__)

# --- 1. 取得使用者所有行程 ---
@trip_bp.route('/<int:user_id>', methods=['GET'])
def get_all_trips(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # DB 欄位確認：使用 Users_id 與 start_datetime
        sql = "SELECT * FROM trips WHERE Users_id = %s ORDER BY start_datetime DESC"
        cursor.execute(sql, (user_id,))
        trips = cursor.fetchall()

        return jsonify({
            "code": "200",
            "data": trips
        }), 200

    except Exception as e:
        return jsonify({
            "code": "2001",
            "message": "取得失敗",
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

# --- 2. 建立新行程 ---
@trip_bp.route('/<int:user_id>', methods=['POST'])
def create_trip(user_id):
    data = request.json
    
    title = data.get('title')
    # 前端傳來 date 與 time，我們需合併成 DB 的 DATETIME 格式
    start_dt = f"{data.get('start_date')} {data.get('start_time')}"
    end_dt = f"{data.get('end_date')} {data.get('end_time')}"
    note = data.get('note', '')
    total_budget = data.get('total_budget', 0)

    if not title or not data.get('start_date') or not data.get('end_date'):
        return jsonify({"code": "2002", "message": "行程建立失敗，必填欄位缺失"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # DB 欄位確認：Users_id, start_datetime, end_datetime
        sql = """
            INSERT INTO trips (Users_id, title, start_datetime, end_datetime, note, total_budget)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (user_id, title, start_dt, end_dt, note, total_budget))
        conn.commit()

        return jsonify({
            "code": "200",
            "message": "行程建立成功"
        }), 200

    except Exception as e:
        return jsonify({
            "code": "2002",
            "message": "行程建立失敗",
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

# --- 3. 編輯行程 ---
@trip_bp.route('/<int:trip_id>', methods=['PUT'])
def update_trip(trip_id):
    data = request.json
    
    start_dt = f"{data.get('start_date')} {data.get('start_time')}"
    end_dt = f"{data.get('end_date')} {data.get('end_time')}"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        sql = """
            UPDATE trips 
            SET title=%s, start_datetime=%s, end_datetime=%s, note=%s, total_budget=%s
            WHERE id=%s
        """
        cursor.execute(sql, (
            data.get('title'),
            start_dt,
            end_dt,
            data.get('note'),
            data.get('total_budget'),
            trip_id
        ))
        conn.commit()

        return jsonify({
            "code": "200",
            "message": "行程修改成功"
        }), 200

    except Exception as e:
        return jsonify({
            "code": "2003",
            "message": "行程修改失敗",
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

# --- 4. 刪除行程 ---
@trip_bp.route('/<int:trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        sql = "DELETE FROM trips WHERE id = %s"
        cursor.execute(sql, (trip_id,))
        conn.commit()

        return jsonify({
            "code": "200",
            "message": "行程刪除成功"
        }), 200

    except Exception as e:
        return jsonify({
            "code": "2004",
            "message": "行程刪除失敗",
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()
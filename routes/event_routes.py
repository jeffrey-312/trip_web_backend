from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import timedelta

event_bp = Blueprint('event_bp', __name__)

def format_timedelta(data):
    if isinstance(data, list):
        for item in data:
            for key, value in item.items():
                if isinstance(value, timedelta):
                    item[key] = str(value)
    return data

# --- 1. 新增活動與帳目 (金額僅存入 expenses) ---
@event_bp.route('/events/<int:trip_id>', methods=['POST'])
def add_event(trip_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # A. 插入活動 (移除 planned_cost 欄位)
        sql_event = """
            INSERT INTO events (Trips_id, day_no, title, start_time, end_time, place_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql_event, (
            trip_id, data.get('day_no', 1), data.get('title'), 
            data.get('start_time'), data.get('end_time'),
            data.get('place_name')
        ))
        
        new_event_id = cursor.lastrowid

        # B. 插入帳目 (金額唯一存儲處)
        sql_expense = """
            INSERT INTO expenses (Trips_id, Events_id, amount, category)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_expense, (trip_id, new_event_id, data.get('cost', 0), data.get('category', '其他')))

        conn.commit()
        return jsonify({"code": "200", "message": "活動與帳目已新增"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "2006", "message": "新增失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 2. 取得行程活動、類別統計與總額 (金額統一來自 expenses) ---
@event_bp.route('/trips/<int:trip_id>/events', methods=['GET'])
def get_trip_events(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # A. 查詢所有活動與來自 expenses 的金額
        sql_events = """
            SELECT 
                e.id, e.Trips_id, e.day_no, e.title, 
                e.start_time, e.end_time, e.place_name, 
                ex.category, ex.amount AS expense 
            FROM events e
            LEFT JOIN expenses ex ON e.id = ex.Events_id
            WHERE e.Trips_id = %s
            ORDER BY e.day_no ASC, e.start_time ASC
        """
        cursor.execute(sql_events, (trip_id,))
        events = cursor.fetchall()

        # B. 統計各類別花費
        sql_category_sum = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE Trips_id = %s
            GROUP BY category
        """
        cursor.execute(sql_category_sum, (trip_id,))
        category_summaries = cursor.fetchall()

        # C. 計算全行程總花費
        total_spent = sum(item['total_amount'] for item in category_summaries)

        return jsonify({
            "code": "200",
            "data": {
                "total_spent": total_spent,
                "category_summaries": category_summaries,
                "events": format_timedelta(events)
            }
        }), 200
    except Exception as e:
        return jsonify({"code": "2005", "message": "取得資料失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 3. 編輯活動 (僅更新 expenses 中的金額) ---
@event_bp.route('/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 更新活動資訊 (不再更新 planned_cost)
        sql_event = """
            UPDATE events 
            SET day_no=%s, title=%s, start_time=%s, end_time=%s, place_name=%s
            WHERE id=%s
        """
        cursor.execute(sql_event, (
            data.get('day_no'), data.get('title'), data.get('start_time'),
            data.get('end_time'), data.get('place_name'), event_id
        ))

        # 2. 更新帳目資訊 (唯一更新金額處)
        sql_expense = "UPDATE expenses SET amount=%s, category=%s WHERE Events_id=%s"
        cursor.execute(sql_expense, (data.get('cost'), data.get('category'), event_id))

        conn.commit()
        return jsonify({"code": "200", "message": "活動與帳目已更新"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "2007", "message": "修改失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 4. 刪除活動 (連動刪除帳目) ---
@event_bp.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM expenses WHERE Events_id = %s", (event_id,))
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        conn.commit()
        return jsonify({"code": "200", "message": "活動及其帳目已刪除"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "2008", "message": "刪除失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import timedelta # 引入 timedelta 進行轉型

event_bp = Blueprint('event_bp', __name__)

# 自定義轉換函式：將 timedelta 轉為字串 (如 "09:00:00")
def format_timedelta(data):
    if isinstance(data, list):
        for item in data:
            for key, value in item.items():
                if isinstance(value, timedelta):
                    item[key] = str(value)
    return data

        
# --- 1. 新增活動與帳目 (連動 Events_id) ---
@event_bp.route('/events/<int:trip_id>', methods=['POST'])
def add_event(trip_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # A. 插入活動
        sql_event = """
            INSERT INTO events (Trips_id, day_no, title, start_time, end_time, place_name, planned_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql_event, (
            trip_id, data.get('day_no', 1), data.get('title'), 
            data.get('start_time'), data.get('end_time'),
            data.get('place_name'), data.get('cost', 0)
        ))
        
        # 拿到剛產生的活動 ID
        new_event_id = cursor.lastrowid

        # B. 插入帳目，並填入 Events_id
        sql_expense = """
            INSERT INTO expenses (Trips_id, Events_id, amount, category)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_expense, (trip_id, new_event_id, data.get('cost', 0), data.get('category', '其他')))

        conn.commit()
        return jsonify({"code": "200", "message": "活動與帳目已成功連結並新增"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "2006", "message": "新增失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 2. 查看：取得該行程所有活動 (GET) ---
@event_bp.route('/trips/<int:trip_id>/events', methods=['GET'])
def get_trip_events(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM events WHERE Trips_id = %s ORDER BY day_no ASC, start_time ASC"
        cursor.execute(sql, (trip_id,))
        events = cursor.fetchall()

        # 解決 timedelta 無法 JSON 序列化的問題
        formatted_events = format_timedelta(events)

        return jsonify({"code": "200", "data": formatted_events}), 200
    except Exception as e:
        return jsonify({"code": "2005", "message": "取得活動失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 3. 編輯活動 (PUT) ---
@event_bp.route('/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 更新 events 資料表中的活動細節
        # 注意：我們使用 planned_cost 作為金額欄位
        sql_event = """
            UPDATE events 
            SET day_no=%s, title=%s, start_time=%s, end_time=%s, place_name=%s, planned_cost=%s
            WHERE id=%s
        """
        cursor.execute(sql_event, (
            data.get('day_no'), 
            data.get('title'), 
            data.get('start_time'),
            data.get('end_time'), 
            data.get('place_name'), 
            data.get('cost'), # 前端傳來的金額
            event_id
        ))

        # 2. 同步更新 expenses 資料表中的金額
        # 透過 Events_id 找到對應的那筆帳目並修改 amount
        sql_expense = """
            UPDATE expenses 
            SET amount=%s 
            WHERE Events_id=%s
        """
        cursor.execute(sql_expense, (
            data.get('cost'), 
            event_id
        ))

        conn.commit()
        return jsonify({"code": "200", "message": "活動與帳目金額已同步修改成功"}), 200

    except Exception as e:
        conn.rollback() # 出錯時回滾，確保兩邊資料一致
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
        # 如果您沒做 SQL 的 ON DELETE CASCADE，就必須手動寫兩行：
        # 1. 先刪帳目
        cursor.execute("DELETE FROM expenses WHERE Events_id = %s", (event_id,))
        # 2. 再刪活動
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))

        conn.commit()
        return jsonify({"code": "200", "message": "活動及其對應帳目已刪除"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "2008", "message": "刪除失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import timedelta
from datetime import datetime

# 建立 Blueprint
admin_bp = Blueprint('admin_bp', __name__)

def format_sql_result(data):
    """
    將資料庫回傳的特殊型別（如 timedelta）轉換為字串，避免 JSON 序列化失敗
    """
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, timedelta):
                        item[key] = str(value)
    return data

@admin_bp.route('/admin/raw-sql', methods=['POST'])
def execute_sql():
    data = request.json
    raw_query = data.get('query')
    
    if not raw_query:
        return jsonify({"code": "400", "message": "請輸入 SQL 語法"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(raw_query)
        query_upper = raw_query.strip().upper()
        
        # 情況 A：查詢類指令 (SELECT, SHOW, DESC, EXPLAIN)
        if any(query_upper.startswith(word) for word in ["SELECT", "SHOW", "DESC", "EXPLAIN"]):
            result = cursor.fetchall()
            
            # ★ 關鍵修復：將結果進行格式轉換，處理 timedelta 問題
            formatted_result = format_sql_result(result)
            
            return jsonify({
                "code": "200",
                "type": "query",
                "data": formatted_result,
                "message": "查詢執行成功"
            }), 200
            
        # 情況 B：修改類指令
        else:
            conn.commit()
            return jsonify({
                "code": "200",
                "type": "update",
                "message": f"指令執行成功，影響列數: {cursor.rowcount}",
                "data": []
            }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "code": "500", 
            "message": "SQL 執行失敗", 
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

# --- 登記今日上線 (由前端在登入或首頁載入時呼叫) ---
@admin_bp.route('/users/check-in', methods=['POST'])
def user_check_in():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"code": "400", "message": "缺少 user_id"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 更新該用戶的最後在線時間為「現在」
        sql = "UPDATE users SET last_seen = NOW() WHERE id = %s"
        cursor.execute(sql, (user_id,))
        conn.commit()
        return jsonify({"code": "200", "message": "登記成功"}), 200
    except Exception as e:
        return jsonify({"code": "500", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 取得今日上線總人數 ---
@admin_bp.route('/stats/today-online', methods=['GET'])
def get_today_online_count():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 統計今天 (00:00:00 之後) 有更新過時間的不重複人數
        sql = "SELECT COUNT(DISTINCT id) AS count FROM users WHERE last_seen >= CURDATE()"
        cursor.execute(sql)
        result = cursor.fetchone()
        return jsonify({
            "code": "200", 
            "today_count": result['count'],
            "date": str(datetime.now().date())
        }), 200
    except Exception as e:
        return jsonify({"code": "500", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
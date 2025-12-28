from flask import Blueprint, request, jsonify
from database import get_db_connection

# 建立 Blueprint
admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/admin/raw-sql', methods=['POST'])
def execute_sql():
    data = request.json
    raw_query = data.get('query')
    
    if not raw_query:
        return jsonify({"code": "400", "message": "請輸入 SQL 語法"}), 400
        
    conn = get_db_connection()
    # 使用 dictionary=True 確保前端能拿到鍵值對來產生表頭
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(raw_query)
        
        # 轉大寫判斷指令類型，以符合前端的 type 判斷邏輯
        query_upper = raw_query.strip().upper()
        
        # 情況 A：查詢類指令 (SELECT, SHOW, DESC, EXPLAIN)
        if any(query_upper.startswith(word) for word in ["SELECT", "SHOW", "DESC", "EXPLAIN"]):
            result = cursor.fetchall()
            return jsonify({
                "code": "200",
                "type": "query",  # ★ 這是前端對應 table 顯示的關鍵
                "data": result,
                "message": "查詢執行成功"
            }), 200
            
        # 情況 B：修改類指令 (INSERT, UPDATE, DELETE, ALTER, DROP)
        else:
            conn.commit()
            return jsonify({
                "code": "200",
                "type": "update", # ★ 這是前端顯示系統訊息的關鍵
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
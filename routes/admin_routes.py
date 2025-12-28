from flask import Blueprint, request, jsonify
from database import get_db_connection

# 建立獨立的 Blueprint
admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/admin/raw-sql', methods=['POST'])
def execute_raw_sql():
    """
    警告：此 API 允許執行任何 SQL 指令，請務必僅在開發測試時使用。
    """
    data = request.json
    # 從 Body 取得 SQL 語法
    raw_query = data.get('query')
    
    if not raw_query:
        return jsonify({"code": "400", "message": "請在 JSON 中提供 'query' 欄位"}), 400
        
    conn = get_db_connection()
    # dictionary=True 讓回傳結果以 dict 格式呈現
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 執行前端傳來的 SQL
        cursor.execute(raw_query)
        
        # 判斷指令類型：如果是 SELECT，則回傳資料
        query_upper = raw_query.strip().upper()
        if query_upper.startswith("SELECT") or query_upper.startswith("SHOW") or query_upper.startswith("DESC"):
            result = cursor.fetchall()
            message = "查詢成功"
        else:
            # 如果是 INSERT/UPDATE/DELETE，則提交變更
            conn.commit()
            result = {"affected_rows": cursor.rowcount}
            message = "指令執行成功並已提交變更"
            
        return jsonify({
            "code": "200", 
            "message": message,
            "data": result
        }), 200

    except Exception as e:
        # 發生錯誤時回滾，避免毀壞資料庫一致性
        conn.rollback()
        return jsonify({
            "code": "500", 
            "message": "SQL 執行出錯", 
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()
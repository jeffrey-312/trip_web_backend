from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime

place_bp = Blueprint('place_bp', __name__)

@place_bp.route('/places', methods=['GET'])
def get_all_places():
    # 取得 query string 參數
    q = (request.args.get('q') or '').strip()
    limit = request.args.get('limit', default=50, type=int)

    # limit 安全限制，避免惡意一次拉爆 DB
    if limit <= 0:
        limit = 10
    if limit > 200:
        limit = 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 若有關鍵字：用 LIKE 搜尋
        if q:
            sql = """
                SELECT id AS place_id, name
                FROM places
                WHERE name LIKE %s
                ORDER BY name ASC
                LIMIT %s
            """
            like_kw = f"%{q}%"
            cursor.execute(sql, (like_kw, limit))
        else:
            # 若沒帶關鍵字：回傳前 N 筆（你也可以改成直接回傳 []）
            sql = """
                SELECT id AS place_id, name
                FROM places
                ORDER BY id DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))

        places = cursor.fetchall()

        return jsonify({
            "code": "200",
            "data": places,
            "meta": {
                "q": q,
                "limit": limit,
                "count": len(places)
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": "3001",
            "message": "取得景點失敗",
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

# --- 2. 加入/取消最愛 (切換狀態) ---
@place_bp.route('/favorites', methods=['POST'])
def toggle_favorite():
    data = request.json
    user_id = data.get('user_id')
    place_id = data.get('place_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 檢查是否已收藏
        cursor.execute("SELECT * FROM favorites WHERE Users_id = %s AND Places_id = %s", (user_id, place_id))
        if cursor.fetchone():
            cursor.execute("DELETE FROM favorites WHERE Users_id = %s AND Places_id = %s", (user_id, place_id))
            message = "已從最愛移除"
        else:
            cursor.execute("INSERT INTO favorites (Users_id, Places_id) VALUES (%s, %s)", (user_id, place_id))
            message = "已加入最愛"
        conn.commit()
        return jsonify({"code": "200", "message": message}), 200
    except Exception as e:
        return jsonify({"code": "4001", "message": "操作失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
# --- 3. 看到我自己收藏的 Favorite 地點 ---
@place_bp.route('/users/<int:user_id>/favorites', methods=['GET'])
def get_my_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 透過 favorites 表 JOIN places
        sql = """
            SELECT p.id AS place_id, p.name 
            FROM favorites f
            JOIN places p ON f.Places_id = p.id
            WHERE f.Users_id = %s
        """
        cursor.execute(sql, (user_id,))
        fav_places = cursor.fetchall()
        return jsonify({"code": "200", "data": fav_places}), 200
    except Exception as e:
        return jsonify({"code": "3002", "message": "取得收藏清單失敗"}), 500
    finally:
        cursor.close()
        conn.close()


# --- 4. 點開地點看到我自己的評論 或 改寫評論 ---
@place_bp.route('/users/<int:user_id>/places/<int:place_id>/review', methods=['GET', 'POST'])
def handle_private_review(user_id, place_id):
    conn = get_db_connection()
    
    # --- GET: 讀取評論 ---
    if request.method == 'GET':
        cursor = conn.cursor(dictionary=True)
        try:
            # 對應 reviews 表欄位: score, comment
            sql = "SELECT score, comment FROM reviews WHERE Users_id = %s AND Places_id = %s"
            cursor.execute(sql, (user_id, place_id))
            review = cursor.fetchone()
            if not review:
                review = {"score": 0, "comment": ""}
            return jsonify({"code": "200", "data": review}), 200
        except Exception as e:
            return jsonify({"code": "3003", "message": "讀取評論失敗"}), 500
        finally:
            cursor.close()
            conn.close()

    # --- POST: 改寫(更新或新增) 評論 ---
    if request.method == 'POST':
        data = request.json
        score = data.get('score')
        comment = data.get('comment')
        cursor = conn.cursor()
        try:
            # 使用 INSERT ... ON DUPLICATE KEY UPDATE 確保每人每地只有一筆
            sql = """
                INSERT INTO reviews (Users_id, Places_id, score, comment)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE score=%s, comment=%s, created_at=CURRENT_TIMESTAMP
            """
            cursor.execute(sql, (user_id, place_id, score, comment, score, comment))
            conn.commit()
            return jsonify({"code": "200", "message": "個人評論已改寫成功"}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"code": "3004", "message": "改寫評論失敗", "error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
            
# --- 5. 使用者：刪除個人評論與評分 ---
@place_bp.route('/users/<int:user_id>/reviews/<int:place_id>', methods=['DELETE'])
def delete_user_review(user_id, place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "DELETE FROM reviews WHERE Users_id = %s AND Places_id = %s"
        cursor.execute(sql, (user_id, place_id))
        conn.commit()
        return jsonify({"code": "200", "message": "已清除您的個人評論與評分"}), 200
    except Exception as e:
        return jsonify({"code": "3005", "message": "清除失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 6. 管理員：新增公共景點到地點庫 ---
# Method: POST /api/admin/places
@place_bp.route('/admin/places', methods=['POST'])
def admin_add_place():
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({"code": "4003", "message": "景點名稱不能為空"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 檢查景點是否已存在
        cursor.execute("SELECT id FROM places WHERE name = %s", (name,))
        if cursor.fetchone():
            return jsonify({"code": "4004", "message": "此景點已存在於公共庫中"}), 400

        # 2. 插入新景點 (僅包含公共資訊，不含 score 與 comment)
        sql = "INSERT INTO places (name) VALUES (%s)"
        cursor.execute(sql, (name,))
        
        conn.commit()
        return jsonify({
            "code": "200",
            "message": f"成功新增公共景點: {name}",
            "place_id": cursor.lastrowid
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "code": "4005",
            "message": "系統錯誤，新增失敗",
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()
        
# --- 7. 管理員：從公共庫刪除景點 ---
@place_bp.route('/admin/places/<int:place_id>', methods=['DELETE'])
def admin_delete_place(place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 執行刪除，CASCADE 會自動處理關聯表
        sql = "DELETE FROM places WHERE id = %s"
        cursor.execute(sql, (place_id,))
        
        if cursor.rowcount == 0:
            return jsonify({"code": "4006", "message": "找不到該景點，刪除失敗"}), 404

        conn.commit()
        return jsonify({"code": "200", "message": "已將景點從公共庫徹底移除"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "4007", "message": "刪除失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
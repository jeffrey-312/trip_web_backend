from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime

place_bp = Blueprint('place_bp', __name__)

# --- 1. 取得景點 (支援關鍵字、國家、城市搜尋) ---
@place_bp.route('/places', methods=['GET'])
def get_all_places():
    # 取得搜尋參數
    q = (request.args.get('q') or '').strip()
    limit = request.args.get('limit', default=50, type=int)

    # 安全限制
    limit = max(1, min(limit, 200))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. 基礎 SQL 語法
        sql = "SELECT id AS place_id, name, country, city FROM places"
        params = []

        # 2. 動態判斷：如果使用者有輸入關鍵字 q
        if q:
            # 同時比對名稱、國家、城市三個欄位
            sql += " WHERE (name LIKE %s OR country LIKE %s OR city LIKE %s)"
            like_kw = f"%{q}%"
            params.extend([like_kw, like_kw, like_kw]) # 傳入三次關鍵字對應三個 LIKE

        # 3. 排序與分頁
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        cursor.execute(sql, tuple(params))
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
        return jsonify({"code": "3001", "message": "取得景點失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
# @place_bp.route('/places', methods=['GET'])
# def get_all_places():
#     # 取得搜尋參數
#     q = (request.args.get('q') or '').strip()           # 名稱關鍵字
#     country = (request.args.get('country') or '').strip() # 國家篩選
#     city = (request.args.get('city') or '').strip()       # 城市篩選
#     limit = request.args.get('limit', default=50, type=int)

#     # 安全限制
#     limit = max(1, min(limit, 200))

#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         # 動態構建 SQL 語法
#         sql = "SELECT id AS place_id, name, country, city FROM places WHERE 1=1"
#         params = []

#         if q:
#             sql += " AND name LIKE %s"
#             params.append(f"%{q}%")
#         if country:
#             sql += " AND country = %s"
#             params.append(country)
#         if city:
#             sql += " AND city = %s"
#             params.append(city)

#         sql += " ORDER BY id DESC LIMIT %s"
#         params.append(limit)

#         cursor.execute(sql, tuple(params))
#         places = cursor.fetchall()

#         return jsonify({
#             "code": "200",
#             "data": places,
#             "meta": {
#                 "q": q,
#                 "country": country,
#                 "city": city,
#                 "limit": limit,
#                 "count": len(places)
#             }
#         }), 200
#     except Exception as e:
#         return jsonify({"code": "3001", "message": "取得景點失敗", "error": str(e)}), 500
#     finally:
#         cursor.close()
#         conn.close()

# --- 2. 加入/取消最愛 ---
@place_bp.route('/favorites', methods=['POST'])
def toggle_favorite():
    data = request.json
    user_id = data.get('user_id')
    place_id = data.get('place_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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

# --- 3. 取得個人收藏清單 (回傳包含國家城市) ---
@place_bp.route('/users/<int:user_id>/favorites', methods=['GET'])
def get_my_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT p.id AS place_id, p.name, p.country, p.city
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

# --- 4. 讀取/改寫個人評論與全站平均分 ---
@place_bp.route('/users/<int:user_id>/places/<int:place_id>/review', methods=['GET', 'POST'])
def handle_private_review(user_id, place_id):
    conn = get_db_connection()
    
    if request.method == 'GET':
        cursor = conn.cursor(dictionary=True)
        try:
            sql_user = "SELECT score, comment FROM reviews WHERE Users_id = %s AND Places_id = %s"
            cursor.execute(sql_user, (user_id, place_id))
            user_review = cursor.fetchone() or {"score": 0, "comment": ""}

            sql_avg = """
                SELECT 
                    ROUND(AVG(score), 1) AS average_score, 
                    COUNT(id) AS total_reviews 
                FROM reviews 
                WHERE Places_id = %s
            """
            cursor.execute(sql_avg, (place_id,))
            global_stat = cursor.fetchone()

            return jsonify({
                "code": "200", 
                "data": {
                    "my_review": user_review,
                    "global_stat": {
                        "average_score": float(global_stat['average_score']) if global_stat['average_score'] else 0.0,
                        "total_reviews": global_stat['total_reviews']
                    }
                }
            }), 200
        except Exception as e:
            return jsonify({"code": "3003", "message": "讀取評論失敗", "error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    if request.method == 'POST':
        data = request.json
        score = data.get('score')
        comment = data.get('comment')
        cursor = conn.cursor()
        try:
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

# --- 5. 刪除個人評論 ---
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

# --- 6. 管理員：新增公共景點 (含國家、城市) ---
@place_bp.route('/admin/places', methods=['POST'])
def admin_add_place():
    data = request.json
    name = data.get('name')
    country = data.get('country')
    city = data.get('city')
    
    if not name:
        return jsonify({"code": "4003", "message": "景點名稱不能為空"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM places WHERE name = %s", (name,))
        if cursor.fetchone():
            return jsonify({"code": "4004", "message": "此景點已存在於公共庫中"}), 400

        # 修改插入語法以支援 country 與 city
        sql = "INSERT INTO places (name, country, city) VALUES (%s, %s, %s)"
        cursor.execute(sql, (name, country, city))
        
        conn.commit()
        return jsonify({
            "code": "200",
            "message": f"成功新增公共景點: {name}",
            "place_id": cursor.lastrowid
        }), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"code": "4005", "message": "系統錯誤，新增失敗", "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- 7. 管理員：從公共庫刪除景點 ---
@place_bp.route('/admin/places/<int:place_id>', methods=['DELETE'])
def admin_delete_place(place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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
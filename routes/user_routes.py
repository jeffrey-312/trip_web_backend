from flask import Blueprint, request, jsonify
from database import get_db_connection
import mysql.connector

user_bp = Blueprint('user_bp', __name__)

# --- 註冊 API ---
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password') # 新增密碼欄位

    if not name or not email or not password:
        return jsonify({"message": "請提供姓名、Email 與密碼"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # SQL 加入 password 欄位
        sql = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(sql, (name, email, password))
        conn.commit()
        return jsonify({"message": "註冊成功！", "user_id": cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        return jsonify({"message": "註冊失敗，Email 可能重複", "error": str(err)}), 400
    finally:
        cursor.close()
        conn.close()
        
# --- 登入 API ---
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"code": "1001", "message": "請提供 Email 與密碼"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 使用子查詢統計行程與收藏
        sql = """
            SELECT 
                u.id, u.name, u.email,
                (SELECT COUNT(*) FROM trips WHERE users_id = u.id) AS total_trips,
                (SELECT COUNT(*) FROM Favorites WHERE Users_id = u.id) AS total_favorites
            FROM users u
            WHERE u.email = %s AND u.password = %s
        """
        cursor.execute(sql, (email, password))
        user = cursor.fetchone()

        if user:
            # 回傳格式必須是乾淨的 JSON，不能有 [cite] 標記
            return jsonify({
                "code": "200",
                "message": "登入成功",
                "data": {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "total_trips": str(user['total_trips']),
                    "total_favorites": str(user['total_favorites'])
                }
            }), 200
        else:
            return jsonify({"code": "1001", "message": "帳號或密碼不正確"}), 401
    except Exception as e:
        return jsonify({"code": "500", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        

# --- 編輯使用者資訊 API ---
@user_bp.route('/User', methods=['POST'])
def update_user():
    data = request.json
    user_id = data.get('id')
    new_name = data.get('name')
    # 根據您的需求文件，編輯時通常也會帶 email，若這次只傳 name 則可從 data 取得
    new_email = data.get('email') 

    # 驗證必要欄位 id 與 name 是否存在
    if not user_id or not new_name:
        return jsonify({
            "code": "1003",
            "message": "資料修改失敗"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 執行 SQL 更新指令
        # 如果前端只傳 id 和 name，則只更新 name
        if new_email:
            sql = "UPDATE users SET name = %s, email = %s WHERE id = %s"
            cursor.execute(sql, (new_name, new_email, user_id))
        else:
            sql = "UPDATE users SET name = %s WHERE id = %s"
            cursor.execute(sql, (new_name, user_id))
            
        conn.commit()

        # 檢查是否有資料列受影響 (rowcount > 0 代表有修改成功)
        if cursor.rowcount > 0:
            return jsonify({
                "code": "200",
                "name": new_name,
                "message": "資料修改成功"
            }), 200
        else:
            # 若 id 不存在或資料與原本一模一樣導致沒更新
            return jsonify({
                "code": "1003",
                "message": "資料修改失敗"
            }), 404

    except Exception as e:
        return jsonify({
            "code": "1003",
            "message": "資料修改失敗"
        }), 500
    finally:
        cursor.close()
        conn.close()

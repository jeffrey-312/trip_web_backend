from flask import Flask
from flask_cors import CORS
from routes.user_routes import user_bp
from routes.trip_routes import trip_bp
from routes.event_routes import event_bp
from routes.place_routes import place_bp

app = Flask(__name__)
app.json.ensure_ascii = False 
CORS(app) # 加上這行，允許前端 React 連進來

# 註冊藍圖，並加上前綴詞
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(trip_bp, url_prefix='/api/trips')
app.register_blueprint(event_bp, url_prefix='/api')
app.register_blueprint(place_bp, url_prefix='/api')

@app.route('/')
def index():
    return "旅遊規劃系統後端運作中"

# 增加一個測試資料庫連線的路由
@app.route('/test-db')
def test_db():
    from database import get_db_connection
    try:
        conn = get_db_connection()
        conn.close()
        return "資料庫連線成功！"
    except Exception as e:
        return f"資料庫連線失敗：{str(e)}"

if __name__ == '__main__':
    # host='0.0.0.0' 讓 Flask 聽取所有網路介面的請求
    # port=5000 是預設埠號
    app.run(debug=True, host='0.0.0.0', port=5000)
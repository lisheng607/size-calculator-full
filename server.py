"""
身材尺码计算器 - 后端服务器
优化Railway部署版本 - 修复数据库路径问题
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import tempfile
from datetime import datetime

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 数据库路径 - 使用临时目录
DB_PATH = os.path.join(tempfile.gettempdir(), 'size_records.db')
print(f"📁 数据库路径: {DB_PATH}")

# 数据库初始化
def init_database():
    """初始化SQLite数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS size_records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                gender      TEXT    NOT NULL,
                height      REAL    NOT NULL,
                weight      REAL    NOT NULL,
                bust        REAL    NOT NULL,
                waist       REAL    NOT NULL,
                hips        REAL    NOT NULL,
                top_size    TEXT    NOT NULL,
                bottom_size TEXT    NOT NULL,
                bmi         REAL    NOT NULL,
                created_at  TEXT    NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

# 尺码计算函数
def calculate_size(gender, bust, waist):
    """根据性别和三围计算尺码"""
    if gender == 'female':
        if   bust < 80:  top = 'XS'
        elif bust < 85:  top = 'S'
        elif bust < 90:  top = 'M'
        elif bust < 95:  top = 'L'
        elif bust < 100: top = 'XL'
        else:            top = 'XXL'
        
        if   waist < 60: bottom = 'XS'
        elif waist < 65: bottom = 'S'
        elif waist < 70: bottom = 'M'
        elif waist < 75: bottom = 'L'
        elif waist < 80: bottom = 'XL'
        else:            bottom = 'XXL'
    else:
        if   bust < 88:  top = 'S'
        elif bust < 92:  top = 'M'
        elif bust < 96:  top = 'L'
        elif bust < 100: top = 'XL'
        else:            top = 'XXL'
        
        if   waist < 72: bottom = 'S'
        elif waist < 76: bottom = 'M'
        elif waist < 80: bottom = 'L'
        elif waist < 85: bottom = 'XL'
        else:            bottom = 'XXL'
    
    return top, bottom

# API路由
@app.route('/')
def home():
    """根路径 - 返回欢迎信息"""
    return jsonify({
        'message': '身材尺码计算器API',
        'version': '1.0',
        'status': 'running',
        'database': DB_PATH,
        'endpoints': {
            '/api/health': '健康检查',
            '/api/calculate': '计算尺码（POST）',
            '/api/records': '获取历史记录'
        }
    })

@app.route('/api/health')
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': '服务器运行正常',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'database': 'connected'
    })

@app.route('/api/calculate', methods=['POST', 'OPTIONS'])
def calculate():
    """计算尺码并保存"""
    # 处理OPTIONS预检请求
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # 获取并打印请求数据（用于调试）
        data = request.json
        print(f"📥 收到计算请求: {data}")
        
        # 提取数据
        gender = data.get('gender', 'female')
        height = float(data.get('height', 0))
        weight = float(data.get('weight', 0))
        bust   = float(data.get('bust', 0))
        waist  = float(data.get('waist', 0))
        hips   = float(data.get('hips', 0))
        
        # 数据验证
        if not all([height, weight, bust, waist, hips]):
            print("❌ 数据不完整")
            return jsonify({'success': False, 'error': '数据不完整'}), 400
        
        if height < 100 or height > 250:
            print(f"❌ 身高数据不合理: {height}")
            return jsonify({'success': False, 'error': '身高数据不合理'}), 400
        
        # 计算尺码和BMI
        top_size, bottom_size = calculate_size(gender, bust, waist)
        bmi = round(weight / ((height / 100) ** 2), 1)
        
        print(f"✅ 计算结果: 上装={top_size}, 下装={bottom_size}, BMI={bmi}")
        
        # 保存到数据库
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO size_records
                (gender, height, weight, bust, waist, hips, top_size, bottom_size, bmi, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                gender, height, weight, bust, waist, hips,
                top_size, bottom_size, bmi,
                datetime.utcnow().isoformat() + 'Z'  # 使用UTC时间的ISO格式
            ))
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ 数据已保存，ID: {record_id}")
            
            return jsonify({
                'success': True,
                'top_size': top_size,
                'bottom_size': bottom_size,
                'bmi': bmi,
                'record_id': record_id,
                'message': '计算完成并已保存'
            })
            
        except sqlite3.Error as db_error:
            print(f"❌ 数据库错误: {db_error}")
            return jsonify({
                'success': False,
                'error': f'数据库错误: {str(db_error)}'
            }), 500
        
    except ValueError as ve:
        print(f"❌ 数据格式错误: {ve}")
        return jsonify({
            'success': False,
            'error': f'数据格式错误: {str(ve)}'
        }), 400
        
    except Exception as e:
        print(f"❌ 服务器错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/records')
def get_records():
    """获取历史记录"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, gender, height, weight, bust, waist, hips,
                   top_size, bottom_size, bmi, created_at
            FROM size_records
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append({
                'id': row[0],
                'gender': row[1],
                'height': row[2],
                'weight': row[3],
                'bust': row[4],
                'waist': row[5],
                'hips': row[6],
                'top_size': row[7],
                'bottom_size': row[8],
                'bmi': row[9],
                'created_at': row[10]
            })
        
        return jsonify({
            'success': True,
            'count': len(records),
            'records': records
        })
        
    except Exception as e:
        print(f"❌ 获取记录错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 启动时初始化数据库
init_database()

# 启动服务器
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 启动服务器在端口 {port}...")
    print(f"📁 数据库位置: {DB_PATH}")
    
    app.run(debug=False, host='0.0.0.0', port=port)

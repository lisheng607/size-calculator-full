# ============================================================
# 后端服务器代码（Python）
# 作用：接收前端发来的数据，处理逻辑，返回结果，存储数据库
# ============================================================

# 导入需要的工具库（就像准备工具箱）
from flask import Flask, request, jsonify  # Flask：创建Web服务器的工具
from flask_cors import CORS                # CORS：允许前端访问后端
import sqlite3                             # SQLite：轻量级数据库
import json
from datetime import datetime

# ---- 创建Flask应用 ----
# 就像开一家餐厅，Flask是这家餐厅的框架
app = Flask(__name__)
CORS(app)  # 允许任何网页来访问这个服务器

# ---- 数据库初始化 ----
# 第一次运行时，自动创建数据库和表
def init_database():
    """
    初始化数据库
    如果数据库文件不存在，会自动创建
    如果表不存在，会自动创建
    """
    # connect() 就像打开一个Excel文件
    conn = sqlite3.connect('size_records.db')
    cursor = conn.cursor()  # cursor 就像一支笔，用来执行SQL命令

    # 创建"身材记录"表
    # 这就是数据库语言SQL，意思是：
    # 如果"身材记录"表不存在，就创建一个
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

    # 保存更改并关闭（就像保存并关闭Excel）
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")


# ============================================================
# 尺码计算逻辑（和前端的逻辑一样，但在服务器端执行）
# 为什么前后端都要有？
# - 前端：快速响应，不需要等待网络
# - 后端：可信任的计算，防止用户修改前端代码
# ============================================================
def calculate_size(gender, bust, waist):
    """
    根据性别和三围计算推荐尺码
    返回：(上装尺码, 下装尺码)
    """
    if gender == 'female':
        # 女装上装
        if   bust < 80:  top = 'XS'
        elif bust < 85:  top = 'S'
        elif bust < 90:  top = 'M'
        elif bust < 95:  top = 'L'
        elif bust < 100: top = 'XL'
        else:            top = 'XXL'

        # 女装下装
        if   waist < 60: bottom = 'XS'
        elif waist < 65: bottom = 'S'
        elif waist < 70: bottom = 'M'
        elif waist < 75: bottom = 'L'
        elif waist < 80: bottom = 'XL'
        else:            bottom = 'XXL'

    else:  # male
        # 男装上装
        if   bust < 88:  top = 'S'
        elif bust < 92:  top = 'M'
        elif bust < 96:  top = 'L'
        elif bust < 100: top = 'XL'
        else:            top = 'XXL'

        # 男装下装
        if   waist < 72: bottom = 'S'
        elif waist < 76: bottom = 'M'
        elif waist < 80: bottom = 'L'
        elif waist < 85: bottom = 'XL'
        else:            bottom = 'XXL'

    return top, bottom


# ============================================================
# API 接口：计算尺码并保存数据
# 当前端发送请求到 /api/calculate 时，这个函数会被调用
# ============================================================
@app.route('/api/calculate', methods=['POST'])
def calculate():
    """
    接收身材数据，计算尺码，保存到数据库
    
    前端发来的数据格式（JSON）：
    {
        "gender": "female",
        "height": 165,
        "weight": 55,
        "bust": 85,
        "waist": 65,
        "hips": 90
    }
    
    返回格式：
    {
        "success": true,
        "top_size": "M",
        "bottom_size": "M",
        "bmi": 20.2,
        "record_id": 1
    }
    """
    try:
        # 读取前端发来的数据
        data = request.json

        # 提取各个字段
        gender = data.get('gender', 'female')
        height = float(data.get('height', 0))
        weight = float(data.get('weight', 0))
        bust   = float(data.get('bust', 0))
        waist  = float(data.get('waist', 0))
        hips   = float(data.get('hips', 0))

        # 验证数据（防止无效数据）
        if not all([height, weight, bust, waist, hips]):
            return jsonify({'success': False, 'error': '数据不完整'}), 400

        if height < 100 or height > 250:
            return jsonify({'success': False, 'error': '身高数据不合理'}), 400

        # 计算尺码
        top_size, bottom_size = calculate_size(gender, bust, waist)

        # 计算BMI
        bmi = round(weight / ((height / 100) ** 2), 1)

        # 保存到数据库
        conn = sqlite3.connect('size_records.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO size_records
            (gender, height, weight, bust, waist, hips, top_size, bottom_size, bmi, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            gender, height, weight, bust, waist, hips,
            top_size, bottom_size, bmi,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

        record_id = cursor.lastrowid  # 获取刚插入记录的ID
        conn.commit()
        conn.close()

        # 返回结果给前端
        return jsonify({
            'success':    True,
            'top_size':   top_size,
            'bottom_size':bottom_size,
            'bmi':        bmi,
            'record_id':  record_id,
            'message':    '计算完成并已保存'
        })

    except Exception as e:
        # 如果出错，返回错误信息
        print(f"❌ 计算出错: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API 接口：查询历史记录
# 当前端访问 /api/records 时，返回所有历史记录
# ============================================================
@app.route('/api/records', methods=['GET'])
def get_records():
    """
    返回最近的历史记录
    """
    try:
        conn = sqlite3.connect('size_records.db')
        cursor = conn.cursor()

        # 查询最近10条记录，按时间倒序
        cursor.execute('''
            SELECT id, gender, height, weight, bust, waist, hips,
                   top_size, bottom_size, bmi, created_at
            FROM size_records
            ORDER BY created_at DESC
            LIMIT 10
        ''')

        rows = cursor.fetchall()
        conn.close()

        # 把数据库结果转换成JSON格式
        records = []
        for row in rows:
            records.append({
                'id':          row[0],
                'gender':      row[1],
                'height':      row[2],
                'weight':      row[3],
                'bust':        row[4],
                'waist':       row[5],
                'hips':        row[6],
                'top_size':    row[7],
                'bottom_size': row[8],
                'bmi':         row[9],
                'created_at':  row[10]
            })

        return jsonify({'success': True, 'records': records})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API 接口：健康检查
# 用来测试服务器是否正常运行
# ============================================================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': '服务器运行正常',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


# ---- 启动服务器 ----
if __name__ == '__main__':
    print("🚀 启动身材尺码计算器后端服务器...")
    init_database()
    # Railway会自动设置PORT环境变量
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, port=port, host='0.0.0.0')

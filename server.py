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

@app.route('/admin')
def admin_page():
    """管理页面 - 查看数据库记录"""
    return '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>数据管理</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:40px 20px}.container{max-width:1200px;margin:0 auto}h1{text-align:center;color:#fff;margin-bottom:30px;font-size:2.5em}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:30px}.stat-card{background:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,.2)}.stat-label{color:#666;font-size:14px}.stat-value{color:#667eea;font-size:32px;font-weight:700}.btn{padding:12px 24px;background:#667eea;color:#fff;border:none;border-radius:8px;cursor:pointer;margin:20px auto;display:block}.table-container{background:#fff;border-radius:12px;padding:20px;box-shadow:0 4px 15px rgba(0,0,0,.2);overflow-x:auto}table{width:100%;border-collapse:collapse}th{background:#f8f9fa;padding:12px;font-size:14px;border-bottom:2px solid #e0e0e0}td{padding:10px;font-size:13px;border-bottom:1px solid #f0f0f0}tr:hover{background:#f8f9fa}.badge{padding:4px 12px;border-radius:12px;font-size:13px;font-weight:600}.badge-female{background:#ffe4e6;color:#e91e63}.badge-male{background:#e3f2fd;color:#2196f3}.size-badge{background:#667eea;color:#fff;padding:4px 10px;border-radius:6px}.loading{text-align:center;color:#fff;padding:40px}.spinner{border:4px solid rgba(255,255,255,.3);border-top:4px solid #fff;border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:20px auto}@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style></head><body><div class="container"><h1>📊 数据管理后台</h1><div class="stats"><div class="stat-card"><div class="stat-label">总记录</div><div class="stat-value" id="total">-</div></div><div class="stat-card"><div class="stat-label">女性</div><div class="stat-value" id="female">-</div></div><div class="stat-card"><div class="stat-label">男性</div><div class="stat-value" id="male">-</div></div><div class="stat-card"><div class="stat-label">平均BMI</div><div class="stat-value" id="bmi">-</div></div></div><button class="btn" onclick="load()">🔄 刷新</button><div id="loading" class="loading"><div class="spinner"></div><p>加载中...</p></div><div id="table" class="table-container" style="display:none"><table><thead><tr><th>ID</th><th>性别</th><th>身高</th><th>体重</th><th>胸围</th><th>腰围</th><th>臀围</th><th>上装</th><th>下装</th><th>BMI</th><th>时间</th></tr></thead><tbody id="tbody"></tbody></table></div></div><script>async function load(){document.getElementById("loading").style.display="block",document.getElementById("table").style.display="none";try{const e=await fetch("/api/records"),t=await e.json();if(document.getElementById("loading").style.display="none",!t.success)throw new Error(t.error);const a=t.records||[];if(0===a.length)return void alert("暂无数据");document.getElementById("table").style.display="block";const n=a.length,d=a.filter(e=>"female"===e.gender).length,l=a.filter(e=>"male"===e.gender).length,o=n>0?(a.reduce((e,t)=>e+parseFloat(t.bmi),0)/n).toFixed(1):"-";document.getElementById("total").textContent=n,document.getElementById("female").textContent=d,document.getElementById("male").textContent=l,document.getElementById("bmi").textContent=o,document.getElementById("tbody").innerHTML=a.map(e=>{const t="female"===e.gender?"badge-female":"badge-male",a="female"===e.gender?"女":"男";return`<tr><td>${e.id}</td><td><span class="badge ${t}">${a}</span></td><td>${e.height}</td><td>${e.weight}</td><td>${e.bust}</td><td>${e.waist}</td><td>${e.hips}</td><td><span class="size-badge">${e.top_size}</span></td><td><span class="size-badge">${e.bottom_size}</span></td><td>${e.bmi}</td><td>${new Date(e.created_at).toLocaleString("zh-CN",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"})}</td></tr>`}).join("")}catch(e){document.getElementById("loading").innerHTML="❌ "+e.message}}load(),setInterval(load,3e4)</script></body></html>'''

# 启动时初始化数据库
init_database()

# 启动服务器
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 启动服务器在端口 {port}...")
    print(f"📁 数据库位置: {DB_PATH}")
    print(f"🔗 管理后台: /admin")
    
    app.run(debug=False, host='0.0.0.0', port=port)

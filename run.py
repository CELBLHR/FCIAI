import os

from app import create_app, db

# 创建应用实例
app = create_app('development') # 使用开发配置

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)

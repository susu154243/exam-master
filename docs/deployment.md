# 部署指南

## 环境要求

| 项目 | 要求 |
|------|------|
| 系统 | Ubuntu 22.04+ |
| Python | 3.10+ |
| 内存 | ≥ 512MB |
| 磁盘 | ≥ 100MB（不含数据库） |

## 开发环境

```bash
cd /keyin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
# 访问 http://localhost:32220
```

## 生产部署（systemd + Gunicorn + Nginx）

### 1. 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/keyin.service > /dev/null << 'EOF'
[Unit]
Description=KeyIn (刻印) Flask Quiz System
After=network.target

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/keyin
Environment="PATH=/keyin/venv/bin"
ExecStart=/keyin/venv/bin/gunicorn \
    --bind 127.0.0.1:32220 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app

[Install]
WantedBy=multi-user.target
EOF
```

### 2. 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable keyin
sudo systemctl start keyin
sudo systemctl status keyin
```

### 3. Nginx 反向代理

```nginx
server {
    listen 80;
    server_name keyin;  # 替换为实际域名或 IP
    
    location / {
        proxy_pass http://127.0.0.1:32220;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /keyin/static;
        expires 30d;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 4. 环境变量（可选）

```bash
# 设置 SECRET_KEY（生产环境必须）
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 永久生效：写入 systemd
sudo systemctl edit keyin
# 添加：
# [Service]
# Environment=SECRET_KEY=your-secret-key-here
```

## 数据库备份

```bash
# 手动备份
cp /keyin/database.db /keyin/database.db.bak.$(date +%Y%m%d_%H%M%S)

# 定时备份（crontab）
0 2 * * * cp /keyin/database.db /backup/keyin-$(date +\%Y\%m\%d).db
```

## 日志查看

```bash
# 应用日志
sudo journalctl -u keyin -f

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 故障排查

| 问题 | 排查命令 |
|------|----------|
| 服务未启动 | `sudo systemctl status keyin` |
| 端口被占用 | `sudo lsof -i :32220` |
| 权限错误 | `ls -la /keyin/database.db` |
| 数据库锁定 | `fuser /keyin/database.db` |
| Python 依赖缺失 | `cd /keyin && venv/bin/pip install -r requirements.txt` |

## 版本升级

```bash
cd /keyin

# 1. 备份数据库
cp database.db database.db.bak.$(date +%Y%m%d_%H%M%S)

# 2. 拉取代码
git pull

# 3. 检查依赖
venv/bin/pip install -r requirements.txt

# 4. 重启服务
sudo systemctl restart keyin

# 5. 验证
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:32220/login
```

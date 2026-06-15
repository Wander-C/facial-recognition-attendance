# 部署指南

## 前置要求

- 华为云ECS服务器（推荐2核4G）
- Ubuntu 22.04系统
- Python 3.10+
- MySQL 8.0
- Redis 7.0
- Nginx

## 1. 服务器环境配置

### 1.1 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2 安装Python 3.10

```bash
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y build-essential libssl-dev libffi-dev
```

### 1.3 安装MySQL

```bash
sudo apt install -y mysql-server

# 启动MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# 初始化MySQL
sudo mysql_secure_installation
```

### 1.4 安装Redis

```bash
sudo apt install -y redis-server

# 启动Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 1.5 安装Nginx

```bash
sudo apt install -y nginx

# 启动Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

## 2. 应用部署

### 2.1 克隆项目

```bash
cd /opt
sudo git clone https://github.com/Wander-C/facial-recognition-attendance.git
cd facial-recognition-attendance
sudo chown -R $USER:$USER .
```

### 2.2 创建虚拟环境

```bash
python3.10 -m venv venv
source venv/bin/activate
```

### 2.3 安装依赖

```bash
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
```

### 2.4 配置环境变量

```bash
cp .env .env
vim .env  # 编辑配置
```

关键配置项：
- `DATABASE_URL`: MySQL连接字符串
- `REDIS_HOST`: Redis地址
- `HWC_AK`, `HWC_SK`, `HWC_PROJECT_ID`: 华为云凭证
- `JWT_SECRET_KEY`: 改为强密钥

### 2.5 初始化数据库

```bash
cd backend
python init_db.py
```

### 2.6 创建日志和上传目录

```bash
mkdir -p logs
mkdir -p /var/uploads/attendance
sudo chown -R www-data:www-data /var/uploads/attendance
```

## 3. 服务管理

### 3.1 使用Supervisor管理FastAPI

安装Supervisor：
```bash
sudo apt install -y supervisor
```

创建配置文件 `/etc/supervisor/conf.d/attendance.conf`：

```ini
[program:attendance]
directory=/opt/facial-recognition-attendance/backend
command=/opt/facial-recognition-attendance/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/facial-recognition-attendance/logs/uvicorn.log
environment=PATH="/opt/facial-recognition-attendance/venv/bin"
```

启动服务：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start attendance
sudo supervisorctl status
```

### 3.2 配置Nginx反向代理

编辑 `/etc/nginx/sites-available/default`：

```nginx
upstream uvicorn {
    server 127.0.0.1:8000;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;
    client_max_body_size 10M;

    location / {
        proxy_pass http://uvicorn;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }

    location /uploads/ {
        alias /var/uploads/attendance/;
        expires 7d;
    }
}
```

测试并重启Nginx：
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 4. HTTPS配置（可选）

使用Let's Encrypt获取免费证书：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 5. 监控和日志

### 查看应用日志

```bash
tail -f logs/app.log
```

### 查看Supervisor日志

```bash
tail -f logs/uvicorn.log
sudo supervisorctl tail -f attendance
```

### 查看Nginx日志

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 6. 性能优化

### 6.1 MySQL优化

编辑 `/etc/mysql/mysql.conf.d/mysqld.cnf`：

```ini
max_connections=500
max_allowed_packet=64M
innodb_buffer_pool_size=1G
```

### 6.2 Redis优化

编辑 `/etc/redis/redis.conf`：

```ini
maxmemory 512mb
maxmemory-policy allkeys-lru
```

## 7. 备份和恢复

### 数据库备份

```bash
mysqldump -u root -p attendance_system > backup.sql
```

### 数据库恢复

```bash
mysql -u root -p attendance_system < backup.sql
```

## 8. 常见问题

### Q: 华为云FRS SDK导入失败
A: 确保已安装所有依赖，运行 `pip install -r backend/requirements.txt`

### Q: 数据库连接超时
A: 检查MySQL是否运行，检查DATABASE_URL配置

### Q: 图片上传失败
A: 确保上传目录存在且有写入权限，检查MAX_UPLOAD_SIZE设置

### Q: Token过期
A: 用户需要重新登录获取新Token，或调整JWT_EXPIRATION_HOURS

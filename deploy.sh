#!/bin/bash
# 英语口语评分工具 · 一键部署脚本
# 适用：阿里云/腾讯云轻量服务器（Ubuntu/Debian/CentOS）
# 使用方法：curl -fsSL https://raw.githubusercontent.com/rudabao/english-speaking-app/main/deploy.sh | bash

set -e

echo "========================================="
echo "英语口语评分工具 · 一键部署"
echo "========================================="

# 检测系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "无法检测系统，仅支持 Ubuntu/Debian/CentOS"
    exit 1
fi

echo "检测到系统: $OS $VERSION"

# 安装基础依赖
install_deps() {
    echo "正在安装基础依赖..."
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        apt-get update
        apt-get install -y python3 python3-pip git nginx
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        yum install -y python3 python3-pip git nginx
    else
        echo "不支持的系统: $OS"
        exit 1
    fi
}

install_deps

# 克隆代码
APP_DIR="/opt/english-speaking-app"
if [ -d "$APP_DIR" ]; then
    echo "目录已存在，正在更新代码..."
    cd "$APP_DIR"
    git pull
else
    echo "正在克隆代码..."
    git clone https://github.com/rudabao/english-speaking-app.git "$APP_DIR"
    cd "$APP_DIR"
fi

# 安装 Python 依赖
echo "正在创建虚拟环境并安装依赖..."
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

# 创建环境变量文件
echo "正在配置环境变量..."
cat > "$APP_DIR/.env" << 'EOF'
IFLYTEK_APP_ID=你的讯飞APPID
IFLYTEK_ISE_API_KEY=你的ISE_APIKey
IFLYTEK_ISE_API_SECRET=你的ISE_APISecret
IFLYTEK_RAASR_API_SECRET=你的转写SecretKey
DEEPSEEK_API_KEY=你的DeepSeek_API_Key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
AUDIO_RETENTION_DAYS=30
CLEANUP_INTERVAL_HOURS=24
ENABLE_CLEANUP=true
HOST=0.0.0.0
PORT=5017
EOF

echo "注意：环境变量已使用占位符，请登录服务器后手动编辑 $APP_DIR/.env 文件填入真实 API key"
echo "编辑命令: nano $APP_DIR/.env"
echo "编辑后重启服务: systemctl restart english-speaking-app"

# 创建 uploads 目录
mkdir -p "$APP_DIR/uploads"

# 配置 Nginx
echo "正在配置 Nginx..."
cat > /etc/nginx/sites-available/english-speaking-app << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5017;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/audio/ {
        alias /opt/english-speaking-app/uploads/;
    }
}
EOF

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    ln -sf /etc/nginx/sites-available/english-speaking-app /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl restart nginx
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    rm -f /etc/nginx/conf.d/default.conf
    cp /etc/nginx/sites-available/english-speaking-app /etc/nginx/conf.d/
    nginx -t
    systemctl restart nginx
fi

# 配置 systemd 服务
echo "正在配置 systemd 服务..."
cat > /etc/systemd/system/english-speaking-app.service << 'EOF'
[Unit]
Description=English Speaking Scoring App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/english-speaking-app
Environment="PATH=/opt/english-speaking-app/venv/bin"
ExecStart=/opt/english-speaking-app/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable english-speaking-app
systemctl restart english-speaking-app

# 配置防火墙（如果有）
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
fi
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --reload
fi

# 获取服务器 IP
SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)

echo "========================================="
echo "部署完成！"
echo "========================================="
echo "访问地址: http://$SERVER_IP"
echo ""
echo "下一步：配置 API Key"
echo "执行命令: cd /opt/english-speaking-app && bash config.sh"
echo "按提示输入你的讯飞和 DeepSeek API Key"
echo ""
echo "如果访问不了，请检查："
echo "1. 云服务器安全组是否开放 80 端口"
echo "2. Nginx 是否正常运行: systemctl status nginx"
echo "3. 应用是否正常运行: systemctl status english-speaking-app"
echo ""
echo "查看日志: journalctl -u english-speaking-app -f"
echo "========================================="

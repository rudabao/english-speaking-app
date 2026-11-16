#!/bin/bash
# 配置 API key 交互式脚本
# 用法：cd /opt/english-speaking-app && bash config.sh

echo "========================================="
echo "英语口语评分工具 · API Key 配置"
echo "========================================="
echo ""
echo "请依次输入以下信息（直接回车跳过）："
echo ""

# 讯飞 APPID
read -p "讯飞 APPID: " app_id
# 讯飞 ISE APIKey
read -p "讯飞 ISE APIKey: " ise_api_key
# 讯飞 ISE APISecret
read -p "讯飞 ISE APISecret: " ise_api_secret
# 讯飞转写 SecretKey
read -p "讯飞转写 SecretKey: " raasr_secret
# DeepSeek API Key
read -p "DeepSeek API Key: " deepseek_key

# 写入 .env 文件
APP_DIR="/opt/english-speaking-app"
cat > "$APP_DIR/.env" << EOF
IFLYTEK_APP_ID=${app_id}
IFLYTEK_ISE_API_KEY=${ise_api_key}
IFLYTEK_ISE_API_SECRET=${ise_api_secret}
IFLYTEK_RAASR_API_SECRET=${raasr_secret}
DEEPSEEK_API_KEY=${deepseek_key}
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
AUDIO_RETENTION_DAYS=30
CLEANUP_INTERVAL_HOURS=24
ENABLE_CLEANUP=true
HOST=0.0.0.0
PORT=5017
EOF

echo ""
echo "配置已保存到 $APP_DIR/.env"
echo "正在重启服务..."
systemctl restart english-speaking-app
echo "完成！"
echo ""
echo "访问地址: http://$(curl -s ifconfig.me || curl -s icanhazip.com)"

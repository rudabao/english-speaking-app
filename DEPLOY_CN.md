# 国内云服务器部署指南（阿里云/腾讯云）

适用于中国大陆用户，部署到阿里云或腾讯云轻量服务器。

---

## 一、购买服务器（如果还没有）

推荐配置：
- **阿里云轻量应用服务器**：https://www.aliyun.com/product/swas
- **腾讯云轻量应用服务器**：https://cloud.tencent.com/product/lighthouse

**推荐套餐**：
- 套餐：2 核 2G + 40GB SSD（约 30-100 元/月）
- 系统：Ubuntu 20.04 或 22.04
- 流量包：建议买包含流量套餐，或按量付费（学生使用量不大）

---

## 二、一键部署脚本（推荐）

### 1. 购买服务器后，拿到服务器信息：
- 公网 IP（例如：123.45.67.89）
- 密码（或 SSH 密钥）

### 2. 登录服务器
**Windows**：下载 PuTTY，输入 IP 和密码登录
**Mac/Linux**：打开终端，输入：
```bash
ssh root@你的服务器IP
# 例如：ssh root@123.45.67.89
# 输入密码（输入时不会显示）
```

### 3. 执行一键部署脚本
登录成功后，复制粘贴以下命令，回车：
```bash
curl -fsSL https://raw.githubusercontent.com/rudabao/english-speaking-app/main/deploy.sh | bash
```

脚本会自动完成：
- 安装 Python、Git、Nginx
- 克隆代码
- 安装依赖
- 配置环境变量（API key 已内置）
- 配置 Nginx 反向代理
- 配置 systemd 服务（开机自启）
- 开放防火墙端口

### 4. 等待部署完成
脚本会显示：
```
=========================================
部署完成！
=========================================
访问地址: http://123.45.67.89
=========================================
```

### 5. 在浏览器打开地址
把脚本显示的地址（例如 `http://123.45.67.89`）发给学生即可。

---

## 三、注意事项

### 1. 云服务器安全组开放 80 端口
- 阿里云：控制台 → 轻量应用服务器 → 防火墙 → 添加规则：端口 80，协议 TCP，来源 0.0.0.0/0
- 腾讯云：控制台 → 轻量应用服务器 → 防火墙 → 添加规则：端口 80，来源 0.0.0.0/0

### 2. 域名（可选）
- 如果有域名，可以在域名解析中添加 A 记录，指向服务器 IP
- 配置后可以通过域名访问（例如 `english.yourdomain.com`）

### 3. 数据备份
- 数据库：`/opt/english-speaking-app/speaking.db`
- 录音：`/opt/english-speaking-app/uploads/`
- 定期用 FTP 或 SCP 下载备份

### 4. 升级代码
如果有新版本，登录服务器执行：
```bash
cd /opt/english-speaking-app
git pull
systemctl restart english-speaking-app
```

---

## 四、故障排查

### 访问不了
1. 检查安全组是否开放 80 端口
2. 检查 Nginx 是否运行：`systemctl status nginx`
3. 检查应用是否运行：`systemctl status english-speaking-app`
4. 查看日志：`journalctl -u english-speaking-app -f`

### 服务重启失败
```bash
cd /opt/english-speaking-app
source venv/bin/activate
python app.py
# 看报错信息
```

---

## 五、费用说明

- 服务器：30-100 元/月（取决于配置）
- 流量：包含在套餐内或按量付费（学生使用不多，每月几块钱）
- API 调用：讯飞 ISE 每天 500 次免费，DeepSeek 计费很低（几块钱够一个班用很久）

**预计总成本**：约 50-150 元/月

# PythonAnywhere 部署指南

本指南说明如何将英语口语评分工具部署到 PythonAnywhere，学生通过互联网访问。

---

## 一、准备工作

1. **PythonAnywhere 账号**
   - 注册账号：https://www.pythonanywhere.com
   - 新建一个 Web 应用（Beginner 账号免费，但功能有限；推荐 Beginner 套餐 5 刀/月）

2. **GitHub 仓库**
   - 在 GitHub 创建新仓库（例如 `english-speaking-app`）
   - 本地代码推送到 GitHub：
     ```bash
     cd english-speaking-app
     git init
     git add .
     git commit -m "Initial commit"
     git remote add origin https://github.com/你的用户名/english-speaking-app.git
     git push -u origin main
     ```

---

## 二、PythonAnywhere 配置

### 1. 拉取代码

- 登录 PythonAnywhere → Files → Open a bash console
- 运行：
  ```bash
  git clone https://github.com/你的用户名/english-speaking-app.git
  cd english-speaking-app
  ```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境变量

- 在 Web 标签页 → 环境变量（Environment variables）添加以下变量：
  ```
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
  ```

### 4. 配置 Web 应用

- 在 Web 标签页 → Code：
  - Working directory: `/home/你的用户名/english-speaking-app`
  - Virtualenv: `/home/你的用户名/english-speaking-app/venv`
  - Python version: Python 3.10 或更新
- WSGI 配置文件内容：
  ```python
  import sys
  sys.path.insert(0, '/home/你的用户名/english-speaking-app')
  from app import app as application
  ```

### 5. 静态文件配置

- 在 Web 标签页 → Static files：
  - URL: `/static`
  - Directory: `/home/你的用户名/english-speaking-app/uploads`
  - **注意**：录音文件通过 `/api/audio/<filename>` 路由访问，不需要单独配置静态文件映射

### 6. 重启 Web 应用

- 点击 "Reload" 按钮

---

## 三、访问地址

部署成功后，PythonAnywhere 会提供一个类似 `https://你的用户名.pythonanywhere.com` 的地址。
把这个地址发给学生即可访问。

---

## 四、存储说明

- **数据库**：SQLite 文件在 `speaking.db`，免费版存储有限，定期备份（Files 标签页可下载）
- **录音文件**：默认保留 30 天，自动清理。可通过环境变量 `AUDIO_RETENTION_DAYS` 调整
- **免费版限制**：Beginner 免费版磁盘空间 517MB，录音较多会占满。建议升级 Beginner 套餐（5 刀/月，1GB 磁盘）

---

## 五、常见问题

**Q：访问报 500 错误？**
- 检查 Log 标签页的错误日志
- 确认环境变量配置正确

**Q：录音文件存满空间？**
- 减小 `AUDIO_RETENTION_DAYS`（例如改为 7）
- 或升级套餐获得更多磁盘空间

**Q：学生访问慢？**
- PythonAnywhere 免费版处于 "tarpitted" 状态时访问会慢
- 升级到付费套餐可解决

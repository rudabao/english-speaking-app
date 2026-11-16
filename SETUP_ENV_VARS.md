# PythonAnywhere 环境变量配置 · 超详细步骤

## 前提：你已经完成前面的步骤

- 已经在 PythonAnywhere 注册账号
- 已经通过 bash 拉取代码（git clone）
- 已经创建虚拟环境并安装依赖

---

## 配置环境变量详细步骤

### 第 1 步：进入 Web 配置页面

1. 登录 PythonAnywhere
2. 顶部导航栏点击 **"Web"** 标签

### 第 2 步：找到环境变量区域

在 Web 页面往下拉，你会看到几个板块：
- Code
- Virtualenv
- **Environment variables** ← 这个就是我们要配置的
- Static files
- ...

### 第 3 步：添加环境变量

在 **Environment variables** 区域，点击 **"Add new variable"** 按钮。

### 第 4 步：逐个添加以下变量

每个环境变量需要填两个字段：
- **Key**：变量名（我左边列出的英文）
- **Value**：变量值（我右边列出的值）

**按顺序添加（每次填完点 "Save"）：**

| Key | Value |
|---|---|
| `IFLYTEK_APP_ID` | `fab5268d` |
| `IFLYTEK_ISE_API_KEY` | `96b0636b7bd75b8d3b7790bfa63e0d22` |
| `IFLYTEK_ISE_API_SECRET` | `MTU2MDNhYzJkMmU1NzJhOWE2ODFmZTQ0` |
| `IFLYTEK_RAASR_API_SECRET` | `2c2e55b0375def0ca4157dc9cc51dd54` |
| `DEEPSEEK_API_KEY` | `sk-8fb1feef70c843f99bcc691daded2fd4` |
| `DEEPSEEK_MODEL` | `deepseek-chat` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `AUDIO_RETENTION_DAYS` | `30` |
| `CLEANUP_INTERVAL_HOURS` | `24` |
| `ENABLE_CLEANUP` | `true` |
| `HOST` | `0.0.0.0` |
| `PORT` | `5017` |

### 第 5 步：检查是否添加成功

添加完后，Environment variables 区域应该列出你刚才添加的所有变量。

---

## 后续步骤（简要）

### 配置 Web 应用

在同一个 Web 页面：

1. **Code 部分**：
   - Working directory: `/home/你的用户名/english-speaking-app`
   - Virtualenv: `/home/你的用户名/english-speaking-app/venv`
   - Python version: 选最新的 Python 3.x

2. **WSGI 配置文件**：
   - 点击 "WSGI configuration file" 链接
   - 删除原有内容，粘贴以下代码：
     ```python
     import sys
     sys.path.insert(0, '/home/你的用户名/english-speaking-app')
     from app import app as application
     ```
   - 点 "Save"

3. **重启应用**：
   - 回到 Web 页面
   - 点击页面顶部的绿色 **"Reload"** 按钮

---

## 访问地址

重启成功后，Web 页面顶部会显示你的网站地址，类似：
`https://rudabao.pythonanywhere.com`

把这个地址发给学生就能用了。

---

## 如果卡住了

如果遇到问题，把页面截图发给我，我帮你判断。

# 英语口语评分

网页端英语口语评分小工具，两个模式：

- **跟读评分**：学生照着参考文本朗读，讯飞语音评测（ISE）客观评分
- **自由表达**：没有参考文本，讯飞语音转写（raasr）识别内容 → 讯飞星火大模型主观评分 + 中文评语

5 个评分维度各 2 分，满分 10 分：发音准确度、语音语调、表达流利度、表达完整度、节奏把控。

## 运行

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py   # 或双击 start-mac.command
```

浏览器打开 http://127.0.0.1:5017

## 配置（iflytek_config.json）

```json
{
  "app_id": "fab5268d",
  "ise":    { "api_key": "...", "api_secret": "..." },   // 语音评测 ISE（跟读模式）
  "raasr":  { "api_secret": "..." },                     // 录音文件转写（自由表达模式）
  "deepseek": { "api_key": "sk-...", "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com" },   // 主观评分（优先）
  "spark":  { "app_id": "", "api_key": "", "api_secret": "", "domain": "generalv3.5" }
}
```

- `ise`：讯飞开放平台 →「语音评测」服务页的 APIKey / APISecret
- `raasr`：语音转写服务的 SecretKey（app_id 共用）
- `deepseek`：DeepSeek API Key（platform.deepseek.com），OpenAI 兼容接口，优先使用
- `spark`：讯飞星火认知大模型备选（xinghuo.xfyun.cn），deepseek 未配置时才用

缺哪项配置，页面顶部就会显示对应模式的警告；提交时也会返回明确错误。

## 使用流程

1. 选模式：跟读评分（填参考文本）或 自由表达（可填主题提示）。
2. 填学生姓名，点「开始朗读」，说完点「停止录音」。
3. 自由表达模式会先显示 AI 转写文本和中文评语，再看 5 维分数。
4. 历史记录可回放录音、看每个学生平均分。

## 文件说明

- `app.py` — Flask 后端：ISE 评测 / raasr 转写 / 星火评分 / SQLite 记录
- `templates/index.html` — 前端页面（浏览器录音 → PCM → WAV → 上传）
- `iflytek_config.json` — 讯飞凭证（勿提交到公开仓库）
- `uploads/` — 录音文件
- `speaking.db` — 评分记录数据库

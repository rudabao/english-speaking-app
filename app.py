from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os
import time
import hmac
import hashlib
import base64
import json
import xml.etree.ElementTree as ET
import requests
import io
import qrcode
import threading
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from email.utils import formatdate

# 加载 .env 文件（如果存在）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 配置：优先从环境变量读取，其次本地文件
def get_config(key, default=''):
    return os.environ.get(key, default)

def load_config():
    # 本地配置文件用于开发，生产环境用环境变量
    cfg_path = os.path.join(BASE_DIR, 'iflytek_config.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # 从环境变量读取（PythonAnywhere 部署用）
    return {
        'app_id': get_config('IFLYTEK_APP_ID', ''),
        'ise': {
            'api_key': get_config('IFLYTEK_ISE_API_KEY', ''),
            'api_secret': get_config('IFLYTEK_ISE_API_SECRET', ''),
        },
        'raasr': {
            'api_secret': get_config('IFLYTEK_RAASR_API_SECRET', ''),
        },
        'deepseek': {
            'api_key': get_config('DEEPSEEK_API_KEY', ''),
            'model': get_config('DEEPSEEK_MODEL', 'deepseek-chat'),
            'base_url': get_config('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        },
        'spark': {
            'app_id': get_config('IFLYTEK_SPARK_APP_ID', ''),
            'api_key': get_config('IFLYTEK_SPARK_API_KEY', ''),
            'api_secret': get_config('IFLYTEK_SPARK_API_SECRET', ''),
            'domain': get_config('IFLYTEK_SPARK_DOMAIN', 'generalv3.5'),
        },
    }

def ise_enabled():
    cfg = load_config()
    ise = cfg.get('ise', {})
    return bool(ise.get('api_key') and ise.get('api_secret'))

def raasr_enabled():
    cfg = load_config()
    raasr = cfg.get('raasr', {})
    secret = raasr.get('api_secret') or cfg.get('raasr_api_secret', '')
    return bool(cfg.get('app_id') and secret)

def spark_enabled():
    cfg = load_config()
    spark = cfg.get('spark', {})
    return bool(spark.get('app_id') and spark.get('api_key') and spark.get('api_secret'))

def deepseek_enabled():
    cfg = load_config()
    ds = cfg.get('deepseek', {})
    return bool(ds.get('api_key'))

def llm_enabled():
    return spark_enabled() or deepseek_enabled()

def free_mode_ready():
    return raasr_enabled() and llm_enabled()

# ---------- 讯飞语音评测（ISE，流式 WebSocket，跟读客观评分） ----------
def iflytek_assess(audio_wav_bytes, reference_text, timeout=90):
    cfg = load_config()
    ise = cfg.get('ise', {})
    app_id = cfg.get('app_id', '')
    api_key = ise.get('api_key', '')
    api_secret = ise.get('api_secret', '')
    if not all([app_id, api_key, api_secret]):
        raise ValueError('跟读评测未配置（需要环境变量 iflytek_config.json 中 ise.api_key / ise.api_secret）')

    import websocket
    host = 'ise-api.xfyun.cn'
    path = '/v2/open-ise'
    date = formatdate(usegmt=True)

    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

    ws_url = (
        f"wss://{host}{path}?authorization={quote(authorization)}"
        f"&host={host}&date={quote(date)}"
    )

    ws = websocket.create_connection(ws_url, timeout=timeout)
    try:
        business = {
            "sub": "ise",
            "ent": "en_vip",
            "category": "read_chapter",
            "cmd": "ssb",
            "text": "﻿" + reference_text,
            "tte": "utf-8",
            "ttp_skip": True,
            "aue": "raw",
            "auf": "audio/L16;rate=16000",
            "rst": "entirety",
            "ise_unite": "1",
            "extra_ability": "multi_dimension"
        }
        ws.send(json.dumps({
            "common": {"app_id": app_id},
            "business": business,
            "data": {"status": 0}
        }))

        pcm_data = audio_wav_bytes[44:] if audio_wav_bytes[:4] == b'RIFF' else audio_wav_bytes
        frame_size = 1280
        chunks = [pcm_data[i:i + frame_size] for i in range(0, len(pcm_data), frame_size)]
        if not chunks:
            chunks = [b'']
        for i, chunk in enumerate(chunks):
            aus = 1 if i == 0 else (4 if i == len(chunks) - 1 else 2)
            data_status = 2 if i == len(chunks) - 1 else 1
            ws.send(json.dumps({
                "business": {"cmd": "auw", "aus": aus},
                "data": {
                    "status": data_status,
                    "data": base64.b64encode(chunk).decode('utf-8')
                }
            }))
            if i < len(chunks) - 1:
                time.sleep(0.04)

        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = ws.recv()
            msg = json.loads(raw)
            if msg.get('code') != 0:
                raise ValueError(f"讯飞评测错误 code={msg.get('code')}: {msg.get('message')}")
            data = msg.get('data') or {}
            payload = data.get('data')
            status = data.get('status')
            if payload and status == 2:
                xml_text = base64.b64decode(payload).decode('utf-8', errors='replace')
                return parse_ise_xml(xml_text)
        raise ValueError('讯飞评测超时')
    finally:
        try:
            ws.close()
        except Exception:
            pass

def parse_ise_xml(xml_text):
    root = ET.fromstring(xml_text)
    for elem in root.iter():
        if 'total_score' in elem.attrib:
            def f(name):
                try:
                    return float(elem.attrib.get(name, 0) or 0)
                except (TypeError, ValueError):
                    return 0.0
            return {
                'total': f('total_score'),
                'accuracy': f('accuracy_score'),
                'fluency': f('fluency_score'),
                'integrity': f('integrity_score'),
                'standard': f('standard_score'),
            }
    raise ValueError('评测结果中未找到评分')

def ise_to_score_result(ise):
    standard = ise['standard'] if ise['standard'] else ise['accuracy']
    dims = {
        "pronunciation": min(2.0, ise['accuracy'] / 50),
        "intonation": min(2.0, standard / 50),
        "fluency": min(2.0, ise['fluency'] / 50),
        "completeness": min(2.0, ise['integrity'] / 50),
        "rhythm": min(2.0, ise['fluency'] / 50),
    }
    result = {k: round(v, 1) for k, v in dims.items()}
    result["total"] = round(sum(dims.values()), 1)
    return result

# ---------- 讯飞录音文件转写（raasr，自由表达模式用） ----------
def generate_signa(app_id, api_secret):
    ts = str(int(time.time()))
    base_string = app_id + ts
    md5_hash = hashlib.md5(base_string.encode('utf-8')).hexdigest()
    signature = hmac.new(
        api_secret.encode('utf-8'),
        md5_hash.encode('utf-8'),
        hashlib.sha1
    ).digest()
    signa = base64.b64encode(signature).decode('utf-8')
    return ts, signa

def extract_transcript_text(order_result):
    texts = []
    for lattice in order_result.get('lattice', []):
        json_1best = lattice.get('json_1best')
        if isinstance(json_1best, str):
            try:
                json_1best = json.loads(json_1best)
            except json.JSONDecodeError:
                continue
        for rt in json_1best.get('st', {}).get('rt', []):
            for ws in rt.get('ws', []):
                for cw in ws.get('cw', []):
                    w = cw.get('w', '')
                    wp = cw.get('wp', '')
                    if w and wp != 'g':
                        texts.append(w)
    return ' '.join(texts)

def iflytek_transcribe(audio_bytes, filename='audio.wav', language='en', timeout=180):
    cfg = load_config()
    app_id = cfg.get('app_id', '')
    raasr = cfg.get('raasr', {})
    api_secret = raasr.get('api_secret') or cfg.get('raasr_api_secret', '')
    if not app_id or not api_secret:
        raise ValueError('语音转写未配置（需要 iflytek_config.json 中 raasr.api_secret）')

    ts, signa = generate_signa(app_id, api_secret)
    params = {
        'appId': app_id, 'ts': ts, 'signa': signa,
        'fileName': filename, 'fileSize': str(len(audio_bytes)),
        'duration': '0', 'language': language,
    }
    upload_url = 'https://raasr.xfyun.cn/v2/api/upload?' + urlencode(params)
    resp = requests.post(upload_url, data=audio_bytes,
                         headers={'Content-Type': 'application/octet-stream'}, timeout=60)
    result = resp.json()
    if result.get('code') != '000000':
        raise ValueError(f"讯飞上传失败: {result.get('descInfo', result)}")
    order_id = result['content']['orderId']

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        ts, signa = generate_signa(app_id, api_secret)
        params = {'appId': app_id, 'ts': ts, 'signa': signa,
                  'orderId': order_id, 'resultType': 'transfer'}
        result_url = 'https://raasr.xfyun.cn/v2/api/getResult?' + urlencode(params)
        resp = requests.get(result_url, timeout=30)
        result = resp.json()
        if result.get('code') != '000000':
            continue
        content = result.get('content', {})
        order_info = content.get('orderInfo', {})
        status = order_info.get('status')
        if status == 4:
            order_result = content.get('orderResult', '{}')
            if isinstance(order_result, str):
                order_result = json.loads(order_result)
            return extract_transcript_text(order_result)
        elif status == -1:
            raise ValueError(f"讯飞转写失败, failType={order_info.get('failType')}")
    raise ValueError('讯飞转写超时')

# ---------- 讯飞星火大模型（自由表达主观评分） ----------
def spark_jwt(api_key, api_secret):
    header = {"alg": "HS256", "sign_type": "JWT"}
    payload = {
        "api_key": api_key,
        "exp": int(time.time()) + 86400,
        "timestamp": int(time.time()),
    }
    def b64(obj):
        return base64.b64encode(json.dumps(obj, separators=(',', ':')).encode()).decode().rstrip('=')
    signing_input = f"{b64(header)}.{b64(payload)}"
    signature = hmac.new(api_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{base64.b64encode(signature).decode().rstrip('=')}"

def spark_chat(prompt, timeout=60):
    cfg = load_config()
    spark = cfg.get('spark', {})
    app_id = spark.get('app_id', '')
    api_key = spark.get('api_key', '')
    api_secret = spark.get('api_secret', '')
    domain = spark.get('domain', 'generalv3.5')
    if not all([app_id, api_key, api_secret]):
        raise ValueError('AI 主观评分未配置（需要 iflytek_config.json 中 spark.app_id / api_key / api_secret，星火认知大模型控制台获取）')

    url = 'https://spark-api.xf-yun.com/v1/chat/completions'
    headers = {
        'Authorization': 'Bearer ' + spark_jwt(api_key, api_secret),
        'Content-Type': 'application/json',
    }
    body = {
        "header": {"app_id": app_id},
        "parameter": {"chat": {"domain": domain, "temperature": 0.3, "max_tokens": 1024}},
        "payload": {"message": {"text": [{"role": "user", "content": prompt}]}}
    }
    resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    data = resp.json()
    if data.get('code') != 0:
        raise ValueError(f"星火接口错误 code={data.get('code')}: {data.get('message', '')}")
    return data['payload']['choices']['text'][0]['content']

# ---------- DeepSeek（OpenAI 兼容接口） ----------
def deepseek_chat(prompt, timeout=60):
    ds = load_config().get('deepseek', {})
    api_key = ds.get('api_key', '')
    model = ds.get('model', 'deepseek-chat')
    base_url = ds.get('base_url', 'https://api.deepseek.com').rstrip('/')
    if not api_key:
        raise ValueError('AI 主观评分未配置（需要 iflytek_config.json 中 deepseek.api_key）')
    resp = requests.post(
        base_url + '/chat/completions',
        headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
        },
        timeout=timeout,
    )
    data = resp.json()
    if 'choices' not in data:
        raise ValueError(f"DeepSeek 接口错误: {str(data)[:200]}")
    return data['choices'][0]['message']['content']

def llm_chat(prompt, timeout=60):
    if deepseek_enabled():
        return deepseek_chat(prompt, timeout)
    return spark_chat(prompt, timeout)

SCORING_PROMPT = """你是一位资深的初中英语口语教师。下面是学生的一段英语口语录音的转写文本（可能包含口误、重复、中式英语或夹杂其他语言）。请根据转写内容，对学生的英语口语表达进行主观评价。

学生转写文本：
"{transcript}"
{topic_line}
请严格按以下 JSON 格式输出（不要输出其他内容），每个维度 0-2 分（可有 0.5）：
{{
  "pronunciation": <发音准确度 0-2，依据转写中可推断的发音/拼写问题、词汇使用是否地道>，
  "intonation": <语音语调 0-2，依据句式是否自然、是否有疑问/感叹等语调线索>，
  "fluency": <表达流利度 0-2，依据重复、卡顿词、中断情况>，
  "completeness": <表达完整度 0-2，依据语义是否表达完整、句子是否成分残缺>，
  "rhythm": <节奏把控 0-2，依据句子长短、停顿是否合理>，
  "feedback": "<用中文写 2-3 句具体、鼓励性的评语，指出做得好的地方和 1-2 个改进建议>",
  "summary": "<一句话总评>"
}}
注意：转写文本是唯一证据，无法判断的维度给中间分 1 分。"""

def score_free_speech(transcript, topic=''):
    topic_line = f'\n表达主题/要求（供参考）：{topic}\n' if topic else ''
    prompt = SCORING_PROMPT.format(transcript=transcript, topic_line=topic_line)
    reply = llm_chat(prompt)

    text = reply.strip()
    if '```' in text:
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end == -1:
        raise ValueError('AI 评分结果解析失败: ' + reply[:200])
    data = json.loads(text[start:end + 1])

    dims = {}
    for key in ['pronunciation', 'intonation', 'fluency', 'completeness', 'rhythm']:
        try:
            v = float(data.get(key, 1))
        except (TypeError, ValueError):
            v = 1.0
        dims[key] = round(min(2.0, max(0.0, v)), 1)
    result = dict(dims)
    result['total'] = round(sum(dims.values()), 1)
    result['feedback'] = str(data.get('feedback', ''))
    result['summary'] = str(data.get('summary', ''))
    return result

# ---------- 数据库 ----------
app.config['DATABASE'] = os.path.join(BASE_DIR, 'speaking.db')

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'read',
            reference_text TEXT,
            transcript TEXT,
            audio_file TEXT,
            pronunciation REAL,
            intonation REAL,
            fluency REAL,
            completeness REAL,
            rhythm REAL,
            total REAL,
            feedback TEXT,
            ise_detail TEXT,
            created_at TEXT
        )
    ''')
    cols = {r[1] for r in conn.execute('PRAGMA table_info(records)')}
    for col, ddl in [
        ('mode', "TEXT NOT NULL DEFAULT 'read'"),
        ('transcript', 'TEXT'),
        ('feedback', 'TEXT'),
    ]:
        if col not in cols:
            conn.execute(f'ALTER TABLE records ADD COLUMN {col} {ddl}')
    conn.commit()
    conn.close()

init_db()

# ---------- 定时清理录音（保留最近 30 天） ----------
def cleanup_old_audio():
    RETENTION_DAYS = int(get_config('AUDIO_RETENTION_DAYS', '30'))
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    rows = conn.execute('SELECT id, audio_file FROM records WHERE created_at < ? AND audio_file IS NOT NULL', (cutoff,)).fetchall()
    deleted = 0
    for r in rows:
        path = os.path.join(app.config['UPLOAD_FOLDER'], r['audio_file'])
        if os.path.exists(path):
            os.remove(path)
            conn.execute('UPDATE records SET audio_file = NULL WHERE id = ?', (r['id'],))
            deleted += 1
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f'[cleanup] deleted {deleted} old audio files (before {cutoff})')

def start_cleanup_thread():
    interval = int(get_config('CLEANUP_INTERVAL_HOURS', '24')) * 3600
    def loop():
        while True:
            try:
                cleanup_old_audio()
            except Exception as e:
                print(f'[cleanup error] {e}')
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

if os.environ.get('ENABLE_CLEANUP', 'true').lower() == 'true':
    start_cleanup_thread()

# ---------- 路由 ----------
@app.route('/')
def index():
    return render_template('index.html',
                           ise_ready=ise_enabled(),
                           free_ready=free_mode_ready())

@app.route('/api/assess', methods=['POST'])
def assess():
    name = (request.form.get('name') or '').strip()
    mode = request.form.get('mode', 'read').strip()
    reference_text = (request.form.get('text') or '').strip()
    topic = (request.form.get('topic') or '').strip()
    audio_file = request.files.get('audio')

    if not name:
        return jsonify({"error": "请填写学生姓名"}), 400
    if not audio_file or audio_file.filename == '':
        return jsonify({"error": "请录制或上传音频"}), 400
    if mode == 'read' and not reference_text:
        return jsonify({"error": "请填写参考文本（学生要朗读的英文句子）"}), 400
    if mode not in ('read', 'free'):
        return jsonify({"error": "无效的评分模式"}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    safe_name = ''.join(c if c.isalnum() else '_' for c in name)[:30]
    audio_filename = f"{safe_name}_{timestamp}.wav"
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
    audio_file.save(audio_path)
    audio_bytes = open(audio_path, 'rb').read()

    transcript = ''
    feedback = ''
    ise_scores = None

    try:
        if mode == 'read':
            ise_scores = iflytek_assess(audio_bytes, reference_text)
            score = ise_to_score_result(ise_scores)
        else:
            transcript = iflytek_transcribe(audio_bytes, filename=audio_filename, language='en')
            if not transcript.strip():
                raise ValueError('未识别到语音内容，请确认麦克风正常并重试')
            score = score_free_speech(transcript, topic)
            feedback = score.pop('feedback', '')
            score.pop('summary', None)
    except Exception as e:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return jsonify({"error": f"AI 评分失败: {e}"}), 502

    conn = get_db()
    conn.execute('''
        INSERT INTO records
        (student_name, mode, reference_text, transcript, audio_file,
         pronunciation, intonation, fluency, completeness, rhythm, total, feedback, ise_detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name, mode, reference_text or None, transcript or None, audio_filename,
        score['pronunciation'], score['intonation'], score['fluency'],
        score['completeness'], score['rhythm'], score['total'],
        feedback or None,
        json.dumps(ise_scores) if ise_scores else None,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()
    record_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()

    return jsonify({"success": True, "record_id": record_id, "score": score,
                    "transcript": transcript, "feedback": feedback, "ise": ise_scores})

@app.route('/api/records')
def list_records():
    conn = get_db()
    rows = conn.execute('''
        SELECT id, student_name, mode, reference_text, transcript, audio_file,
               pronunciation, intonation, fluency, completeness, rhythm, total, feedback, created_at
        FROM records ORDER BY id DESC LIMIT 200
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/records/<int:rid>', methods=['DELETE'])
def delete_record(rid):
    conn = get_db()
    row = conn.execute('SELECT audio_file FROM records WHERE id = ?', (rid,)).fetchone()
    if row:
        conn.execute('DELETE FROM records WHERE id = ?', (rid,))
        conn.commit()
        if row['audio_file']:
            path = os.path.join(app.config['UPLOAD_FOLDER'], row['audio_file'])
            if os.path.exists(path):
                os.remove(path)
    conn.close()
    return jsonify({"success": True})

@app.route('/api/audio/<filename>')
def get_audio(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/stats')
def stats():
    conn = get_db()
    rows = conn.execute('SELECT student_name, total FROM records').fetchall()
    conn.close()
    by_student = {}
    for r in rows:
        by_student.setdefault(r['student_name'], []).append(r['total'])
    return jsonify([{
        "student_name": k,
        "count": len(v),
        "avg": round(sum(v) / len(v), 1),
        "best": max(v)
    } for k, v in by_student.items()])

@app.route('/api/access-info')
def access_info():
    # 云服务器部署时，直接使用当前请求的 host
    # 本地部署时尝试获取局域网 IP
    url = request.host_url.rstrip('/')
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    return jsonify({'url': url, 'qr': qr})

if __name__ == '__main__':
    port = int(get_config('PORT', '5017'))
    host = get_config('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)

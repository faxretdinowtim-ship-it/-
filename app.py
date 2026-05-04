import os
import re
import json
import logging
import tempfile
import subprocess
import time
from datetime import datetime
from flask import Flask, request, jsonify
import requests

TELEGRAM_TOKEN = "8663335250:AAG022Ubd_a00DTNk-JTx1bo4rhzHgw3myM"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # Токен из переменных окружения (безопасно)
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_sessions = {}
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"https://bot-koder.onrender.com/webhook"

# ==================== СПИСОК МОДЕЛЕЙ ====================
MODELS = [
    "Phi-4",
    "DeepSeek-R1",
    "Mistral-Large",
    "Llama-3.3-70B",
    "GPT-4o"
]

# ==================== AI ФУНКЦИЯ С АВТОПЕРЕКЛЮЧЕНИЕМ ====================
def call_ai(prompt):
    """Вызов GitHub Models с автоматическим переключением между моделями"""
    for model in MODELS:
        try:
            url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 401:
                continue
            if response.status_code == 429:
                continue
            if response.status_code != 200:
                continue
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
            return content.strip()
        except:
            continue
    
    return None

def send_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    try:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
    except:
        pass

def send_document(chat_id, filename, caption=""):
    try:
        with open(filename, "rb") as f:
            requests.post(f"{API_URL}/sendDocument", data={"chat_id": chat_id, "caption": caption}, files={"document": f}, timeout=30)
    except:
        pass

def run_code_safe(code):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_file = f.name
    try:
        process = subprocess.run(["python3", temp_file], capture_output=True, text=True, timeout=5)
        return {"success": process.returncode == 0, "output": process.stdout, "error": process.stderr}
    except:
        return {"success": False, "output": "", "error": "Timeout"}
    finally:
        os.unlink(temp_file)

def auto_fix_code(code):
    prompt = f"""Исправь все ошибки в этом коде. Верни ТОЛЬКО исправленный код.

Код:
{code}

Исправленный код:"""
    return call_ai(prompt)

def find_bugs_ai(code):
    prompt = f"""Найди все ошибки в этом коде. Верни JSON: {{"bugs": [{{"message": "...", "severity": "CRITICAL/HIGH/MEDIUM/LOW", "line": 0}}]}}

Код:
{code}"""
    response = call_ai(prompt)
    if response:
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group()).get("bugs", [])
        except:
            pass
    return []

def analyze_complexity(code):
    lines = code.split("\n")
    code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    functions = code.count("def ")
    classes = code.count("class ")
    branches = code.count("if ") + code.count("for ") + code.count("while ")
    complexity = 1 + branches * 0.5
    if complexity < 10:
        rating = "🟢 Низкая"
    elif complexity < 20:
        rating = "🟡 Средняя"
    else:
        rating = "🔴 Высокая"
    return f"📊 *Анализ сложности кода*\n\n• Строк кода: {code_lines}\n• Функций: {functions}\n• Классов: {classes}\n• Сложность: {complexity:.1f}\n• Оценка: {rating}"

def generate_code(description):
    prompt = f"""Напиши код на Python по описанию. Верни ТОЛЬКО код.

Описание: {description}

Код:"""
    return call_ai(prompt)

def smart_merge(parts):
    if not parts:
        return ""
    parts_text = "\n\n--- ЧАСТЬ ---\n\n".join(parts)
    prompt = f"""Объедини эти части кода в один работающий файл. Верни ТОЛЬКО итоговый код.

Части:
{parts_text}

Итоговый код:"""
    return call_ai(prompt)

def convert_code(code, target_lang):
    prompt = f"""Переведи этот код с Python на {target_lang}. Верни ТОЛЬКО код.

Код:
{code}

Код на {target_lang}:"""
    return call_ai(prompt)

def generate_tests(code):
    prompt = f"""Напиши pytest тесты для этого кода. Верни ТОЛЬКО код тестов.

Код:
{code}

Тесты:"""
    return call_ai(prompt)

def code_review(code):
    prompt = f"""Проведи code review этого кода. Найди проблемы, дай рекомендации.

Код:
{code}

Ответ:"""
    return call_ai(prompt)

def add_comments(code):
    prompt = f"""Добавь подробные комментарии к этому коду. Верни ТОЛЬКО код с комментариями.

Код:
{code}

Код с комментариями:"""
    return call_ai(prompt)

def create_pdf_export(code):
    escaped_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Экспорт кода</title>
<style>
body {{ font-family: monospace; padding: 40px; }}
pre {{ background: #f5f5f5; padding: 20px; overflow-x: auto; }}
</style>
</head>
<body>
<h1>Экспорт кода</h1>
<p>Дата: {datetime.now()}</p>
<pre>{escaped_code}</pre>
<p>Создано AI Code Bot</p>
</body>
</html>"""

def format_code(code):
    prompt = f"""Отформатируй этот код. Верни ТОЛЬКО отформатированный код.

Код:
{code}

Отформатированный код:"""
    return call_ai(prompt)

def search_in_code(code, search_term):
    lines = code.split('\n')
    results = []
    for i, line in enumerate(lines, 1):
        if search_term.lower() in line.lower():
            results.append(f"Строка {i}: {line[:100]}")
    if results:
        return "🔍 *Результаты поиска:*\n\n" + "\n".join(results[:20])
    return "❌ Ничего не найдено"

def replace_in_code(code, old, new):
    return code.replace(old, new)

def fix_bug_by_description(code, bug_description):
    prompt = f"""Исправь баг в коде: {bug_description}
Верни ТОЛЬКО исправленный код.

Код:
{code}

Исправленный код:"""
    return call_ai(prompt)

def improve_code_by_description(code, improvement):
    prompt = f"""Улучши код: {improvement}
Верни ТОЛЬКО улучшенный код.

Код:
{code}

Улучшенный код:"""
    return call_ai(prompt)

def explain_code(code):
    prompt = f"""Объясни, что делает этот код. Кратко и понятно.

Код:
{code}

Объяснение:"""
    return call_ai(prompt)

def refactor_code_ai(code):
    prompt = f"""Проведи рефакторинг кода. Верни ТОЛЬКО отрефакторенный код.

Код:
{code}

Отрефакторенный код:"""
    return call_ai(prompt)

def translate_code(code, target_lang):
    prompt = f"""Переведи код с Python на {target_lang}. Верни ТОЛЬКО код.

Код:
{code}

Код на {target_lang}:"""
    return call_ai(prompt)

def run_tests_with_report(code):
    tests = generate_tests(code)
    if not tests:
        return "❌ Не удалось сгенерировать тесты"
    full_code = code + "\n\n" + tests
    result = run_code_safe(full_code)
    if result["success"]:
        return "✅ *Все тесты пройдены!*\n\n" + result['output'][:500]
    else:
        return "❌ *Тесты не пройдены!*\n\n" + result['error'][:500]

def find_logic_bugs(code):
    prompt = f"""Найди логические ошибки в коде. Верни JSON.

Код:
{code}

JSON:"""
    response = call_ai(prompt)
    if response:
        try:
            return json.loads(response)
        except:
            return {"bugs": [{"message": response[:500]}]}
    return {"bugs": []}

def get_stats(user_id):
    data = user_sessions.get(user_id, {})
    return f"""📊 *Статистика:*\n• Символов: {len(data.get('code', ''))}\n• Частей: {len(data.get('parts', []))}\n• Действий: {len(data.get('history', []))}"""

# ==================== КЛАВИАТУРА ====================
def get_full_keyboard():
    return {
        "keyboard": [
            ["📝 Показать код", "💾 Скачать код", "🔧 ИСПРАВИТЬ"],
            ["🐛 ОШИБКИ", "📊 АНАЛИЗ", "🏃 ЗАПУСТИТЬ"],
            ["✨ ГЕНЕРАЦИЯ", "🧠 УМНАЯ СКЛЕЙКА", "🔄 ПРЕОБРАЗОВАТЬ"],
            ["🧪 ТЕСТЫ", "📋 CODE REVIEW", "📝 КОММЕНТАРИИ"],
            ["📄 ЭКСПОРТ PDF", "🎨 ФОРМАТИРОВАТЬ", "🔍 ПОИСК"],
            ["🔄 ЗАМЕНИТЬ", "🐞 FIX BUG", "⚡ УЛУЧШИТЬ"],
            ["📖 ОБЪЯСНИТЬ", "🔧 РЕФАКТОРИНГ", "🔄 ПЕРЕВОД"],
            ["🏆 ТЕСТЫ С ОТЧЁТОМ", "🧠 ЛОГИЧЕСКИЕ БАГИ", "📁 ФАЙЛЫ"],
            ["➕ ДОБАВИТЬ ФАЙЛ", "🗑 Удалить последний", "📜 ИСТОРИЯ"],
            ["📊 СТАТИСТИКА", "🗑 ОЧИСТИТЬ ВСЁ", "❓ ПОМОЩЬ"]
        ],
        "resize_keyboard": True
    }

def set_webhook():
    try:
        url = f"{API_URL}/setWebhook?url={WEBHOOK_URL}"
        response = requests.get(url, timeout=10)
        result = response.json()
        if result.get("ok"):
            logger.info(f"Webhook установлен: {WEBHOOK_URL}")
        return result
    except:
        return None

BUTTONS = {
    "📝 Показать код": "/show", "💾 Скачать код": "/done", "🔧 ИСПРАВИТЬ": "/fix",
    "🐛 ОШИБКИ": "/bugs", "📊 АНАЛИЗ": "/complexity", "🏃 ЗАПУСТИТЬ": "/run",
    "✨ ГЕНЕРАЦИЯ": "/generate", "🧠 УМНАЯ СКЛЕЙКА": "/smart_merge", "🔄 ПРЕОБРАЗОВАТЬ": "/convert",
    "🧪 ТЕСТЫ": "/tests", "📋 CODE REVIEW": "/review", "📝 КОММЕНТАРИЙ": "/comment",
    "📄 ЭКСПОРТ PDF": "/pdf", "🎨 ФОРМАТИРОВАТЬ": "/format", "🔍 ПОИСК": "/search",
    "🔄 ЗАМЕНИТЬ": "/replace", "🐞 FIX BUG": "/fixbug", "⚡ УЛУЧШИТЬ": "/improve",
    "📖 ОБЪЯСНИТЬ": "/explain", "🔧 РЕФАКТОРИНГ": "/refactor", "🔄 ПЕРЕВОД": "/translate",
    "🏆 ТЕСТЫ С ОТЧЁТОМ": "/test_report", "🧠 ЛОГИЧЕСКИЕ БАГИ": "/logic_bugs",
    "📁 ФАЙЛЫ": "/files", "➕ ДОБАВИТЬ ФАЙЛ": "/add_file", "🗑 Удалить последний": "/undo",
    "📜 ИСТОРИЯ": "/history", "📊 СТАТИСТИКА": "/stats", "🗑 ОЧИСТИТЬ ВСЁ": "/reset",
    "❓ ПОМОЩЬ": "/help"
}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        
        if data and "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")
            
            if user_id not in user_sessions:
                user_sessions[user_id] = {"code": "", "parts": [], "files": {}, "history": []}
            
            if text in BUTTONS:
                text = BUTTONS[text]
            
            if text == "/start":
                send_message(chat_id, "🤖 *AI Code Bot*\n\nВыбери действие:", reply_markup=json.dumps(get_full_keyboard()))
            
            elif text == "/show":
                code = user_sessions[user_id].get("code", "")
                send_message(chat_id, f"```python\n{code[:3000] if code else '# Код пуст'}\n```")
            
            elif text == "/done":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    filename = f"code_{user_id}.py"
                    with open(filename, "w") as f:
                        f.write(code)
                    send_document(chat_id, filename, "✅ Код")
                    os.remove(filename)
                else:
                    send_message(chat_id, "❌ Нет кода")
            
            elif text == "/fix":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    send_message(chat_id, "🔧 AI исправляет код...")
                    fixed = auto_fix_code(code)
                    if fixed:
                        user_sessions[user_id]["code"] = fixed
                        send_message(chat_id, f"✅ Исправлено:\n```python\n{fixed[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/bugs":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    bugs = find_bugs_ai(code)
                    if bugs:
                        report = "🔍 *Ошибки:*\n" + "\n".join([f"• {b.get('message', '')}" for b in bugs[:5]])
                        send_message(chat_id, report)
                    else:
                        send_message(chat_id, "✅ Ошибок не найдено")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/complexity":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    send_message(chat_id, analyze_complexity(code))
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/run":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    result = run_code_safe(code)
                    if result["success"]:
                        send_message(chat_id, f"✅ Выполнено!\n```\n{result['output'][:1500]}\n```")
                    else:
                        send_message(chat_id, f"❌ Ошибка:\n```\n{result['error'][:500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/generate":
                send_message(chat_id, "📝 *Опиши код для генерации:*")
                user_sessions[user_id]["waiting_for"] = "generate"
            
            elif text == "/smart_merge":
                parts = user_sessions[user_id].get("parts", [])
                if parts:
                    merged = smart_merge(parts)
                    if merged:
                        user_sessions[user_id]["code"] = merged
                        user_sessions[user_id]["parts"] = []
                        send_message(chat_id, f"✅ Код склеен!\n\n/show — посмотреть")
                else:
                    send_message(chat_id, "📭 Нет частей")
            
            elif text == "/format":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    formatted = format_code(code)
                    if formatted:
                        user_sessions[user_id]["code"] = formatted
                        send_message(chat_id, f"✅ Отформатировано:\n```python\n{formatted[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/search":
                send_message(chat_id, "🔍 *Введите текст для поиска:*")
                user_sessions[user_id]["waiting_for"] = "search"
            
            elif text == "/replace":
                send_message(chat_id, "🔄 *Формат:* старое | новое")
                user_sessions[user_id]["waiting_for"] = "replace"
            
            elif text == "/fixbug":
                send_message(chat_id, "🐞 *Опишите баг:*")
                user_sessions[user_id]["waiting_for"] = "fixbug"
            
            elif text == "/improve":
                send_message(chat_id, "⚡ *Опишите улучшение:*")
                user_sessions[user_id]["waiting_for"] = "improve"
            
            elif text == "/explain":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    explanation = explain_code(code)
                    send_message(chat_id, f"📖 *Объяснение:*\n{explanation[:2000]}")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/refactor":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    refactored = refactor_code_ai(code)
                    if refactored:
                        user_sessions[user_id]["code"] = refactored
                        send_message(chat_id, f"✅ Отрефакторено:\n```python\n{refactored[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/translate":
                send_message(chat_id, "🌐 *Выбери язык:* Python → JavaScript, Java, C++, Go, Rust")
                user_sessions[user_id]["waiting_for"] = "translate_lang"
            
            elif text == "/tests":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    tests = generate_tests(code)
                    if tests:
                        send_message(chat_id, f"✅ Тесты:\n```python\n{tests[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/review":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    review = code_review(code)
                    send_message(chat_id, f"📋 *Review:*\n{review[:2000]}")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/comment":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    commented = add_comments(code)
                    if commented:
                        user_sessions[user_id]["code"] = commented
                        send_message(chat_id, f"✅ Комментарии добавлены:\n```python\n{commented[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/pdf":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    html = create_pdf_export(code)
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                        f.write(html)
                        fname = f.name
                    send_document(chat_id, fname, "📄 PDF экспорт")
                    os.remove(fname)
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/test_report":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    report = run_tests_with_report(code)
                    send_message(chat_id, report)
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/logic_bugs":
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    result = find_logic_bugs(code)
                    bugs = result.get("bugs", [])
                    if bugs:
                        report = "🧠 *Логические ошибки:*\n" + "\n".join([f"• {b.get('message', '')}" for b in bugs[:5]])
                        send_message(chat_id, report)
                    else:
                        send_message(chat_id, "✅ Логических ошибок не найдено")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif text == "/files":
                files = user_sessions[user_id].get("files", {})
                if files:
                    file_list = "\n".join([f"• {n}" for n in files.keys()])
                    send_message(chat_id, f"📁 *Файлы:*\n{file_list}")
                else:
                    send_message(chat_id, "📭 Нет файлов")
            
            elif text == "/add_file":
                send_message(chat_id, "📝 Введите имя файла:")
                user_sessions[user_id]["waiting_for"] = "add_file"
            
            elif text == "/undo":
                parts = user_sessions[user_id].get("parts", [])
                if parts:
                    parts.pop()
                    user_sessions[user_id]["parts"] = parts
                    send_message(chat_id, f"🗑 Удалена последняя часть. Осталось: {len(parts)}")
                else:
                    send_message(chat_id, "📭 Нет частей")
            
            elif text == "/history":
                history = user_sessions[user_id].get("history", [])
                if history:
                    msg = "📜 *История:*\n" + "\n".join([f"{i}. {h.get('action', '')}" for i, h in enumerate(history[-10:], 1)])
                    send_message(chat_id, msg)
                else:
                    send_message(chat_id, "📭 История пуста")
            
            elif text == "/stats":
                send_message(chat_id, get_stats(user_id))
            
            elif text == "/reset":
                user_sessions[user_id] = {"code": "", "parts": [], "files": {}, "history": []}
                send_message(chat_id, "🧹 Всё очищено!", reply_markup=json.dumps(get_full_keyboard()))
            
            elif user_sessions[user_id].get("waiting_for") == "generate":
                user_sessions[user_id]["waiting_for"] = None
                generated = generate_code(text)
                if generated:
                    user_sessions[user_id]["code"] = generated
                    send_message(chat_id, f"✅ *Сгенерировано:*\n```python\n{generated[:2000]}\n```")
                else:
                    send_message(chat_id, "❌ Ошибка генерации")
            
            elif user_sessions[user_id].get("waiting_for") == "search":
                user_sessions[user_id]["waiting_for"] = None
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    result = search_in_code(code, text)
                    send_message(chat_id, result)
                else:
                    send_message(chat_id, "📭 Нет кода для поиска")
            
            elif user_sessions[user_id].get("waiting_for") == "replace":
                user_sessions[user_id]["waiting_for"] = None
                if "|" in text:
                    old, new = text.split("|", 1)
                    old = old.strip()
                    new = new.strip()
                    code = user_sessions[user_id].get("code", "")
                    if code.strip():
                        new_code = replace_in_code(code, old, new)
                        user_sessions[user_id]["code"] = new_code
                        send_message(chat_id, f"✅ Заменено '{old}' на '{new}'")
                    else:
                        send_message(chat_id, "📭 Нет кода")
                else:
                    send_message(chat_id, "❌ Формат: старое | новое")
            
            elif user_sessions[user_id].get("waiting_for") == "fixbug":
                user_sessions[user_id]["waiting_for"] = None
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    fixed = fix_bug_by_description(code, text)
                    if fixed:
                        user_sessions[user_id]["code"] = fixed
                        send_message(chat_id, f"✅ Баг исправлен!\n```python\n{fixed[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif user_sessions[user_id].get("waiting_for") == "improve":
                user_sessions[user_id]["waiting_for"] = None
                code = user_sessions[user_id].get("code", "")
                if code.strip():
                    improved = improve_code_by_description(code, text)
                    if improved:
                        user_sessions[user_id]["code"] = improved
                        send_message(chat_id, f"✅ Код улучшен!\n```python\n{improved[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif user_sessions[user_id].get("waiting_for") == "translate_lang":
                user_sessions[user_id]["waiting_for"] = None
                code = user_sessions[user_id].get("code", "")
                lang_map = {"javascript": "JavaScript", "js": "JavaScript", "java": "Java", "cpp": "C++", "go": "Go", "rust": "Rust"}
                target = lang_map.get(text.lower(), text)
                if code.strip():
                    translated = translate_code(code, target)
                    if translated:
                        user_sessions[user_id]["code"] = translated
                        send_message(chat_id, f"✅ Переведено на {target}:\n```\n{translated[:1500]}\n```")
                else:
                    send_message(chat_id, "📭 Нет кода")
            
            elif user_sessions[user_id].get("waiting_for") == "add_file":
                user_sessions[user_id]["waiting_for"] = None
                filename = text.strip()
                user_sessions[user_id]["files"][filename] = ""
                send_message(chat_id, f"✅ Файл `{filename}` создан")
            
            else:
                greetings = ["привет", "здравствуй", "hello", "hi", "ку"]
                if text.lower().strip() in greetings:
                    send_message(chat_id, "👋 *Привет!* Я AI Code Bot.\n\n📝 Отправь код, и я помогу!")
                else:
                    parts = user_sessions[user_id].get("parts", [])
                    parts.append(text)
                    user_sessions[user_id]["parts"] = parts
                    user_sessions[user_id]["code"] = text if not user_sessions[user_id]["code"] else user_sessions[user_id]["code"] + "\n\n" + text
                    user_sessions[user_id]["history"].append({"time": datetime.now().strftime("%H:%M:%S"), "action": f"Часть {len(parts)}"})
                    send_message(chat_id, f"✅ *Часть {len(parts)} сохранена!*")
        
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({"ok": False}), 500

@app.route("/")
def health():
    return "Bot is running!", 200

if __name__ == "__main__":
    time.sleep(2)
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)

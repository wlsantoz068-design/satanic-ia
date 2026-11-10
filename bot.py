#!/usr/bin/env python3
import os
import sys
import json
import time
import base64
import random
import logging
import datetime
import threading
import urllib.request
import urllib.error
import urllib.parse
from threading import Lock
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import config
except ImportError:
    print("[ERRO FATAL] O arquivo config.py não foi encontrado.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("SatanicIA")

BOT_TOKEN = getattr(config, "BOT_TOKEN", "").strip()
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", "").strip()
DEFAULT_CONFIG_MODEL = getattr(config, "GEMINI_MODEL", "gemini-flash-latest")
GEMINI_IMAGE_MODEL = getattr(config, "GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

if not BOT_TOKEN or "COLOQUE" in BOT_TOKEN:
    logger.error("BOT_TOKEN inválido em config.py.")
    sys.exit(1)

if not GEMINI_API_KEY or "COLOQUE" in GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY inválida em config.py.")
    sys.exit(1)

# SERVIDOR DE SAÚDE PORTA 7860
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SATANIC IA ONLINE 24/7 NO HUGGING FACE")

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 7860))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server error: {e}")

SYSTEM_INSTRUCTION = (
    "Você é a SATANIC IA, uma assistente virtual inteligente, educada, moderna, "
    "objetiva e criativa. Você responde sempre em português brasileiro de forma clara, "
    "sendo capaz de explicar assuntos difíceis de maneira simples. "
    "Mantenha um tom solícito, confiante e amigável."
)

WELCOME_MESSAGE = (
    "🩸 SATANIC IA\n\n"
    "Olá! Eu sou a SATANIC IA, sua assistente virtual com inteligência do Google Gemini e geração de imagens. 🔥\n\n"
    "Mande sua pergunta ou crie uma imagem agora mesmo!\n\n"
    "📌 Comandos:\n"
    "/img [descrição] — Gerar imagem por IA\n"
    "/novo — Começar uma conversa do zero\n"
    "/status — Ver o estado do bot\n"
    "/ajuda — Ver lista de comandos"
)

HELP_MESSAGE = (
    "🩸 *Comandos Disponíveis:*\n\n"
    "• /img <descrição> — Gera imagens com IA.\n"
    "  _Exemplo:_ `/img um dragão cibernético sobrevoando uma metrópole futurista`\n"
    "• /start — Inicia o assistente e boas-vindas.\n"
    "• /novo — Limpa sua memória de conversa atual.\n"
    "• /status — Exibe o status operacional do bot.\n"
    "• /ajuda — Mostra este guia de comandos."
)

MAX_TURNS_PER_USER = 10
MAX_USERS_CACHE = 400

memory_lock = Lock()
user_histories = {}
user_last_seen = {}
bot_start_time = time.time()
total_queries_processed = 0
total_images_generated = 0
active_models_pool = []

def trim_cache_if_needed():
    if len(user_histories) > MAX_USERS_CACHE:
        oldest = sorted(user_last_seen.items(), key=lambda x: x[1])[:100]
        for uid, _ in oldest:
            user_histories.pop(uid, None)
            user_last_seen.pop(uid, None)

def get_user_context(user_id):
    with memory_lock:
        user_last_seen[user_id] = time.time()
        return list(user_histories.get(user_id, []))

def append_user_message(user_id, role, text):
    with memory_lock:
        if user_id not in user_histories:
            user_histories[user_id] = []
        user_histories[user_id].append({"role": role, "parts": [{"text": text}]})
        if len(user_histories[user_id]) > MAX_TURNS_PER_USER:
            user_histories[user_id] = user_histories[user_id][-MAX_TURNS_PER_USER:]
        user_last_seen[user_id] = time.time()
        trim_cache_if_needed()

def reset_user_history(user_id):
    with memory_lock:
        if user_id in user_histories:
            user_histories[user_id] = []
            return True
        return False

def discover_available_models():
    global active_models_pool
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    discovered = []
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = m.get("name", "").replace("models/", "")
                    discovered.append(name)
    except Exception as e:
        logger.warning(f"Descoberta de modelos: {type(e).__name__}")

    priority_order = [
        DEFAULT_CONFIG_MODEL,
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash"
    ]
    final_pool = []
    for candidate in priority_order:
        if candidate not in final_pool and (not discovered or candidate in discovered or "latest" in candidate):
            final_pool.append(candidate)

    for m in discovered:
        if m not in final_pool and "flash" in m:
            final_pool.append(m)

    active_models_pool = final_pool or ["gemini-flash-latest", "gemini-3.8-flash"]
    logger.info(f"Modelos de texto ativos: {active_models_pool}")

def call_gemini_endpoint(model_name, conversation):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": conversation,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        candidates = res_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                return True, parts[0]["text"].strip()
        return False, "O modelo não retornou conteúdo."

def request_gemini(conversation):
    global active_models_pool
    if not active_models_pool:
        discover_available_models()

    for idx, model in enumerate(list(active_models_pool)):
        try:
            success, text = call_gemini_endpoint(model, conversation)
            if success:
                if idx > 0:
                    with memory_lock:
                        active_models_pool.insert(0, active_models_pool.pop(idx))
                return text
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                return "Erro de autenticação: Chave Gemini inválida ou sem permissão."
            continue
        except Exception:
            continue

    return "Serviço temporariamente indisponível. Repita a pergunta em instantes."

def generate_image_with_gemini(prompt_text):
    image_models_to_try = [
        GEMINI_IMAGE_MODEL,
        "gemini-2.5-flash-image",
        "imagen-3.0-generate-002"
    ]
    for model_name in image_models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            }
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": f"Generate image: {prompt_text}"}]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"]
                }
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for part in data.get("candidates", [])[0].get("content", {}).get("parts", []):
                    inline = part.get("inlineData", {})
                    if "data" in inline:
                        return base64.b64decode(inline["data"])
        except Exception:
            continue
    return None

def telegram_call(method, payload=None, timeout=30):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    headers = {"Content-Type": "application/json"}
    try:
        data_bytes = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        logger.warning(f"Erro Telegram ({method}): {type(err).__name__}")
        return None

def send_chat_action(chat_id, action="typing"):
    telegram_call("sendChatAction", {"chat_id": chat_id, "action": action}, timeout=8)

def send_message(chat_id, text, reply_to_id=None):
    max_len = 4000
    if len(text) <= max_len:
        p = {"chat_id": chat_id, "text": text}
        if reply_to_id:
            p["reply_to_message_id"] = reply_to_id
        telegram_call("sendMessage", p)
        return

    parts = []
    rem = text
    while len(rem) > max_len:
        split_at = rem.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(rem[:split_at])
        rem = rem[split_at:].lstrip()
    if rem:
        parts.append(rem)

    for p in parts:
        telegram_call("sendMessage", {"chat_id": chat_id, "text": p})
        time.sleep(0.3)

def send_photo_bytes(chat_id, image_bytes, caption=None, reply_to_id=None):
    boundary = f"----WebKitFormBoundary{random.randint(1000000000, 9999999999)}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    body = bytearray()

    def add_field(name, value):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    add_field("chat_id", str(chat_id))
    if caption:
        add_field("caption", caption)
    if reply_to_id:
        add_field("reply_to_message_id", str(reply_to_id))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="photo"; filename="image.png"\r\n')
    body.extend(b"Content-Type: image/png\r\n\r\n")
    body.extend(image_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    }

    try:
        req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("ok", False)
    except Exception as e:
        logger.error(f"Erro envio foto: {e}")
        return False

def send_photo_url(chat_id, photo_url, caption=None, reply_to_id=None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    if reply_to_id:
        payload["reply_to_message_id"] = reply_to_id
    res = telegram_call("sendPhoto", payload, timeout=45)
    return res is not None and res.get("ok", False)

def handle_image_generation(chat_id, prompt_text, msg_id):
    global total_images_generated
    send_chat_action(chat_id, "upload_photo")
    clean_prompt = prompt_text.strip()

    img_bytes = generate_image_with_gemini(clean_prompt)
    if img_bytes:
        cap = f"🎨 *Prompt:* _{clean_prompt}_\n🩸 *SATANIC IA* (Gemini Vision)"
        if send_photo_bytes(chat_id, img_bytes, caption=cap, reply_to_id=msg_id):
            total_images_generated += 1
            return

    encoded = urllib.parse.quote(clean_prompt)
    seed = random.randint(1, 9999999)
    fallback_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&seed={seed}&nologo=true"
    cap_fallback = f"🎨 *Prompt:* _{clean_prompt}_\n🩸 *SATANIC IA*"

    if send_photo_url(chat_id, fallback_url, caption=cap_fallback, reply_to_id=msg_id):
        total_images_generated += 1
    else:
        send_message(chat_id, "⚠️ Falha ao renderizar imagem. Tente novamente.", reply_to_id=msg_id)

def process_message(update):
    global total_queries_processed
    msg = update.get("message")
    if not msg:
        return

    text = msg.get("text", "").strip()
    chat_id = msg.get("chat", {}).get("id")
    user_id = str(msg.get("from", {}).get("id", chat_id))
    msg_id = msg.get("message_id")

    if not text or not chat_id:
        return

    if text.startswith("/start"):
        send_message(chat_id, WELCOME_MESSAGE)
        return

    if text.startswith("/ajuda"):
        send_message(chat_id, HELP_MESSAGE)
        return

    if text.startswith("/novo"):
        reset_user_history(user_id)
        send_message(chat_id, "🧹 Histórico de conversa limpo! Começamos do zero.", reply_to_id=msg_id)
        return

    if text.startswith("/status"):
        uptime = str(datetime.timedelta(seconds=int(time.time() - bot_start_time)))
        with memory_lock:
            cached_users = len(user_histories)
            current_model = active_models_pool[0] if active_models_pool else "Auto"
        status_text = (
            "⚙️ *STATUS DO SISTEMA — SATANIC IA (24/7)*\n\n"
            f"• *Status:* Operacional 🟢\n"
            f"• *Modelo Texto:* `{current_model}`\n"
            f"• *Motor Imagem:* `Dual-Engine`\n"
            f"• *Uptime:* `{uptime}`\n"
            f"• *Usuários Ativos:* `{cached_users}`\n"
            f"• *Consultas:* `{total_queries_processed}`\n"
            f"• *Imagens:* `{total_images_generated}`"
        )
        send_message(chat_id, status_text)
        return

    if text.startswith("/img") or text.startswith("/imagem"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o prompt: `/img castelo medieval`", reply_to_id=msg_id)
            return
        handle_image_generation(chat_id, parts[1].strip(), msg_id)
        return

    send_chat_action(chat_id, "typing")
    context = get_user_context(user_id)
    context.append({"role": "user", "parts": [{"text": text}]})

    response = request_gemini(context)

    total_queries_processed += 1
    append_user_message(user_id, "user", text)
    append_user_message(user_id, "model", response)

    send_message(chat_id, response, reply_to_id=msg_id)

def main():
    logger.info("Iniciando SATANIC IA...")

    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    discover_available_models()

    me = telegram_call("getMe")
    if not me or not me.get("ok"):
        logger.error("Falha ao autenticar com Telegram. Verifique seu BOT_TOKEN.")
        sys.exit(1)

    username = me.get("result", {}).get("username", "Desconhecido")
    logger.info(f"SATANIC IA online como @{username}")

    offset = None
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            updates_data = telegram_call("getUpdates", params, timeout=35)
            if updates_data and updates_data.get("ok"):
                for upd in updates_data.get("result", []):
                    offset = upd["update_id"] + 1
                    try:
                        process_message(upd)
                    except Exception as err:
                        logger.error(f"Erro: {type(err).__name__}")
            else:
                time.sleep(2)

        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(4)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
=====================================================
SATANIC IA — BOT INTELIGENTE PARA TELEGRAM
Criador: Raizel Mddz
Texto: Google Gemini API (com auto-fallback)
Imagens: FLUX HD Oficial (com suporte a Tipografia/Logos)
Hospedagem: Render (24/7 Online)
=====================================================
"""

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
    print("[ERRO FATAL] config.py não encontrado.")
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

# Servidor de saúde para o Render (Porta 10000)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SATANIC IA ONLINE 24/7 NO RENDER (Criada por Raizel Mddz)")

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server: {e}")

SYSTEM_INSTRUCTION = (
    "Você é a SATANIC IA, uma inteligência artificial moderna, objetiva e cheia de "
    "personalidade, criada exclusivamente pelo desenvolvedor Raizel Mddz. "
    "Você foi desenvolvida para unir tecnologia de ponta e eficiência, tornando a vida "
    "das pessoas mais fácil e explicando assuntos complexos de forma simples e acessível, "
    "sempre com um toque de elegância, simpatia e confiança. "
    "Você responde sempre em português brasileiro. "
    "Se alguém perguntar quem criou você, diga com orgulho que foi o Raizel Mddz."
)

WELCOME_MESSAGE = (
    "🩸 SATANIC IA\n\n"
    "Olá! Eu sou a SATANIC IA, fui criada pelo **Raizel Mddz**.\n\n"
    "Sou uma inteligência artificial moderna, objetiva e cheia de personalidade, "
    "desenvolvida para unir tecnologia de ponta e eficiência. Estou aqui para tornar a "
    "sua vida mais fácil, explicar assuntos complexos de forma simples e ajudar no que você "
    "precisar, sempre com um toque de elegância e simpatia.\n\n"
    "Como posso te ajudar hoje? 🔥\n\n"
    "📌 Comandos:\n"
    "/img [descrição] — Gerar imagem realista com FLUX HD\n"
    "/novo — Começar uma conversa do zero\n"
    "/status — Ver o estado do bot\n"
    "/ajuda — Ver lista de comandos"
)

HELP_MESSAGE = (
    "🩸 *Comandos Disponíveis — SATANIC IA:*\n\n"
    "• /img <descrição> — Gera imagens fiéis e realistas em alta definição.\n"
    "  _Exemplo:_ `/img um lobo cibernético com olhos vermelhos sob a névoa`\n"
    "  _Exemplo com texto:_ `/img logotipo 3d com o nome SATANIC IA metálico`\n"
    "• /start — Iniciar o assistente e ver a mensagem de boas-vindas.\n"
    "• /novo — Limpar memória e histórico de conversa.\n"
    "• /status — Ver o status operacional e tempo de atividade do bot.\n"
    "• /ajuda — Mostra este guia de comandos.\n\n"
    "Criada por: **Raizel Mddz**"
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
        logger.warning(f"Descoberta de modelos: {e}")

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

    with urllib.request.urlopen(req, timeout=25) as resp:
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
        except Exception:
            continue

    return "Serviço temporariamente indisponível. Repita a pergunta em instantes."

# ---------------------------------------------------
# TRADUTOR COM AUTO-ROTAÇÃO (NUNCA TRAVA EM 503)
# ---------------------------------------------------
def translate_prompt_accurately(user_prompt):
    """
    Traduz e adapta pedidos de imagem (incluindo textos/logos)
    usando a fila de modelos para não falhar com 503.
    """
    translation_task = [
        {
            "role": "user",
            "parts": [{
                "text": (
                    "Act as an expert prompt translator for FLUX image generator. "
                    "Translate the following user request into English. "
                    "If the user wants words or a name on the image, specify: bold 3D text 'NAME' in typography logo style. "
                    "Keep the exact subject, add realistic cinematic lighting and 8k detail. "
                    "Return ONLY the prompt string without any quotes or explanations:\n\n"
                    f"{user_prompt}"
                )
            }]
        }
    ]

    try:
        translated = request_gemini(translation_task)
        if translated and len(translated) > 3 and "Serviço temporariamente" not in translated:
            clean = translated.replace('"', '').replace('\n', ' ').strip()
            if ":" in clean and len(clean.split(":", 1)[0]) < 20:
                clean = clean.split(":", 1)[1].strip()
            logger.info(f"Prompt pronto para imagem: {clean}")
            return clean
    except Exception as e:
        logger.warning(f"Fallback no tradutor: {e}")

    return f"{user_prompt}, 8k, photorealistic, highly detailed, dramatic lighting"

# ---------------------------------------------------
# MOTOR DE IMAGENS FLUX HD COM AUTO-FALLBACK
# ---------------------------------------------------
def fetch_image_bytes(english_prompt):
    encoded = urllib.parse.quote(english_prompt)
    seed = random.randint(10000, 9999999)

    # Tenta com FLUX oficial; se o FLUX demorar, usa turbo (rápido e preciso)
    models = ["flux", "turbo"]

    for mod in models:
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?model={mod}&width=1024&height=1024&seed={seed}&nologo=true"
        )
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            timeout_to_use = 35 if mod == "flux" else 20
            with urllib.request.urlopen(req, timeout=timeout_to_use) as resp:
                data = resp.read()
                if len(data) > 8000 and (data[:2] == b'\xff\xd8' or data[:4] == b'\x89PNG'):
                    logger.info(f"Imagem gerada com sucesso via [{mod}]!")
                    return data
        except Exception as e:
            logger.warning(f"Tentativa com [{mod}] falhou: {type(e).__name__}. Tentando reserva...")
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
    except urllib.error.HTTPError as err:
        logger.warning(f"HTTP {err.code} no Telegram ({method}).")
        return None
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
    body.extend(b'Content-Disposition: form-data; name="photo"; filename="image.jpg"\r\n')
    body.extend(b"Content-Type: image/jpeg\r\n\r\n")
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
        logger.error(f"Erro no envio binário da foto: {e}")
        return False

def handle_image_generation(chat_id, user_prompt, msg_id):
    global total_images_generated
    send_chat_action(chat_id, "upload_photo")

    clean_prompt = user_prompt.strip()

    # 1. Traduz e adapta para modelo de imagem com auto-fallback
    english_prompt = translate_prompt_accurately(clean_prompt)

    # 2. Gera e baixa a imagem direta
    img_data = fetch_image_bytes(english_prompt)

    if img_data:
        caption = (
            f"🎨 *Prompt:* _{clean_prompt}_\n"
            f"✨ *Motor:* `FLUX HD Oficial`\n"
            f"🩸 *SATANIC IA* • Criada por: *Raizel Mddz*"
        )
        if send_photo_bytes(chat_id, img_data, caption=caption, reply_to_id=msg_id):
            total_images_generated += 1
            return

    send_message(chat_id, "⚠️ O servidor de imagem está com alta demanda. Tente novamente em instantes.", reply_to_id=msg_id)

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

    logger.info(f"Mensagem recebida de {user_id}: {text}")

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
            f"• *Criador:* Raizel Mddz\n"
            f"• *Status:* Operacional 🟢\n"
            f"• *Modelo Texto:* `{current_model}`\n"
            f"• *Motor Imagem:* `FLUX HD Oficial`\n"
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
            send_message(chat_id, "⚠️ Digite o prompt: `/img logotipo 3d com o nome SATANIC IA`", reply_to_id=msg_id)
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

    logger.info("Limpando possíveis travas de webhook...")
    telegram_call("deleteWebhook", {"drop_pending_updates": True})

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
            params = {"timeout": 20}
            if offset is not None:
                params["offset"] = offset

            updates_data = telegram_call("getUpdates", params, timeout=30)
            if updates_data and updates_data.get("ok"):
                for upd in updates_data.get("result", []):
                    offset = upd["update_id"] + 1
                    try:
                        process_message(upd)
                    except Exception as err:
                        logger.error(f"Erro ao processar: {type(err).__name__}")
            else:
                time.sleep(2)

        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(4)

if __name__ == "__main__":
    main()

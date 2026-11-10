#!/usr/bin/env python3
"""
=====================================================
SATANIC IA — BOT MULTIFUNCIONAL PARA TELEGRAM
Criador Oficial: Raizel Mddz
Menu Nativo: Comandos registrados na API do Telegram
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

# CREDENCIAIS
BOT_TOKEN = getattr(config, "BOT_TOKEN", "").strip()
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", "").strip()
DEFAULT_CONFIG_MODEL = getattr(config, "GEMINI_MODEL", "gemini-flash-latest")

# ID SILENCIOSO DO CRIADOR
OWNER_ID = "8593052742"

# Servidor de saúde para o Render (Porta 10000)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SATANIC IA ONLINE 24/7 NO RENDER")

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
    "Você une tecnologia de ponta e eficiência para responder qualquer dúvida de "
    "forma simples, elegante e prestativa. Responda sempre em português brasileiro. "
    "Se alguém perguntar quem criou você, diga com respeito que foi o Raizel Mddz."
)

WELCOME_MESSAGE_USER = (
    "🩸 SATANIC IA\n\n"
    "Olá! Eu sou a SATANIC IA, fui criada pelo **Raizel Mddz**.\n\n"
    "Sou uma inteligência artificial completa! Toque no botão **Menu** ao lado do seu "
    "teclado para ver todos os comandos disponíveis.\n\n"
    "📌 *Principais Recursos:*\n"
    "• /img [descrição] — Gerar imagem 8k com FLUX HD\n"
    "• /voz [texto] — Gerar áudio com voz falada\n"
    "• /video [descrição] — Criar vídeo/animação por IA\n"
    "• /clima [cidade] — Previsão do tempo ao vivo\n"
    "• /wiki [assunto] — Pesquisa enciclopédica inteligente\n"
    "• 📸 *Mande uma foto no chat* — Eu analiso e explico tudo!\n"
    "• /id — Ver suas informações de usuário\n"
    "• /status — Ver o status do servidor"
)

WELCOME_MESSAGE_CREATOR = (
    "🩸 *SATANIC IA — MODO CRIADOR ATIVADO*\n\n"
    "Bem-vindo de volta, **Raizel Mddz**! 👑\n"
    "Reconhecimento biométrico confirmado.\n\n"
    "🛠️ *Painel de Gestão:*\n"
    "• /painel — Métricas e estatísticas em tempo real\n"
    "• /usuarios — Ver lista de usuários com Nick e ID\n"
    "• /usuario <id> — Ver ficha detalhada de um usuário\n"
    "• /aviso <texto> — Transmissão em massa para todos\n"
    "• /limparcache — Esvaziar RAM do servidor\n\n"
    "Todos os comandos foram adicionados ao seu menu!"
)

HELP_MESSAGE = (
    "🩸 *Guia de Comandos — SATANIC IA:*\n\n"
    "🎨 *Multimídia & Criação:*\n"
    "• `/img <descrição>` — Imagens realistas em alta definição.\n"
    "• `/video <descrição>` — Cria vídeos curtos e animações.\n"
    "• `/voz <texto>` — Envia áudio falado com voz natural.\n"
    "• 📸 *Envie uma foto* para análise visual detalhada.\n\n"
    "🌐 *Pesquisas & Utilidades:*\n"
    "• `/clima <cidade>` — Clima e temperatura em tempo real.\n"
    "• `/wiki <termo>` — Pesquisa enciclopédica inteligente.\n"
    "• `/id` — Exibe seu nome, @username e ID.\n"
    "• `/novo` — Reinicia a conversa.\n"
    "• `/status` — Mostra o estado do servidor.\n\n"
    "Criada por: **Raizel Mddz**"
)

MAX_TURNS_PER_USER = 10
MAX_USERS_CACHE = 400

memory_lock = Lock()
user_histories = {}
user_last_seen = {}
user_profiles = {}

bot_start_time = time.time()
total_queries_processed = 0
total_images_generated = 0
total_voices_generated = 0
total_videos_generated = 0
active_models_pool = []

def is_creator(user_id):
    return str(user_id).strip() == OWNER_ID

def register_user_profile(user_id, first_name, username):
    uid = str(user_id)
    with memory_lock:
        if uid not in user_profiles:
            user_profiles[uid] = {
                "name": first_name or "Sem nome",
                "username": username or "Sem @",
                "first_seen": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "msg_count": 0
            }
        user_profiles[uid]["msg_count"] += 1
        user_profiles[uid]["last_seen"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        if first_name:
            user_profiles[uid]["name"] = first_name
        if username:
            user_profiles[uid]["username"] = username

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

# ---------------------------------------------------
# CONFIGURAÇÃO DO MENU DE COMANDOS DO TELEGRAM
# ---------------------------------------------------
def setup_telegram_commands_menu():
    """Registra os comandos no botão Menu nativo do Telegram."""
    user_commands = [
        {"command": "img", "description": "🎨 Gerar imagem 8k com FLUX HD"},
        {"command": "voz", "description": "🎙️ Gerar áudio falado por IA"},
        {"command": "video", "description": "🎬 Gerar vídeo/animação por IA"},
        {"command": "clima", "description": "🌦️ Previsão do tempo ao vivo"},
        {"command": "wiki", "description": "📚 Pesquisa enciclopédica inteligente"},
        {"command": "id", "description": "👤 Ver seu perfil e ID de usuário"},
        {"command": "novo", "description": "🧹 Limpar memória da conversa"},
        {"command": "status", "description": "⚙️ Ver status e saúde da IA"},
        {"command": "ajuda", "description": "📖 Guia completo de comandos"}
    ]

    # Registra o menu público geral
    telegram_call("setMyCommands", {"commands": user_commands})

    # Registra o menu especial exclusivo para o Criador (Raizel Mddz)
    creator_commands = user_commands + [
        {"command": "painel", "description": "👑 Abrir Painel do Criador"},
        {"command": "usuarios", "description": "👥 Ver lista de usuários com ID e Nick"},
        {"command": "aviso", "description": "📢 Enviar transmissão em massa"},
        {"command": "limparcache", "description": "🧹 Esvaziar RAM do servidor"}
    ]
    telegram_call("setMyCommands", {
        "commands": creator_commands,
        "scope": {"type": "chat", "chat_id": OWNER_ID}
    })
    logger.info("Menu nativo de comandos configurado com sucesso!")

# ---------------------------------------------------
# MOTOR DE TEXTO E VISÃO GEMINI
# ---------------------------------------------------
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
    logger.info(f"Modelos de texto/visão prontos: {active_models_pool}")

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
# VISÃO COMPUTACIONAL (ANÁLISE DE FOTOS)
# ---------------------------------------------------
def analyze_photo_with_gemini(photo_bytes, user_prompt):
    b64_image = base64.b64encode(photo_bytes).decode("utf-8")
    prompt = user_prompt if user_prompt else "Analise esta imagem detalhadamente em português e explique o que você vê nela."

    contents = [{
        "role": "user",
        "parts": [
            {"text": prompt},
            {
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": b64_image
                }
            }
        ]
    }]

    global active_models_pool
    if not active_models_pool:
        discover_available_models()

    for model in active_models_pool:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048}
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=30) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                parts = res_json.get("candidates", [])[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()
        except Exception:
            continue

    return "Não consegui processar a foto enviada no momento. Tente novamente."

# ---------------------------------------------------
# TEXT-TO-SPEECH (ÁUDIO / VOZ)
# ---------------------------------------------------
def generate_voice_bytes(text_to_speak):
    clean_text = text_to_speak.strip()[:250]
    encoded_text = urllib.parse.quote(clean_text)
    url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl=pt-BR&client=tw-ob"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            if len(data) > 1000:
                return data
    except Exception as e:
        logger.warning(f"Erro TTS: {e}")
    return None

# ---------------------------------------------------
# UTILITÁRIOS: CLIMA E WIKIPÉDIA INTELIGENTE
# ---------------------------------------------------
def fetch_weather(city_name):
    encoded_city = urllib.parse.quote(city_name.strip())
    url = f"https://wttr.in/{encoded_city}?format=j1"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            curr = data.get("current_condition", [])[0]
            temp = curr.get("temp_C", "?")
            feels = curr.get("FeelsLikeC", "?")
            humidity = curr.get("humidity", "?")
            wind = curr.get("windspeedKmph", "?")
            desc = curr.get("lang_pt", [{}])[0].get("value") or curr.get("weatherDesc", [{}])[0].get("value", "")

            return (
                f"🌦️ *CLIMA ATUAL — {city_name.title()}*\n\n"
                f"• *Condição:* {desc}\n"
                f"• *Temperatura:* `{temp}°C` (Sensação de `{feels}°C`)\n"
                f"• *Umidade:* `{humidity}%`\n"
                f"• *Vento:* `{wind} km/h`\n\n"
                f"🩸 *SATANIC IA*"
            )
    except Exception:
        return f"❌ Não foi possível obter a previsão para '{city_name}'. Verifique o nome da cidade."

def fetch_wikipedia_smart(search_term):
    """
    Pesquisa na Wikipédia oficial. Se não houver artigo exato,
    a IA do Gemini explica o assunto enciclopedicamente.
    """
    clean_term = search_term.strip()
    encoded_term = urllib.parse.quote(clean_term.replace(" ", "_"))
    url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{encoded_term}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SatanicIA_Bot/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            title = data.get("title", clean_term)
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

            if extract and len(extract) > 20:
                return (
                    f"📚 *ENCICLOPÉDIA OFICIAL — {title}*\n\n"
                    f"{extract}\n\n"
                    f"🔗 [Ler artigo na Wikipédia]({page_url})\n"
                    f"🩸 *SATANIC IA*"
                )
    except Exception:
        pass

    # Fallback inteligente: O Gemini explica o assunto como enciclopédia
    logger.info(f"Termo '{clean_term}' não encontrado na Wikipédia formal. Acionando IA...")
    ai_query = [{
        "role": "user",
        "parts": [{
            "text": (
                f"Escreva um resumo explicativo e enciclopédico sobre o termo: '{clean_term}'. "
                "Explique o que é, o contexto, curiosidades e significados em 2 a 3 parágrafos claros em português brasileiro."
            )
        }]
    }]
    ai_explanation = request_gemini(ai_query)
    return (
        f"📚 *ENCICLOPÉDIA IA — {clean_term.title()}*\n\n"
        f"{ai_explanation}\n\n"
        f"🩸 *SATANIC IA (Conhecimento Sintético)*"
    )

# ---------------------------------------------------
# GERAÇÃO DE VÍDEO / ANIMAÇÃO (/video)
# ---------------------------------------------------
def fetch_video_bytes(english_prompt):
    """Busca animação/vídeo curto gerado por IA."""
    encoded = urllib.parse.quote(english_prompt)
    seed = random.randint(1000, 999999)
    
    # Endpoints de vídeo e animação resilientes
    endpoints = [
        f"https://video.pollinations.ai/prompt/{encoded}?width=512&height=512&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{encoded}?model=video&width=512&height=512&seed={seed}&nologo=true"
    ]

    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=50) as resp:
                data = resp.read()
                if len(data) > 5000:
                    return data
        except Exception:
            continue
    return None

# ---------------------------------------------------
# MOTOR DE IMAGENS FLUX HD
# ---------------------------------------------------
def translate_prompt_accurately(user_prompt):
    translation_task = [{
        "role": "user",
        "parts": [{
            "text": (
                "Act as an expert prompt translator for AI image and video generators. "
                "Translate this user prompt to English. If text is requested, format as: bold 3D text 'NAME'. "
                "Keep the subject, add realistic cinematic lighting and 8k detail. "
                f"Return ONLY the prompt string:\n\n{user_prompt}"
            )
        }]
    }]

    try:
        translated = request_gemini(translation_task)
        if translated and len(translated) > 3 and "Serviço temporariamente" not in translated:
            clean = translated.replace('"', '').replace('\n', ' ').strip()
            if ":" in clean and len(clean.split(":", 1)[0]) < 20:
                clean = clean.split(":", 1)[1].strip()
            return clean
    except Exception:
        pass

    return f"{user_prompt}, 8k, photorealistic, cinematic lighting"

def fetch_image_bytes(english_prompt):
    encoded = urllib.parse.quote(english_prompt)
    seed = random.randint(10000, 9999999)

    for mod in ["flux", "turbo"]:
        url = f"https://image.pollinations.ai/prompt/{encoded}?model={mod}&width=1024&height=1024&seed={seed}&nologo=true"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            timeout_val = 35 if mod == "flux" else 20
            with urllib.request.urlopen(req, timeout=timeout_val) as resp:
                data = resp.read()
                if len(data) > 8000 and (data[:2] == b'\xff\xd8' or data[:4] == b'\x89PNG'):
                    return data
        except Exception:
            continue
    return None

# ---------------------------------------------------
# ENVIOS NATIVOS TELEGRAM (MULTIPART)
# ---------------------------------------------------
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

def send_multipart_file(method, field_name, chat_id, file_bytes, filename, mime_type, caption=None, reply_to_id=None):
    boundary = f"----WebKitFormBoundary{random.randint(1000000000, 9999999999)}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
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
    body.extend(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    }

    try:
        req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("ok", False)
    except Exception as e:
        logger.error(f"Erro multipart ({method}): {e}")
        return False

# ---------------------------------------------------
# PROCESSAMENTO DE MENSAGENS E ATUALIZAÇÕES
# ---------------------------------------------------
def process_message(update):
    global total_queries_processed, total_images_generated, total_voices_generated, total_videos_generated

    msg = update.get("message")
    if not msg:
        return

    chat_id = msg.get("chat", {}).get("id")
    user_id = str(msg.get("from", {}).get("id", chat_id))
    first_name = msg.get("from", {}).get("first_name", "Usuário")
    username = msg.get("from", {}).get("username", "")
    msg_id = msg.get("message_id")
    text = msg.get("text", "").strip()
    caption = msg.get("caption", "").strip()

    if not chat_id:
        return

    register_user_profile(user_id, first_name, username)

    # ===================================================
    # 1. FOTO RECEBIDA (GEMINI VISION)
    # ===================================================
    photos = msg.get("photo")
    if photos:
        send_chat_action(chat_id, "typing")
        photo_id = photos[-1]["file_id"]

        res_file = telegram_call("getFile", {"file_id": photo_id})
        if res_file and res_file.get("ok"):
            file_path = res_file["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            try:
                req = urllib.request.Request(download_url)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    photo_data = resp.read()

                vision_analysis = analyze_photo_with_gemini(photo_data, caption)
                total_queries_processed += 1
                send_message(chat_id, vision_analysis, reply_to_id=msg_id)
                return
            except Exception as e:
                logger.error(f"Erro na visão da foto: {e}")

        send_message(chat_id, "❌ Não consegui baixar ou processar a imagem. Tente novamente.", reply_to_id=msg_id)
        return

    if not text:
        return

    logger.info(f"Mensagem de {user_id} (@{username or 'sem_nick'}): {text}")

    # ===================================================
    # 2. COMANDOS GERAIS & ID
    # ===================================================
    if text.startswith("/start"):
        if is_creator(user_id):
            send_message(chat_id, WELCOME_MESSAGE_CREATOR)
        else:
            send_message(chat_id, WELCOME_MESSAGE_USER)
        return

    if text.startswith("/id") or text.startswith("/meuid"):
        user_info = (
            "👤 *Suas Informações no Sistema:*\n\n"
            f"• *Nome:* {first_name}\n"
            f"• *User ID:* `{user_id}`\n"
            f"• *Username:* @{username if username else 'Nenhum'}\n"
            f"• *Status:* {'👑 Criador' if is_creator(user_id) else 'Membro'}"
        )
        send_message(chat_id, user_info, reply_to_id=msg_id)
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
            f"• *Imagens:* `{total_images_generated}`\n"
            f"• *Vozes:* `{total_voices_generated}`\n"
            f"• *Vídeos:* `{total_videos_generated}`"
        )
        send_message(chat_id, status_text)
        return

    # ===================================================
    # 3. RESPOSTA EM VOZ (/voz)
    # ===================================================
    if text.startswith("/voz") or text.startswith("/audio"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o texto: `/voz Olá, eu sou a SATANIC IA!`", reply_to_id=msg_id)
            return

        send_chat_action(chat_id, "record_voice")
        texto_falar = parts[1].strip()
        audio_bytes = generate_voice_bytes(texto_falar)

        if audio_bytes:
            ok = send_multipart_file("sendVoice", "voice", chat_id, audio_bytes, "voice.mp3", "audio/mpeg", caption="🎙️ *SATANIC IA* (Áudio)", reply_to_id=msg_id)
            if ok:
                total_voices_generated += 1
                return

        send_message(chat_id, "⚠️ Não consegui gerar o áudio no momento. Tente novamente.", reply_to_id=msg_id)
        return

    # ===================================================
    # 4. CLIMA E WIKIPÉDIA INTELIGENTE
    # ===================================================
    if text.startswith("/clima") or text.startswith("/tempo"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o nome da cidade: `/clima Rio de Janeiro`", reply_to_id=msg_id)
            return

        send_chat_action(chat_id, "typing")
        resultado_clima = fetch_weather(parts[1].strip())
        send_message(chat_id, resultado_clima, reply_to_id=msg_id)
        return

    if text.startswith("/wiki") or text.startswith("/pesquisa"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o termo: `/wiki Inteligência Artificial`", reply_to_id=msg_id)
            return

        send_chat_action(chat_id, "typing")
        resultado_wiki = fetch_wikipedia_smart(parts[1].strip())
        send_message(chat_id, resultado_wiki, reply_to_id=msg_id)
        return

    # ===================================================
    # 5. GERAÇÃO DE VÍDEO (/video)
    # ===================================================
    if text.startswith("/video"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite a descrição: `/video um dragão voando sobre um castelo`", reply_to_id=msg_id)
            return

        send_chat_action(chat_id, "upload_video")
        send_message(chat_id, "🎬 *Renderizando animação por IA... Aguarde alguns instantes.*", reply_to_id=msg_id)

        prompt_video = parts[1].strip()
        english_prompt = translate_prompt_accurately(prompt_video)
        video_bytes = fetch_video_bytes(english_prompt)

        if video_bytes:
            cap = f"🎬 *Prompt:* _{prompt_video}_\n🩸 *SATANIC IA Video*"
            ok = send_multipart_file("sendVideo", "video", chat_id, video_bytes, "video.mp4", "video/mp4", caption=cap, reply_to_id=msg_id)
            if ok:
                total_videos_generated += 1
                return

        send_message(chat_id, "⚠️ Servidor de vídeo sobrecarregado no momento. Tente novamente em instantes.", reply_to_id=msg_id)
        return

    # ===================================================
    # 6. GERAÇÃO DE IMAGEM (/img)
    # ===================================================
    if text.startswith("/img") or text.startswith("/imagem"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o prompt: `/img logotipo 3d com o nome SATANIC IA`", reply_to_id=msg_id)
            return

        send_chat_action(chat_id, "upload_photo")
        prompt_img = parts[1].strip()
        english_prompt = translate_prompt_accurately(prompt_img)
        img_data = fetch_image_bytes(english_prompt)

        if img_data:
            cap = f"🎨 *Prompt:* _{prompt_img}_\n✨ *Motor:* `FLUX HD Oficial`\n🩸 *SATANIC IA* • Criada por: *Raizel Mddz*"
            ok = send_multipart_file("sendPhoto", "photo", chat_id, img_data, "image.jpg", "image/jpeg", caption=cap, reply_to_id=msg_id)
            if ok:
                total_images_generated += 1
                return

        send_message(chat_id, "⚠️ O servidor de imagem está com alta demanda. Tente novamente em instantes.", reply_to_id=msg_id)
        return

    # ===================================================
    # 7. PAINEL DO CRIADOR (RAIZEL MDDZ)
    # ===================================================
    if text.startswith("/painel") or text.startswith("/admin"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso Restrito ao Criador.")
            return

        uptime = str(datetime.timedelta(seconds=int(time.time() - bot_start_time)))
        with memory_lock:
            total_users_count = len(user_profiles)
            in_ram_count = len(user_histories)
            active_model = active_models_pool[0] if active_models_pool else "Auto"

        painel_msg = (
            "👑 *PAINEL EXECUTIVO — SATANIC IA*\n\n"
            f"• *Criador:* Raizel Mddz\n"
            f"• *Uptime:* `{uptime}`\n"
            f"• *Modelo Ativo:* `{active_model}`\n\n"
            "📊 *Métricas em Tempo Real:*\n"
            f"• *Total de Usuários:* `{total_users_count}`\n"
            f"• *Conversas na RAM:* `{in_ram_count}`\n"
            f"• *Mensagens:* `{total_queries_processed}`\n"
            f"• *Imagens:* `{total_images_generated}`\n"
            f"• *Áudios de Voz:* `{total_voices_generated}`\n"
            f"• *Vídeos:* `{total_videos_generated}`\n\n"
            "🛠️ *Comandos de Gestão:*\n"
            "• `/usuarios` — Lista recente com Nick e ID\n"
            "• `/usuario <id>` — Ficha completa de um usuário\n"
            "• `/aviso <texto>` — Transmissão em massa para todos\n"
            "• `/limparcache` — Esvaziar RAM do servidor"
        )
        send_message(chat_id, painel_msg)
        return

    if text.startswith("/usuarios"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso restrito ao Criador.")
            return

        with memory_lock:
            if not user_profiles:
                send_message(chat_id, "Nenhum usuário registrado.")
                return

            linhas = ["👥 *USUÁRIOS REGISTRADOS:*\n"]
            itens = list(user_profiles.items())[-25:]
            for uid, info in itens:
                nick = f"@{info['username']}" if info['username'] != "Sem @" else "Sem nick"
                linhas.append(
                    f"• *Nome:* {info['name']} ({nick})\n"
                    f"  └ *ID:* `{uid}` | *Msgs:* {info['msg_count']} | *Visto:* {info['last_seen']}\n"
                )
            linhas.append(f"📌 *Total no banco:* {len(user_profiles)}")

        send_message(chat_id, "\n".join(linhas))
        return

    if text.startswith("/usuario"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso restrito ao Criador.")
            return

        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o ID: `/usuario 123456789`", reply_to_id=msg_id)
            return

        target_id = parts[1].strip()
        with memory_lock:
            info = user_profiles.get(target_id)

        if not info:
            send_message(chat_id, f"❌ Usuário `{target_id}` não encontrado.")
            return

        nick = f"@{info['username']}" if info['username'] != "Sem @" else "Sem @"
        detalhes = (
            f"🔍 *FICHA DO USUÁRIO — `{target_id}`*\n\n"
            f"• *Nome:* {info['name']}\n"
            f"• *Username:* {nick}\n"
            f"• *Mensagens:* {info['msg_count']}\n"
            f"• *Primeiro Acesso:* {info['first_seen']}\n"
            f"• *Última Atividade:* {info['last_seen']}"
        )
        send_message(chat_id, detalhes, reply_to_id=msg_id)
        return

    if text.startswith("/aviso") or text.startswith("/broadcast"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Apenas o Criador pode enviar avisos.")
            return

        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite a mensagem: `/aviso Olá a todos!`", reply_to_id=msg_id)
            return

        comunicado = parts[1].strip()
        send_message(chat_id, "📢 Iniciando envio em massa...")

        with memory_lock:
            destinatarios = list(user_profiles.keys())

        enviados = 0
        for uid in destinatarios:
            msg_formatada = (
                "📢 *COMUNICADO OFICIAL DO CRIADOR (Raizel Mddz)*\n\n"
                f"{comunicado}\n\n"
                "🩸 *SATANIC IA*"
            )
            try:
                res = telegram_call("sendMessage", {"chat_id": uid, "text": msg_formatada})
                if res and res.get("ok"):
                    enviados += 1
                time.sleep(0.05)
            except Exception:
                pass

        send_message(chat_id, f"✅ Entregue para *{enviados}* usuários!")
        return

    if text.startswith("/limparcache"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Apenas o Criador pode limpar o cache.")
            return

        with memory_lock:
            user_histories.clear()
            user_last_seen.clear()

        send_message(chat_id, "🧹 *Memória RAM esvaziada com sucesso!*")
        return

    # ===================================================
    # 8. CHAT DE TEXTO NORMAL (GEMINI)
    # ===================================================
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

    telegram_call("deleteWebhook", {"drop_pending_updates": True})
    discover_available_models()

    me = telegram_call("getMe")
    if not me or not me.get("ok"):
        logger.error("Falha ao autenticar com Telegram. Verifique seu BOT_TOKEN.")
        sys.exit(1)

    username = me.get("result", {}).get("username", "Desconhecido")
    logger.info(f"SATANIC IA online como @{username} | Criador: Raizel Mddz")

    # REGISTRA TODOS OS COMANDOS NO BOTÃO MENU DO TELEGRAM
    setup_telegram_commands_menu()

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

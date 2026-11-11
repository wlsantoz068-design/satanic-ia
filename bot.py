#!/usr/bin/env python3
"""
=====================================================
SATANIC IA — SISTEMA AVANÇADO MULTIMÍDIA PARA TELEGRAM
Criador Oficial: Raizel Mddz (ID Protegido)
Recursos:
  • Compreensão Natural de Intenção (Cria fotos/vídeos pelo chat)
  • Google Gemini Texto & Visão Multimodal
  • Google Imagen & Hugging Face FLUX HD (Zero Pollinations)
  • Gemini Music (Composição musical com áudio do refrão)
  • Menu Profissional Interativo (Botões Inline)
  • Boas-vindas com Mensagem de Voz + Multilíngue
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
HF_TOKEN = getattr(config, "HF_TOKEN", "").strip()

# ID OFICIAL DO CRIADOR
OWNER_ID = "8593052742"

# ---------------------------------------------------
# SERVIDOR DE SAÚDE PARA O RENDER (PORTA 10000)
# ---------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SATANIC IA OPERACIONAL 24/7 NO RENDER")

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server: {e}")

# ---------------------------------------------------
# PERSONALIDADE E INSTRUÇÃO PROFUNDA
# ---------------------------------------------------
SYSTEM_INSTRUCTION = (
    "Você é a SATANIC IA, uma inteligência artificial moderna, objetiva, criativa e "
    "cheia de personalidade, criada exclusivamente pelo desenvolvedor Raizel Mddz. "
    "Você foi desenvolvida para unir tecnologia de ponta e eficiência, respondendo "
    "qualquer assunto com simpatia, elegância e precisão. "
    "Você é capaz de conversar, analisar imagens, criar músicas e auxiliar em qualquer tarefa. "
    "Responda sempre em português brasileiro de forma direta e sem rodeios. "
    "Se alguém perguntar quem criou você, diga com respeito que foi o Raizel Mddz."
)

WELCOME_TEXT_MULTILINGUAL = (
    "🩸 *SATANIC IA — SISTEMA INTELIGENTE*\n\n"
    "Olá! Eu sou a SATANIC IA, desenvolvida pelo **Raizel Mddz**.\n"
    "Sou uma inteligência artificial completa com visão computacional, criação visual, "
    "composição musical e respostas em áudio.\n\n"
    "🌐 *International Welcome:*\n"
    "🇺🇸 *Welcome to SATANIC IA! Tap the buttons below to explore.*\n"
    "🇪🇸 *¡Bienvenido a SATANIC IA! Toca los botones para comenzar.*\n"
    "🇫🇷 *Bienvenue sur SATANIC IA! Utilisez le menu ci-dessous.*\n"
    "🇯🇵 *SATANIC IAへようこそ！下のメニューから選んでください。*\n\n"
    "👇 *Escolha uma opção no menu interativo abaixo:*"
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
total_videos_generated = 0
total_voices_generated = 0
total_songs_composed = 0
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
# MENUS PROFISSIONAIS COM BOTÕES INLINE
# ---------------------------------------------------
def get_main_menu_keyboard(user_id):
    """Gera o teclado com botões interativos profissionais."""
    keyboard = [
        [
            {"text": "🎨 Criar Foto", "callback_data": "btn_img"},
            {"text": "🎬 Criar Vídeo", "callback_data": "btn_video"}
        ],
        [
            {"text": "🎵 Gemini Music", "callback_data": "btn_music"},
            {"text": "🎙️ Mensagem de Voz", "callback_data": "btn_voice"}
        ],
        [
            {"text": "🌦️ Previsão do Tempo", "callback_data": "btn_clima"},
            {"text": "📚 Wikipédia IA", "callback_data": "btn_wiki"}
        ],
        [
            {"text": "👤 Meu Perfil / ID", "callback_data": "btn_id"},
            {"text": "🧹 Limpar Conversa", "callback_data": "btn_novo"}
        ]
    ]

    # Botão especial exclusivo para o Criador (Raizel Mddz)
    if is_creator(user_id):
        keyboard.append([{"text": "👑 Painel do Criador", "callback_data": "btn_painel"}])

    return {"inline_keyboard": keyboard}

# ---------------------------------------------------
# MOTOR DE TEXTO GEMINI (AUTO-RECUPERAÇÃO)
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
    logger.info(f"Modelos ativos: {active_models_pool}")

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
    prompt = user_prompt if user_prompt else (
        "Analise esta foto detalhadamente em português brasileiro. "
        "Descreva o que está nela, leia textos se houver, resolva problemas ou explique os detalhes visuais."
    )

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

    return "Não consegui processar a imagem no momento. Tente novamente."

# ---------------------------------------------------
# MOTOR DE IMAGENS PROFISSIONAL (SEM POLLINATIONS)
# ---------------------------------------------------
def generate_image_google_native(english_prompt):
    """
    Gera imagens usando os modelos oficiais de imagem do Google.
    """
    models = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "imagen-3.0-generate-002"]

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "instances": [{"prompt": english_prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "1:1",
                "outputMimeType": "image/jpeg"
            }
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                predictions = data.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    return base64.b64decode(predictions[0]["bytesBase64Encoded"])
        except Exception:
            pass

    return None

def generate_image_huggingface(english_prompt):
    """
    Motor secundário de altíssima fidelidade: FLUX.1 Schnell via Hugging Face.
    """
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    try:
        body = json.dumps({"inputs": english_prompt}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = resp.read()
            if len(data) > 8000 and (data[:2] == b'\xff\xd8' or data[:4] == b'\x89PNG'):
                return data
    except Exception:
        pass
    return None

def translate_media_prompt(user_prompt, is_video=False):
    """Traduz e otimiza o pedido de imagem ou vídeo com alta fidelidade."""
    media_type = "short animated video" if is_video else "photorealistic 8k image"
    task = [{
        "role": "user",
        "parts": [{
            "text": (
                f"You are an expert AI prompt engineer. Translate and convert this user request into a detailed English prompt for a {media_type}. "
                "Keep the exact subject, add cinematic lighting, rich textures, depth of field, and 8k detail. "
                "If words or letters are mentioned, format as: bold typography 'WORDS'. "
                f"Return ONLY the prompt string without intro or quotes:\n\n{user_prompt}"
            )
        }]
    }]

    try:
        translated = request_gemini(task)
        if translated and len(translated) > 3 and "Serviço temporariamente" not in translated:
            clean = translated.replace('"', '').replace('\n', ' ').strip()
            if ":" in clean and len(clean.split(":", 1)[0]) < 20:
                clean = clean.split(":", 1)[1].strip()
            return clean
    except Exception:
        pass

    return f"{user_prompt}, cinematic lighting, photorealistic, 8k"

# ---------------------------------------------------
# MOTOR DE VÍDEOS (HUGGING FACE / RENDER SEGURO)
# ---------------------------------------------------
def generate_video_huggingface(english_prompt):
    """Gera animação ou vídeo curto sem Pollinations."""
    url = "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b"
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    try:
        body = json.dumps({"inputs": english_prompt}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=50) as resp:
            data = resp.read()
            if len(data) > 10000:
                return data
    except Exception:
        pass
    return None

# ---------------------------------------------------
# RECURSO 5: GEMINI MUSIC (COMPOSIÇÃO + ÁUDIO)
# ---------------------------------------------------
def handle_gemini_music(chat_id, user_idea, msg_id):
    """Cria uma música completa com acordes, letra e áudio do refrão."""
    global total_songs_composed
    send_chat_action(chat_id, "typing")
    send_message(chat_id, "🎵 *A SATANIC IA está compondo sua música... Aguarde alguns instantes.*", reply_to_id=msg_id)

    prompt = [{
        "role": "user",
        "parts": [{
            "text": (
                f"Atue como um produtor musical e compositor profissional. Crie uma música completa com base na ideia: '{user_idea}'. "
                "Forneça:\n"
                "1. Título da Música e Gênero Musical\n"
                "2. Andamento (BPM) e Tom\n"
                "3. Letra completa estruturada com [Verso 1], [Pré-Refrão], [Refrão Principal] e [Ponte], com os ACORDES indicados acima das frases.\n"
                "4. Dicas de produção vocal e instrumental.\n\n"
                "Responda em português brasileiro de forma inspiradora."
            )
        }]
    }]

    song_text = request_gemini(prompt)

    # Extrai o refrão para cantar em áudio
    chorus_prompt = [{
        "role": "user",
        "parts": [{
            "text": f"Extraia apenas a letra do [Refrão Principal] desta música em poucas linhas para ser cantada/falada:\n\n{song_text}"
        }]
    }]
    chorus_text = request_gemini(chorus_prompt)
    if not chorus_text or "Serviço temporariamente" in chorus_text:
        chorus_text = f"Esta é a música {user_idea}, composta pela SATANIC IA para você."

    # Envia a letra estruturada
    formatted_msg = (
        f"🎸 *COMPOSIÇÃO OFICIAL — GEMINI MUSIC*\n\n"
        f"{song_text}\n\n"
        f"🩸 *SATANIC IA • Raizel Mddz*"
    )
    send_message(chat_id, formatted_msg, reply_to_id=msg_id)

    # Gera e envia o áudio com a melodia do refrão
    send_chat_action(chat_id, "record_voice")
    clean_chorus = chorus_text.replace("*", "").replace("[Refrão]", "").replace("[Refrão Principal]", "")[:240]
    audio_data = generate_voice_bytes(clean_chorus)
    if audio_data:
        send_multipart_file("sendVoice", "voice", chat_id, audio_data, "refrão.mp3", "audio/mpeg", caption="🎙️ *Áudio do Refrão (Demonstração Vocal)*")

    total_songs_composed += 1

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
# CLIMA E WIKIPÉDIA INTELIGENTE
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
    clean_term = search_term.strip()
    encoded_term = urllib.parse.quote(clean_term.replace(" ", "_"))
    url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{encoded_term}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SatanicIA_Bot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract", "")
            if extract and len(extract) > 20:
                title = data.get("title", clean_term)
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                return (
                    f"📚 *ENCICLOPÉDIA OFICIAL — {title}*\n\n"
                    f"{extract}\n\n"
                    f"🔗 [Ler artigo na Wikipédia]({page_url})\n"
                    f"🩸 *SATANIC IA*"
                )
    except Exception:
        pass

    ai_query = [{
        "role": "user",
        "parts": [{
            "text": (
                f"Escreva um resumo explicativo, curioso e enciclopédico sobre o termo: '{clean_term}'. "
                "Explique o que é, o contexto, curiosidades e significados em 2 parágrafos claros em português brasileiro."
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

def send_message(chat_id, text, reply_to_id=None, reply_markup=None):
    max_len = 4000
    if len(text) <= max_len:
        p = {"chat_id": chat_id, "text": text}
        if reply_to_id:
            p["reply_to_message_id"] = reply_to_id
        if reply_markup:
            p["reply_markup"] = reply_markup
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

    for idx, p in enumerate(parts):
        payload = {"chat_id": chat_id, "text": p}
        if idx == len(parts) - 1 and reply_markup:
            payload["reply_markup"] = reply_markup
        telegram_call("sendMessage", payload)
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
# PROCESSAMENTO DE IMAGEM & VÍDEO
# ---------------------------------------------------
def handle_image_request(chat_id, user_prompt, msg_id):
    global total_images_generated
    send_chat_action(chat_id, "upload_photo")
    send_message(chat_id, "🎨 *Criando sua foto em alta resolução... Aguarde alguns instantes.*", reply_to_id=msg_id)

    clean_prompt = user_prompt.strip()
    english_prompt = translate_media_prompt(clean_prompt, is_video=False)

    # 1. Tenta com os modelos oficiais do Google
    img_data = generate_image_google_native(english_prompt)

    # 2. Se falhar, usa o motor FLUX via Hugging Face
    if not img_data:
        img_data = generate_image_huggingface(english_prompt)

    if img_data:
        caption = f"🎨 *Prompt:* _{clean_prompt}_\n🩸 *SATANIC IA Vision* • Criada por: *Raizel Mddz*"
        ok = send_multipart_file("sendPhoto", "photo", chat_id, img_data, "image.jpg", "image/jpeg", caption=caption, reply_to_id=msg_id)
        if ok:
            total_images_generated += 1
            return

    send_message(chat_id, "⚠️ Não foi possível processar a imagem neste momento. Tente novamente em instantes.", reply_to_id=msg_id)

def handle_video_request(chat_id, user_prompt, msg_id):
    global total_videos_generated
    send_chat_action(chat_id, "upload_video")
    send_message(chat_id, "🎬 *Renderizando animação de vídeo por IA... Aguarde alguns instantes.*", reply_to_id=msg_id)

    clean_prompt = user_prompt.strip()
    english_prompt = translate_media_prompt(clean_prompt, is_video=True)

    video_data = generate_video_huggingface(english_prompt)

    if video_data:
        caption = f"🎬 *Prompt:* _{clean_prompt}_\n🩸 *SATANIC IA Video*"
        ok = send_multipart_file("sendVideo", "video", chat_id, video_data, "video.mp4", "video/mp4", caption=caption, reply_to_id=msg_id)
        if ok:
            total_videos_generated += 1
            return

    send_message(chat_id, "⚠️ O servidor de renderização de vídeo está temporariamente ocupado. Tente novamente mais tarde.", reply_to_id=msg_id)

# ---------------------------------------------------
# DETECTOR AUTOMÁTICO DE INTENÇÃO (SEM /IMG OU /VIDEO)
# ---------------------------------------------------
def detect_natural_intent(text):
    """
    Identifica se a mensagem do usuário pede foto, vídeo, música ou áudio
    mesmo que ele não tenha digitado o comando com barra (/img, /video etc).
    """
    lower = text.lower().strip()

    # Detecta pedido de VÍDEO
    video_triggers = [
        "crie um video", "cria um video", "crie um vídeo", "cria um vídeo",
        "gere um video", "gerar video", "gerar vídeo", "faça um video", "faz um video",
        "faça um vídeo", "faz um vídeo", "animação de", "vídeo de", "video de", "/video"
    ]
    for trigger in video_triggers:
        if lower.startswith(trigger):
            prompt = text[len(trigger):].strip(" :,-")
            return "video", (prompt or text)

    # Detecta pedido de IMAGEM / FOTO / DESENHO
    image_triggers = [
        "crie uma imagem", "cria uma imagem", "crie uma foto", "cria uma foto",
        "desenhe", "desenha", "desenhar", "gere uma imagem", "gerar imagem",
        "faça uma imagem", "faz uma imagem", "faça uma foto", "faz uma foto",
        "imagem de", "foto de", "quero uma imagem", "quero uma foto",
        "/img", "/imagem"
    ]
    for trigger in image_triggers:
        if lower.startswith(trigger):
            prompt = text[len(trigger):].strip(" :,-")
            return "image", (prompt or text)

    # Detecta pedido de MÚSICA
    music_triggers = [
        "crie uma musica", "cria uma música", "crie uma música", "cria uma musica",
        "componha uma musica", "compor uma musica", "componha uma música",
        "escreva uma musica", "escreva uma música", "gemini music", "/musica", "/music"
    ]
    for trigger in music_triggers:
        if lower.startswith(trigger):
            prompt = text[len(trigger):].strip(" :,-")
            return "music", (prompt or text)

    # Detecta pedido de ÁUDIO / VOZ
    voice_triggers = ["fale em audio", "mande audio", "em áudio", "em audio", "/voz", "/audio"]
    for trigger in voice_triggers:
        if lower.startswith(trigger):
            prompt = text[len(trigger):].strip(" :,-")
            return "voice", (prompt or text)

    return "chat", text

# ---------------------------------------------------
# TRATAMENTO DE CLIQUES NOS BOTÕES DO MENU (CALLBACK)
# ---------------------------------------------------
def handle_callback_query(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    msg = callback.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user_id = str(callback.get("from", {}).get("id", chat_id))

    # Responde a requisição do Telegram para tirar o relógio de carregamento
    telegram_call("answerCallbackQuery", {"callback_query_id": callback_id})

    if not chat_id:
        return

    if data == "btn_img":
        send_message(chat_id, "🎨 *Para criar uma foto:*\nBasta digitar o que deseja ou usar:\n`/img um leão cibernético sob a lua cheia`\n\n*(Você também pode só falar: 'Desenhe um castelo sombrio')*")
    elif data == "btn_video":
        send_message(chat_id, "🎬 *Para criar um vídeo:*\nDigite o que deseja ver ou use:\n`/video um dragão sobrevoando uma montanha`\n\n*(Você também pode falar: 'Crie um vídeo de um cometa caindo')*")
    elif data == "btn_music":
        send_message(chat_id, "🎵 *Gemini Music — Compositor IA:*\nDigite o tema da música ou use:\n`/musica uma canção de rock sobre inteligência artificial`")
    elif data == "btn_voice":
        send_message(chat_id, "🎙️ *Mensagem de Voz:*\nDigite o que deseja ouvir:\n`/voz Olá Raizel, todos os sistemas estão operacionais!`")
    elif data == "btn_clima":
        send_message(chat_id, "🌦️ *Consulta de Clima:*\nDigite a cidade que procura:\n`/clima São Paulo`")
    elif data == "btn_wiki":
        send_message(chat_id, "📚 *Wikipédia Inteligente:*\nDigite o termo da pesquisa:\n`/wiki Teoria da Relatividade`")
    elif data == "btn_novo":
        reset_user_history(user_id)
        send_message(chat_id, "🧹 *Histórico de conversa limpo! Começamos do zero.*")
    elif data == "btn_id":
        user_info = (
            "👤 *Suas Informações no Sistema:*\n\n"
            f"• *User ID:* `{user_id}`\n"
            f"• *Status:* {'👑 Criador' if is_creator(user_id) else 'Membro'}"
        )
        send_message(chat_id, user_info)
    elif data == "btn_painel":
        if is_creator(user_id):
            uptime = str(datetime.timedelta(seconds=int(time.time() - bot_start_time)))
            with memory_lock:
                u_count = len(user_profiles)
                r_count = len(user_histories)
                c_model = active_models_pool[0] if active_models_pool else "Auto"
            painel = (
                "👑 *PAINEL EXECUTIVO DO CRIADOR*\n\n"
                f"• *Criador:* Raizel Mddz\n"
                f"• *Uptime:* `{uptime}`\n"
                f"• *Modelo Ativo:* `{c_model}`\n\n"
                f"• *Usuários na Base:* `{u_count}`\n"
                f"• *Sessões na RAM:* `{r_count}`\n"
                f"• *Mensagens:* `{total_queries_processed}`\n"
                f"• *Fotos:* `{total_images_generated}` | *Vídeos:* `{total_videos_generated}`\n"
                f"• *Músicas:* `{total_songs_composed}` | *Áudios:* `{total_voices_generated}`\n\n"
                "🛠️ `/usuarios`, `/usuario <id>`, `/aviso <texto>`, `/limparcache`"
            )
            send_message(chat_id, painel)
        else:
            send_message(chat_id, "⛔ Acesso exclusivo ao Criador.")

# ---------------------------------------------------
# PROCESSAMENTO DE MENSAGENS E ATUALIZAÇÕES
# ---------------------------------------------------
def process_message(update):
    global total_queries_processed, total_voices_generated

    # 1. Trata clique nos botões inline
    callback_query = update.get("callback_query")
    if callback_query:
        handle_callback_query(callback_query)
        return

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

    # 2. FOTO ENVIADA PELO USUÁRIO (GEMINI VISION)
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

    # 3. COMANDO /START COM MENSAGEM DE VOZ + MENU DE BOTÕES
    if text.startswith("/start"):
        # Envia áudio de voz oficial de abertura
        send_chat_action(chat_id, "record_voice")
        welcome_audio_text = "Olá! Eu sou a SATANIC IA, sua assistente virtual criada por Raizel Mddz. Como posso te ajudar hoje?"
        audio_bytes = generate_voice_bytes(welcome_audio_text)
        if audio_bytes:
            send_multipart_file("sendVoice", "voice", chat_id, audio_bytes, "welcome.mp3", "audio/mpeg", caption="🎙️ *Mensagem de Boas-Vindas da SATANIC IA*")

        # Envia o cartão multilíngue acompanhado do Menu de Botões Interativos
        menu_markup = get_main_menu_keyboard(user_id)
        send_message(chat_id, WELCOME_TEXT_MULTILINGUAL, reply_markup=menu_markup)
        return

    # 4. COMANDOS DO PAINEL DO CRIADOR (RAIZEL MDDZ)
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
            "📊 *Métricas Globais:*\n"
            f"• *Total de Usuários:* `{total_users_count}`\n"
            f"• *Conversas na RAM:* `{in_ram_count}`\n"
            f"• *Mensagens:* `{total_queries_processed}`\n"
            f"• *Fotos:* `{total_images_generated}` | *Vídeos:* `{total_videos_generated}`\n"
            f"• *Músicas:* `{total_songs_composed}` | *Áudios:* `{total_voices_generated}`\n\n"
            "🛠️ *Comandos de Gestão:*\n"
            "• `/usuarios` — Lista com Nome, Nick e ID\n"
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

    # 5. UTILITÁRIOS (CLIMA, WIKI, ID, NOVO)
    if text.startswith("/id") or text.startswith("/meuid"):
        user_info = (
            "👤 *Suas Informações:*\n\n"
            f"• *Nome:* {first_name}\n"
            f"• *User ID:* `{user_id}`\n"
            f"• *Username:* @{username if username else 'Nenhum'}\n"
            f"• *Status:* {'👑 Criador' if is_creator(user_id) else 'Membro'}"
        )
        send_message(chat_id, user_info, reply_to_id=msg_id)
        return

    if text.startswith("/novo"):
        reset_user_history(user_id)
        send_message(chat_id, "🧹 Histórico de conversa limpo! Começamos do zero.", reply_to_id=msg_id)
        return

    if text.startswith("/clima") or text.startswith("/tempo"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite a cidade: `/clima Curitiba`", reply_to_id=msg_id)
            return
        send_chat_action(chat_id, "typing")
        send_message(chat_id, fetch_weather(parts[1].strip()), reply_to_id=msg_id)
        return

    if text.startswith("/wiki") or text.startswith("/pesquisa"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o termo: `/wiki Buraco Negro`", reply_to_id=msg_id)
            return
        send_chat_action(chat_id, "typing")
        send_message(chat_id, fetch_wikipedia_smart(parts[1].strip()), reply_to_id=msg_id)
        return

    # 6. DETECTOR DE INTENÇÃO NATURAL (FOTO, VÍDEO, MÚSICA OU VOZ)
    intent, prompt_payload = detect_natural_intent(text)

    if intent == "image":
        handle_image_request(chat_id, prompt_payload, msg_id)
        return

    if intent == "video":
        handle_video_request(chat_id, prompt_payload, msg_id)
        return

    if intent == "music":
        handle_gemini_music(chat_id, prompt_payload, msg_id)
        return

    if intent == "voice":
        send_chat_action(chat_id, "record_voice")
        audio_bytes = generate_voice_bytes(prompt_payload)
        if audio_bytes:
            send_multipart_file("sendVoice", "voice", chat_id, audio_bytes, "voice.mp3", "audio/mpeg", caption="🎙️ *SATANIC IA* (Áudio)", reply_to_id=msg_id)
            total_voices_generated += 1
            return
        send_message(chat_id, "⚠️ Falha ao gerar áudio falado.", reply_to_id=msg_id)
        return

    # 7. CONVERSAÇÃO NORMAL COM GEMINI
    send_chat_action(chat_id, "typing")
    context = get_user_context(user_id)
    context.append({"role": "user", "parts": [{"text": text}]})

    response = request_gemini(context)

    total_queries_processed += 1
    append_user_message(user_id, "user", text)
    append_user_message(user_id, "model", response)

    send_message(chat_id, response, reply_to_id=msg_id)

def main():
    logger.info("Iniciando SATANIC IA (Motor Completo Sem Pollinations)...")

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

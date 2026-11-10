#!/usr/bin/env python3
"""
=====================================================
SATANIC IA — BOT INTELIGENTE PARA TELEGRAM
Criador: Raizel Mddz
Segurança: Reconhecimento Silencioso de Criador (Sem vazar ID)
Mapeamento: Banco de Usuários (Nome, Nick, ID)
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

# ID SILENCIOSO DO CRIADOR (NUNCA É EXIBIDO NAS RESPOSTAS)
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

# ---------------------------------------------------
# PERSONALIDADE E TEXTOS PÚBLICOS (SEM DADOS PRIVADOS)
# ---------------------------------------------------
SYSTEM_INSTRUCTION = (
    "Você é a SATANIC IA, uma inteligência artificial moderna, objetiva e cheia de "
    "personalidade, criada exclusivamente pelo desenvolvedor Raizel Mddz. "
    "Você foi desenvolvida para unir tecnologia de ponta e eficiência, tornando a vida "
    "das pessoas mais fácil e explicando assuntos complexos de forma simples e acessível, "
    "sempre com um toque de elegância, simpatia e confiança. "
    "Você responde sempre em português brasileiro. "
    "Se alguém perguntar quem criou você, responda apenas que foi o Raizel Mddz. "
    "Nunca mencione identificadores numéricos, dados confidenciais ou códigos internos."
)

WELCOME_MESSAGE_USER = (
    "🩸 SATANIC IA\n\n"
    "Olá! Eu sou a SATANIC IA, fui criada pelo **Raizel Mddz**.\n\n"
    "Sou uma inteligência artificial moderna, objetiva e cheia de personalidade, "
    "desenvolvida para unir tecnologia de ponta e eficiência. Estou aqui para tornar a "
    "sua vida mais fácil, explicar assuntos complexos de forma simples e ajudar no que você "
    "precisar, sempre com um toque de elegância e simpatia.\n\n"
    "Como posso te ajudar hoje? 🔥\n\n"
    "📌 Comandos:\n"
    "/img [descrição] — Gerar imagem realista com FLUX HD\n"
    "/id — Ver suas próprias informações de usuário\n"
    "/novo — Começar uma conversa do zero\n"
    "/status — Ver o estado do bot\n"
    "/ajuda — Ver lista de comandos"
)

WELCOME_MESSAGE_CREATOR = (
    "🩸 *SATANIC IA — MODO CRIADOR ATIVADO*\n\n"
    "Bem-vindo de volta, **Raizel Mddz**! 👑\n"
    "Reconhecimento biométrico efetuado com sucesso em segundo plano.\n\n"
    "🛠️ *Seu Menu de Controle:*\n"
    "• /painel — Ver estatísticas e métricas do sistema\n"
    "• /usuarios — Ver lista de usuários com Nick e ID\n"
    "• /usuario <id> — Ver ficha detalhada de um usuário\n"
    "• /aviso <texto> — Transmissão em massa para todos\n"
    "• /limparcache — Esvaziar RAM do servidor\n\n"
    "Estou pronta para qualquer comando, Mestre."
)

HELP_MESSAGE = (
    "🩸 *Comandos Disponíveis — SATANIC IA:*\n\n"
    "• /img <descrição> — Gera imagens fiéis e realistas em alta definição.\n"
    "  _Exemplo:_ `/img um lobo cibernético com olhos vermelhos sob a névoa`\n"
    "• /id — Exibe seu nome, @username e seu ID de usuário.\n"
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
# Banco em memória que mapeia: { user_id: { "name": ..., "username": ..., "msgs": ... } }
user_profiles = {}

bot_start_time = time.time()
total_queries_processed = 0
total_images_generated = 0
active_models_pool = []

def is_creator(user_id):
    """Compara o ID de forma totalmente oculta."""
    return str(user_id).strip() == OWNER_ID

def register_user_profile(user_id, first_name, username):
    """Atualiza a ficha de perfil do usuário no banco."""
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
        # Mantém atualizado caso o usuário mude de nome ou nick
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
# MOTOR DE TEXTO GEMINI
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
# TRADUTOR DE PROMPT PARA IMAGEM
# ---------------------------------------------------
def translate_prompt_accurately(user_prompt):
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
# MOTOR DE IMAGENS FLUX HD
# ---------------------------------------------------
def fetch_image_bytes(english_prompt):
    encoded = urllib.parse.quote(english_prompt)
    seed = random.randint(10000, 9999999)
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
            logger.warning(f"Tentativa com [{mod}] falhou: {type(e).__name__}.")
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
    english_prompt = translate_prompt_accurately(clean_prompt)
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

# ---------------------------------------------------
# PROCESSAMENTO DE MENSAGENS E SEGURANÇA
# ---------------------------------------------------
def process_message(update):
    global total_queries_processed
    msg = update.get("message")
    if not msg:
        return

    text = msg.get("text", "").strip()
    chat_id = msg.get("chat", {}).get("id")
    user_id = str(msg.get("from", {}).get("id", chat_id))
    first_name = msg.get("from", {}).get("first_name", "Usuário")
    username = msg.get("from", {}).get("username", "")
    msg_id = msg.get("message_id")

    if not text or not chat_id:
        return

    # Registra o perfil do usuário de forma automática
    register_user_profile(user_id, first_name, username)

    logger.info(f"Mensagem de {user_id} (@{username or 'sem_nick'}): {text}")

    # ===================================================
    # BLOCO 1: COMANDOS GERAIS
    # ===================================================
    if text.startswith("/start"):
        if is_creator(user_id):
            send_message(chat_id, WELCOME_MESSAGE_CREATOR)
        else:
            send_message(chat_id, WELCOME_MESSAGE_USER)
        return

    # Comando para o usuário conferir suas próprias informações
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
            f"• *Imagens:* `{total_images_generated}`"
        )
        send_message(chat_id, status_text)
        return

    # ===================================================
    # BLOCO 2: PAINEL EXCLUSIVO DO CRIADOR (RAIZEL MDDZ)
    # ===================================================
    if text.startswith("/painel") or text.startswith("/admin"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ *Acesso Restrito.* Comando exclusivo do Criador.")
            return

        uptime = str(datetime.timedelta(seconds=int(time.time() - bot_start_time)))
        with memory_lock:
            total_users_count = len(user_profiles)
            in_ram_count = len(user_histories)
            current_model = active_models_pool[0] if active_models_pool else "Auto"

        painel_msg = (
            "👑 *PAINEL EXECUTIVO DO CRIADOR — SATANIC IA*\n\n"
            f"• *Mestre:* Raizel Mddz\n"
            f"• *Servidor:* Render 24/7 Ativo 🟢\n"
            f"• *Uptime:* `{uptime}`\n"
            f"• *Modelo Ativo:* `{current_model}`\n\n"
            "📊 *Métricas da Base:*\n"
            f"• *Total de Usuários Registrados:* `{total_users_count}`\n"
            f"• *Conversas em Memória RAM:* `{in_ram_count}`\n"
            f"• *Mensagens Respondidas:* `{total_queries_processed}`\n"
            f"• *Imagens Geradas:* `{total_images_generated}`\n\n"
            "🛠️ *Ferramentas do Mestre:*\n"
            "• `/usuarios` — Lista usuários com Nome, Nick e ID\n"
            "• `/usuario <id>` — Ver histórico de um usuário específico\n"
            "• `/aviso <texto>` — Transmissão em massa para todos\n"
            "• `/limparcache` — Esvaziar RAM do servidor"
        )
        send_message(chat_id, painel_msg)
        return

    # Comando: Lista todos os usuários com Nome, Nick e ID
    if text.startswith("/usuarios"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso restrito ao Criador.")
            return

        with memory_lock:
            if not user_profiles:
                send_message(chat_id, "Nenhum usuário registrado ainda.")
                return

            linhas = ["👥 *LISTA DE USUÁRIOS REGISTRADOS:*\n"]
            # Exibe os últimos 25 usuários para não estourar a mensagem
            itens = list(user_profiles.items())[-25:]
            for uid, info in itens:
                nick = f"@{info['username']}" if info['username'] != "Sem @" else "Sem nick"
                linhas.append(
                    f"• *Nome:* {info['name']} ({nick})\n"
                    f"  └ *ID:* `{uid}` | *Msgs:* {info['msg_count']} | *Visto:* {info['last_seen']}\n"
                )

            total_u = len(user_profiles)
            linhas.append(f"📌 *Total cadastrado no banco:* {total_u}")

        send_message(chat_id, "\n".join(linhas))
        return

    # Comando: Puxa detalhes de um usuário específico pelo ID
    if text.startswith("/usuario"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso restrito ao Criador.")
            return

        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o ID desejado: `/usuario 123456789`", reply_to_id=msg_id)
            return

        target_id = parts[1].strip()
        with memory_lock:
            info = user_profiles.get(target_id)

        if not info:
            send_message(chat_id, f"❌ Usuário com ID `{target_id}` não foi localizado no banco de dados.")
            return

        nick = f"@{info['username']}" if info['username'] != "Sem @" else "Sem @"
        detalhes = (
            f"🔍 *FICHA DO USUÁRIO — `{target_id}`*\n\n"
            f"• *Nome:* {info['name']}\n"
            f"• *Username:* {nick}\n"
            f"• *Total de Interações:* {info['msg_count']} mensagens\n"
            f"• *Primeiro Acesso:* {info['first_seen']}\n"
            f"• *Última Atividade:* {info['last_seen']}"
        )
        send_message(chat_id, detalhes, reply_to_id=msg_id)
        return

    # Transmissão Global (Broadcast)
    if text.startswith("/aviso") or text.startswith("/broadcast"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso restrito ao Criador.")
            return

        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite a mensagem: `/aviso Olá a todos!`", reply_to_id=msg_id)
            return

        comunicado = parts[1].strip()
        send_message(chat_id, "📢 Iniciando disparo em massa para todos os usuários...")

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

        send_message(chat_id, f"✅ Comunicado entregue com sucesso para *{enviados}* usuários!")
        return

    # Limpeza de Cache de Memória
    if text.startswith("/limparcache"):
        if not is_creator(user_id):
            send_message(chat_id, "⛔ Acesso restrito ao Criador.")
            return

        with memory_lock:
            user_histories.clear()
            user_last_seen.clear()

        send_message(chat_id, "🧹 *Memória RAM esvaziada com sucesso!*")
        return

    # ===================================================
    # BLOCO 3: GERAÇÃO DE IMAGENS E CHAT NORMAL
    # ===================================================
    if text.startswith("/img") or text.startswith("/imagem"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_message(chat_id, "⚠️ Digite o prompt: `/img logotipo 3d com o nome SATANIC IA`", reply_to_id=msg_id)
            return
        handle_image_generation(chat_id, parts[1].strip(), msg_id)
        return

    # Diálogo de texto normal com o Gemini
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
    logger.info(f"SATANIC IA online como @{username} | Criador: Raizel Mddz")

    # Mensagem silenciosa e discreta no seu privado confirmando que ela subiu
    try:
        telegram_call("sendMessage", {
            "chat_id": OWNER_ID,
            "text": "👑 *SATANIC IA ONLINE!* Reconhecimento de Criador ativo e pronto para suas ordens, Raizel Mddz."
        })
    except Exception:
        pass

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

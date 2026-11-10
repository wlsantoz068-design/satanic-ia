#!/usr/bin/env python3
"""
=====================================================
SATANIC IA — BOT INTELIGENTE PARA TELEGRAM
Criador: Raizel Mddz
Texto: Google Gemini API
Imagens: FLUX HD Oficial (Fidelidade ao Prompt + Binário)
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

# ---------------------------------------------------
# PERSONALIDADE E MENSAGENS PERSONALIZADAS
# ---------------------------------------------------
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
                    discovere

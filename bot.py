#!/usr/bin/env python3
"""
=====================================================
SATANIC IA — BOT INTELIGENTE PARA TELEGRAM
Texto: Google Gemini API
Imagens: FLUX Realism HD + Gemini Prompt Enhancer
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
    "Você é a SATANIC IA, uma assistente virtual inteligente, educada, moderna, "
    "objetiva e criativa. Você responde sempre em português brasileiro de forma clara, "
    "sendo capaz de explicar assuntos difíceis de maneira simples. "
    "Mantenha um tom solícito, confiante e amigável."
)

WELCOME_MESSAGE = (
    "🩸 SATANIC IA\n\n"
    "Olá! Eu sou a SATANIC IA, sua assistente com inteligência do Google Gemini e gerador de imagens ultra-realistas FLUX HD. 🔥\n\n"
    "📌 Comandos:\n"
    "/img [descrição] — Gerar imagem realista em alta definição\n"
    "/novo — Começar uma conversa do zero\n"
    "/status — Ver o estado do bot\n"
    "/ajuda — Ver lista de comandos"
)

HELP_MESSAGE = (
    "🩸 *Comandos Disponíveis:*\n\n"
    "• /img <descrição> — Gera imagens hiper-realistas com FLUX HD.\n"
    "  _Exemplo:_ `/img um lobo sombrio com olhos vermelhos sob névoa`\n"
    "• /start — Iniciar o assistente\n"
    "• /novo — Limpar memória e histórico\n"
    "• /status — Ver o status e uptime do bot\n"
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
        except Exception:
            continue

    return "Serviço temporariamente indisponível. Repita a pergunta em instantes."

# ---------------------------------------------------
# OTIMIZADOR DE PROMPT COM GEMINI (TURBO PROMPT)
# ---------------------------------------------------
def enhance_prompt_with_gemini(user_prompt):
    """
    Usa o Gemini para converter o prompt do usuário em uma descrição
    cinematográfica rica em detalhes em inglês, elevando a imagem para o nível Midjourney.
    """
    prompt_engineer_task = [
        {
            "role": "user",
            "parts": [{
                "text": (
                    "Act as an elite AI image prompt engineer (Midjourney and FLUX style). "
                    "Convert the following user idea into a single, highly detailed, photorealistic prompt in English. "
                    "Add dramatic cinematic lighting, camera perspective, realistic textures, atmosphere, and 8k detail. "
                    "Return ONLY the prompt string. Do not use quotes, explanations, or introductory text.\n\n"
                    f"User idea: {user_prompt}"
                )
            }]
        }
    ]

    try:
        model_to_use = active_models_pool[0] if active_models_pool else "gemini-flash-latest"
        success, enhanced = call_gemini_endpoint(model_to_use, prompt_engineer_task)
        if success and enhanced and len(enhanced) > 10:
            cleaned = enhanced.replace('"', '').replace('\n', ' ').strip()
            logger.info(f"Prompt turbinado pelo Gemini: {cleaned[:80]}...")
            return cleaned
    except Exception as e:
        logger.warning(f"Falha ao otimizar prompt com Gemini: {e}")

    # Fallback caso falhe
    return f"masterpiece, highly detailed, photorealisti

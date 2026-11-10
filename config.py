import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "SEU_TOKEN_DO_TELEGRAM")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "SUA_CHAVE_GEMINI")

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
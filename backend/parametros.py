import os
from dotenv import load_dotenv

load_dotenv()

GENAI_KEY = os.getenv("GENAI_KEY", "")

GEMINI_MODEL_RESUMEN = os.getenv("GEMINI_MODEL_RESUMEN", "gemini-2.0-flash")
GEMINI_MODEL_PLAN = os.getenv("GEMINI_MODEL_PLAN", "gemini-2.5-flash")

ZONA_HORARIA = os.getenv("ZONA_HORARIA", "America/Santiago")

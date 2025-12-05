import os
from dotenv import load_dotenv

load_dotenv()

GENAI_KEY = os.getenv("GENAI_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ZONA_HORARIA = os.getenv("ZONA_HORARIA", "America/Santiago")

import json
import time
from typing import Dict, Any

from google import genai
from google.genai import errors as genai_errors
from gen_calendar import generar_ics_desde_plan

from parametros import GENAI_KEY, GEMINI_MODEL, ZONA_HORARIA
from modelos import PlanEstudio


def _esquema_salida_textual() -> str:
    return f"""
{{
  "curso": {{
    "nombre": "string",
    "codigo": "string | null",
    "semestre": "string | null"
  }},
  "configuracion": {{
    "fecha_inicio": "DD-MM-YYYY",
    "fecha_fin": "DD-MM-YYYY",
    "zona_horaria": "{ZONA_HORARIA}",
    "intensidad": "suave | normal | intensa"
  }},
  "resumen": {{
    "estrategia": "string",
    "riesgos": ["string"]
  }},
  "semanas": [
    {{
      "numero": 1,
      "rango_fechas": {{
        "inicio": "DD-MM-YYYY",
        "fin": "DD-MM-YYYY"
      }},
      "objetivos": ["string"],
      "contenidos": ["string"],
      "evaluaciones_cercanas": [
        {{
          "nombre": "string",
          "fecha": "DD-MM-YYYY",
          "tipo": "control | tarea | certamen | examen | otro",
          "ponderacion": 0.2
        }}
      ],
      "sesiones": [
        {{
          "id": "W01-S01",
          "titulo": "string",
          "fecha": "DD-MM-YYYY",
          "inicio": "HH:MM",
          "fin": "HH:MM",
          "duracion_minutos": 90,
          "tipo": "teoria | ejercicios | repaso | evaluacion | proyecto",
          "temas": ["string"],
          "output": "string",
          "prioridad": 1
        }}
      ]
    }}
  ]
}}
""".strip()


def construir_prompt_plan(payload_entrada: Dict[str, Any]) -> str:
    esquema = _esquema_salida_textual()

    return f"""
Eres un planificador académico experto.

OBJETIVO:
Generar un plan de estudio semestral realista basado en:
- programa del curso
- apuntes
- evaluaciones conocidas
- disponibilidad del estudiante

INSTRUCCIONES CRÍTICAS:
- Devuelve SOLO un JSON válido.
- Sin markdown, sin explicación, sin texto extra.
- Respeta EXACTAMENTE esta estructura:

{esquema}

REGLAS:
- Fechas en formato DD-MM-YYYY.
- Horas en formato HH:MM (24h).
- Zona horaria: {ZONA_HORARIA}.
- No inventes evaluaciones nuevas si no aparecen en el programa o en evaluaciones conocidas.
- Genera sesiones dentro de los bloques de disponibilidad.
- Prioridad de las sesiones entre 1 y 3 (1 = alta, 3 = baja).
- Si falta un dato, usa null o listas vacías.

DATOS DE ENTRADA (JSON):
{json.dumps(payload_entrada, ensure_ascii=False)}
""".strip()


def _normalizar_prioridades(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gemini a veces devuelve prioridad 0 u otros valores fuera de 1-3.
    Esta limpieza evita que Pydantic falle al validar.
    """
    for semana in plan.get("semanas", []):
        for sesion in semana.get("sesiones", []):
            prioridad = sesion.get("prioridad", 1)
            try:
                prioridad_int = int(prioridad)
            except (TypeError, ValueError):
                prioridad_int = 1
            sesion["prioridad"] = max(1, min(3, prioridad_int))
    return plan


def _llamar_modelo_con_reintentos(cliente: genai.Client, prompt: str, max_intentos: int = 3, espera_inicial: float = 2.0):
    """Reintenta la llamada si el modelo está sobrecargado (503)."""
    espera = espera_inicial
    for intento in range(1, max_intentos + 1):
        try:
            return cliente.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                # config={"response_mime_type": "application/json"}
            )
        except genai_errors.ServerError as e:
            msg = str(e).lower()
            if e.status_code == 503 or "overloaded" in msg:
                if intento == max_intentos:
                    raise
                time.sleep(espera)
                espera *= 2
                continue
            raise


def llamar_gemini_para_plan(payload_entrada: Dict[str, Any]) -> PlanEstudio:
    cliente = genai.Client(api_key=GENAI_KEY)

    prompt = construir_prompt_plan(payload_entrada)

    # Opción A: llamada con reintentos básicos ante 503 (modelo sobrecargado)
    respuesta = _llamar_modelo_con_reintentos(cliente, prompt)

    texto = (respuesta.text or "").strip()

    # Limpieza defensiva mínima por si el modelo mete algo raro
    # (en hackatón esto te salva)
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        # si venía con "json\n{...}"
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    json_plan = _normalizar_prioridades(json.loads(texto))
    plan_validado = PlanEstudio(**json_plan)
    return plan_validado

def generar_plan_y_ics(payload_entrada):
    plan = llamar_gemini_para_plan(payload_entrada)
    ics_str = generar_ics_desde_plan(plan)
    return plan, ics_str

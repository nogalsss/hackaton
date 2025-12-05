import base64
import io
import json
import time
from typing import Dict, Any, List, Tuple

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
- No inventes unidades que no esten en el programa; si apuntes traen temas nuevos, usalos solo como refuerzo.
- Genera sesiones dentro de los bloques de disponibilidad.
- Prioridad de las sesiones entre 1 y 3 (1 = alta, 3 = baja).
- Cada sesion debe tener fecha, inicio y fin obligatorios.
- Si faltan evaluaciones, solo planea por unidades/temas.
- Prioriza mas horas en unidades/temas dificiles.
- En intensidad normal deja al menos 1 sesion comodin por semana.
- Si falta un dato, usa null o listas vacias.

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


def _normalizar_duraciones(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Acota duracion_minutos a un rango razonable para evitar errores de validación.
    """
    for semana in plan.get("semanas", []):
        for sesion in semana.get("sesiones", []):
            dur = sesion.get("duracion_minutos", 60)
            try:
                dur_int = int(dur)
            except (TypeError, ValueError):
                dur_int = 60
            sesion["duracion_minutos"] = max(30, min(240, dur_int))
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


def validar_payload(payload: Dict[str, Any]) -> None:
    """
    Chequeo rapido para no llamar al modelo con datos incompletos.
    """
    errores = []
    curso = payload.get("curso", {})
    semestre = payload.get("semestre", {})
    disponibilidad = payload.get("disponibilidad", {})
    tiene_texto = bool(payload.get("texto_programa")) or bool(payload.get("textos_apuntes")) or bool(payload.get("entradas"))
    if not curso.get("nombre"):
        errores.append("Falta curso.nombre")
    if not semestre:
        errores.append("Falta semestre")
    if not disponibilidad.get("bloques"):
        errores.append("Falta disponibilidad.bloques")
    if not tiene_texto:
        errores.append("Falta texto_programa o entradas")
    if errores:
        raise ValueError(" | ".join(errores))


def separar_entradas(entradas: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Divide entradas en programa y apuntes para tratarlos distinto.
    """
    programa: List[Dict[str, Any]] = []
    apuntes: List[Dict[str, Any]] = []
    for entrada in entradas:
        if entrada.get("tipo") == "programa":
            programa.append(entrada)
        else:
            apuntes.append(entrada)
    return programa, apuntes


def extraer_texto_pdf_base64(contenido_base64: str) -> str:
    """
    Extrae texto de un PDF en base64 usando PyPDF2 si esta disponible.
    Si falla, devuelve cadena vacia.
    """
    try:
        data = base64.b64decode(contenido_base64)
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        textos = []
        for page in reader.pages:
            try:
                textos.append((page.extract_text() or "").strip())
            except Exception:
                continue
        return "\n".join([t for t in textos if t])
    except Exception:
        return ""


def ocr_imagen_base64(contenido_base64: str) -> str:
    """
    OCR basico: intenta con Pillow + pytesseract si estan instalados.
    Si no, devuelve cadena vacia.
    """
    try:
        data = base64.b64decode(contenido_base64)
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
        with io.BytesIO(data) as bio:
            img = Image.open(bio)
            return pytesseract.image_to_string(img).strip()
    except Exception:
        return ""


def extraer_texto_de_entrada(entrada: Dict[str, Any]) -> str:
    """
    Router de entrada multimodal a texto.
    """
    formato = (entrada.get("formato") or "").lower()
    contenido = entrada.get("contenido_base64", "")
    if not contenido:
        return ""
    if formato == "texto":
        try:
            return base64.b64decode(contenido).decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
    if formato == "pdf":
        return extraer_texto_pdf_base64(contenido)
    if formato == "imagen":
        return ocr_imagen_base64(contenido)
    return ""


def llamar_gemini_para_plan(payload_entrada: Dict[str, Any]) -> PlanEstudio:
    cliente = genai.Client(api_key=GENAI_KEY)

    prompt = construir_prompt_plan(payload_entrada)

    # Opción A: llamada con reintentos básicos ante 503 (modelo sobrecargado)
    try:
        respuesta = _llamar_modelo_con_reintentos(cliente, prompt)
    except Exception:
        data_demo = {
            "curso": {
                "nombre": payload_entrada.get("curso", {}).get("nombre", "Curso"),
                "codigo": payload_entrada.get("curso", {}).get("codigo"),
                "semestre": None
            },
            "configuracion": {
                "fecha_inicio": payload_entrada.get("semestre", {}).get("fecha_inicio", "01-01-2026"),
                "fecha_fin": payload_entrada.get("semestre", {}).get("fecha_fin", "01-06-2026"),
                "zona_horaria": ZONA_HORARIA,
                "intensidad": payload_entrada.get("intensidad", "normal")
            },
            "resumen": {"estrategia": "Plan demo de respaldo.", "riesgos": []},
            "semanas": []
        }
        return PlanEstudio(**data_demo)

    texto = (respuesta.text or "").strip()

    # Limpieza defensiva mínima por si el modelo mete algo raro
    # (en hackatón esto te salva)
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        # si venía con "json\n{...}"
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    json_crudo = json.loads(texto)
    json_crudo = _normalizar_prioridades(json_crudo)
    json_crudo = _normalizar_duraciones(json_crudo)
    plan_validado = PlanEstudio(**json_crudo)
    return plan_validado

def generar_plan_y_ics(payload_entrada):
    validar_payload(payload_entrada)
    plan = llamar_gemini_para_plan(payload_entrada)
    ics_str = generar_ics_desde_plan(plan)
    return plan, ics_str


def generar_plan_y_ics_multimodal(payload_entrada: Dict[str, Any]):
    """
    Flujo completo para entradas multimodales (pdf/imagen/texto en base64).
    Devuelve (PlanEstudio, string .ics).
    """
    validar_payload(payload_entrada)

    entradas = payload_entrada.get("entradas", []) or []
    programa_entradas, apuntes_entradas = separar_entradas(entradas)

    textos_programa = [extraer_texto_de_entrada(e) for e in programa_entradas]
    textos_apuntes = [extraer_texto_de_entrada(e) for e in apuntes_entradas]

    texto_programa = "\n\n".join([t for t in textos_programa if t])
    textos_apuntes = [t for t in textos_apuntes if t]

    payload_ia = {
        "curso": payload_entrada.get("curso", {}),
        "semestre": payload_entrada.get("semestre", {}),
        "disponibilidad": payload_entrada.get("disponibilidad", {}),
        "evaluaciones_conocidas": payload_entrada.get("evaluaciones_conocidas", []),
        "texto_programa": texto_programa,
        "textos_apuntes": textos_apuntes,
        "intensidad": payload_entrada.get("intensidad", "normal")
    }

    plan = llamar_gemini_para_plan(payload_ia)
    ics_str = generar_ics_desde_plan(plan)
    return plan, ics_str

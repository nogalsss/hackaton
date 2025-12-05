import base64
import io
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List


from google import genai
from google.genai import errors as genai_errors

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

from gen_calendar import generar_ics_desde_plan
from parametros import GENAI_KEY, GEMINI_MODEL_RESUMEN, GEMINI_MODEL_PLAN, ZONA_HORARIA
from modelos import PlanEstudio
MODO_DEMO = True


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


def _recortar_texto(texto: str, max_chars: int) -> str:
    return "" if not texto else texto[:max_chars]


def _recortar_lista_textos(textos: List[str], max_por_texto: int, max_total: int) -> List[str]:
    out, total = [], 0
    for t in textos:
        if not t:
            continue
        t_rec = _recortar_texto(t, max_por_texto)
        if total + len(t_rec) > max_total:
            t_rec = t_rec[: max_total - total]
        if t_rec:
            out.append(t_rec)
            total += len(t_rec)
        if total >= max_total:
            break
    return out


def _normalizar_fecha(fecha_str: str) -> str:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(fecha_str, fmt).strftime("%d-%m-%Y")
        except ValueError:
            pass
    return ""


def extraer_info_programa(texto: str) -> Dict[str, Any]:
    fechas_raw = re.findall(
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
        texto or ""
    )
    fechas = [_normalizar_fecha(f) for f in fechas_raw]
    fechas = [f for f in fechas if f]

    fechas_unique = sorted(set(fechas), key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    semestre = {}
    if len(fechas_unique) >= 2:
        semestre = {"fecha_inicio": fechas_unique[0], "fecha_fin": fechas_unique[-1]}

    evaluaciones = []
    for linea in (texto or "").splitlines():
        lower = linea.lower()
        fechas_linea = re.findall(
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
            linea
        )
        if not fechas_linea:
            continue

        tipo = (
            "certamen" if "certamen" in lower else
            "examen" if "examen" in lower else
            "control" if "control" in lower else
            "tarea" if "tarea" in lower else
            None
        )
        if not tipo:
            continue

        fecha_eval = _normalizar_fecha(fechas_linea[0])
        if not fecha_eval:
            continue

        ponderacion = None
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", linea)
        if m:
            try:
                ponderacion = float(m.group(1).replace(",", ".")) / 100.0
            except ValueError:
                pass

        evaluaciones.append({
            "nombre": linea.strip()[:50] or tipo,
            "fecha": fecha_eval,
            "tipo": tipo,
            "ponderacion": ponderacion
        })

    return {"semestre": semestre, "evaluaciones": evaluaciones}


def _decode_base64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(b64)


def extraer_texto_pdf_base64(b64: str) -> str:
    if PyPDF2 is None:
        return ""
    try:
        data = _decode_base64_to_bytes(b64)
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join([(p.extract_text() or "").strip() for p in reader.pages if p])
    except Exception:
        return ""


def ocr_imagen_base64(b64: str) -> str:
    if Image is None or pytesseract is None:
        return ""
    try:
        data = _decode_base64_to_bytes(b64)
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img).strip()
    except Exception:
        return ""


def extraer_texto_de_entrada(entrada: Dict[str, Any]) -> str:
    formato = (entrada.get("formato") or "").lower()
    b64 = entrada.get("contenido_base64", "")
    if not b64:
        return ""

    if formato == "texto":
        try:
            return _decode_base64_to_bytes(b64).decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
    if formato == "pdf":
        return extraer_texto_pdf_base64(b64)
    if formato == "imagen":
        return ocr_imagen_base64(b64)

    return ""


def _clasificar_entradas_auto(entradas: List[Dict[str, Any]], textos: List[str]) -> List[Dict[str, Any]]:
    if not entradas:
        return entradas

    keys = ("programa", "syllabus", "enunciado", "program")
    program_idx = None

    for i, e in enumerate(entradas):
        if e.get("tipo"):
            continue
        nombre = (e.get("nombre") or "").lower()
        if any(k in nombre for k in keys):
            program_idx = i
            break

    if program_idx is None:
        program_idx = max(range(len(textos)), key=lambda i: len(textos[i] or ""), default=0)

    for i, e in enumerate(entradas):
        if not e.get("tipo"):
            e["tipo"] = "programa" if i == program_idx else "apunte"

    return entradas


def intensidad_desde_estado_animo(estado: str) -> str:
    estado = (estado or "").lower()
    return "suave" if estado == "cansado" else "intensa" if estado == "motivado" else "normal"


def _clasificar_estado_animo_desde_texto(texto: str) -> str:
    if not texto or not texto.strip():
        return "normal"

    cliente = genai.Client(api_key=GENAI_KEY)
    prompt = (
        "Clasifica el siguiente texto en: cansado, normal, motivado. "
        "Responde solo una palabra.\n"
        f"Texto: {texto.strip()}"
    )
    try:
        resp = cliente.models.generate_content(model=GEMINI_MODEL_RESUMEN, contents=prompt)
        s = (resp.text or "").strip().lower()
        if "cansado" in s:
            return "cansado"
        if "motivado" in s:
            return "motivado"
        return "normal"
    except Exception:
        return "normal"


def validar_payload(payload: Dict[str, Any]) -> None:
    errores = []
    curso = payload.get("curso", {})
    disponibilidad = payload.get("disponibilidad", {})

    tiene_texto = bool(payload.get("texto_programa")) or bool(payload.get("textos_apuntes"))
    tiene_entradas = bool(payload.get("entradas"))

    if not curso.get("nombre"):
        errores.append("Falta curso.nombre")
    if not disponibilidad.get("bloques"):
        errores.append("Falta disponibilidad.bloques")
    if not tiene_texto and not tiene_entradas:
        errores.append("Falta texto_programa/textos_apuntes o entradas")

    if errores:
        raise ValueError(" | ".join(errores))


def _normalizar_prioridades(plan: Dict[str, Any]) -> Dict[str, Any]:
    for semana in plan.get("semanas", []):
        for sesion in semana.get("sesiones", []):
            try:
                p = int(sesion.get("prioridad", 1))
            except (TypeError, ValueError):
                p = 1
            sesion["prioridad"] = max(1, min(3, p))
    return plan


def _normalizar_duraciones(plan: Dict[str, Any]) -> Dict[str, Any]:
    for semana in plan.get("semanas", []):
        for sesion in semana.get("sesiones", []):
            try:
                d = int(sesion.get("duracion_minutos", 60))
            except (TypeError, ValueError):
                d = 60
            sesion["duracion_minutos"] = max(30, min(240, d))
    return plan


def _payload_para_prompt(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "curso": payload.get("curso", {}),
        "semestre": payload.get("semestre", {}),
        "disponibilidad": payload.get("disponibilidad", {}),
        "evaluaciones_conocidas": payload.get("evaluaciones_conocidas", []) or [],
        "intensidad": payload.get("intensidad", "normal"),
        "estado_animo": payload.get("estado_animo"),
        "texto_programa": payload.get("texto_programa", ""),
        "textos_apuntes": payload.get("textos_apuntes", []) or [],
    }


def construir_prompt_plan(payload: Dict[str, Any]) -> str:
    esquema = _esquema_salida_textual()
    data = _payload_para_prompt(payload)

    return f"""
Eres un planificador académico experto.
Devuelve SOLO un JSON válido, sin markdown ni texto extra.
Respeta EXACTAMENTE esta estructura:

{esquema}

Reglas:
- Fechas DD-MM-YYYY, horas HH:MM.
- Zona horaria: {ZONA_HORARIA}.
- No inventes evaluaciones nuevas.
- Usa apuntes solo como refuerzo del programa.
- Genera sesiones dentro de los bloques de disponibilidad.
- Prioridad entre 1 y 3.
- Si falta un dato, usa null o listas vacías.

Datos de entrada (JSON):
{json.dumps(data, ensure_ascii=False)}
""".strip()


def _llamar_modelo_con_reintentos(
    cliente: genai.Client,
    modelo: str,
    prompt: str,
    max_intentos: int = 2 if MODO_DEMO else 3,
    espera_inicial: float = 1.0 if MODO_DEMO else 2.0
):
    espera = espera_inicial
    for intento in range(1, max_intentos + 1):
        try:
            return cliente.models.generate_content(model=modelo, contents=prompt)
        except genai_errors.ClientError as e:
            msg = str(e).lower()
            status = getattr(e, "status_code", None) or getattr(e, "code", None)
            if status == 429 or "resource_exhausted" in msg:
                if intento == max_intentos:
                    raise
                time.sleep(espera)
                espera *= 2
                continue
            raise
        except genai_errors.ServerError as e:
            msg = str(e).lower()
            if getattr(e, "status_code", None) == 503 or "overloaded" in msg:
                if intento == max_intentos:
                    raise
                time.sleep(espera)
                espera *= 2
                continue
            raise

def _resumir_texto(cliente: genai.Client, texto: str, etiqueta: str, max_chars: int = 1200) -> str:
    if not texto:
        return ""

    # Si ya es corto, no gastamos llamada
    umbral = 1200 if not MODO_DEMO else 900
    if len(texto) <= umbral:
        return _recortar_texto(texto, max_chars)

    prompt = (
        f"Resume el siguiente {etiqueta} en puntos clave muy concisos. "
        f"Prioriza: unidades/temas, orden sugerido, evaluaciones si aparecen "
        f"y pistas de dificultad. "
        f"Máximo {max_chars} caracteres. "
        f"Responde solo texto.\n\n"
        f"TEXTO:\n{texto}"
    )
    try:
        resp = _llamar_modelo_con_reintentos(cliente, GEMINI_MODEL_RESUMEN, prompt)
        return _recortar_texto((resp.text or "").strip(), max_chars)
    except Exception:
        return _recortar_texto(texto, max_chars)


def llamar_gemini_para_plan(payload: Dict[str, Any]) -> PlanEstudio:
    cliente = genai.Client(api_key=GENAI_KEY)
    prompt = construir_prompt_plan(payload)

    try:
        resp = _llamar_modelo_con_reintentos(cliente, GEMINI_MODEL_PLAN, prompt)
    except Exception:
        data_demo = {
            "curso": {
                "nombre": payload.get("curso", {}).get("nombre", "Curso"),
                "codigo": payload.get("curso", {}).get("codigo"),
                "semestre": None
            },
            "configuracion": {
                "fecha_inicio": payload.get("semestre", {}).get("fecha_inicio", "01-01-2026"),
                "fecha_fin": payload.get("semestre", {}).get("fecha_fin", "01-06-2026"),
                "zona_horaria": ZONA_HORARIA,
                "intensidad": payload.get("intensidad", "normal")
            },
            "resumen": {"estrategia": "Plan demo de respaldo.", "riesgos": []},
            "semanas": []
        }
        return PlanEstudio(**data_demo)

    texto = (resp.text or "").strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    data = json.loads(texto)
    data = _normalizar_prioridades(_normalizar_duraciones(data))
    return PlanEstudio(**data)


def generar_plan_y_ics(payload: Dict[str, Any]):
    validar_payload(payload)
    plan = llamar_gemini_para_plan(payload)
    return plan, generar_ics_desde_plan(plan)


def generar_plan_y_ics_multimodal(payload_entrada: Dict[str, Any]):
    validar_payload(payload_entrada)
    payload = dict(payload_entrada)

    if payload.get("estado_animo_texto") and not payload.get("estado_animo"):
        payload["estado_animo"] = _clasificar_estado_animo_desde_texto(payload["estado_animo_texto"])

    if not payload.get("intensidad"):
        payload["intensidad"] = intensidad_desde_estado_animo(payload.get("estado_animo"))

    entradas = [dict(e) for e in (payload.get("entradas", []) or [])]
    textos_todos = [extraer_texto_de_entrada(e) for e in entradas]
    entradas = _clasificar_entradas_auto(entradas, textos_todos)

    textos_programa = [t for e, t in zip(entradas, textos_todos) if e.get("tipo") == "programa"]
    textos_apuntes = [t for e, t in zip(entradas, textos_todos) if e.get("tipo") != "programa"]

    texto_programa = "\n\n".join([t for t in textos_programa if t])
    textos_apuntes = [t for t in textos_apuntes if t]

    # Recortes (mas agresivos en demo)
    if MODO_DEMO:
        texto_programa = _recortar_texto(texto_programa, 2000)
        textos_apuntes = _recortar_lista_textos(textos_apuntes, 1000, 2500)
    else:
        texto_programa = _recortar_texto(texto_programa, 4000)
        textos_apuntes = _recortar_lista_textos(textos_apuntes, 2000, 6000)

    info = extraer_info_programa(texto_programa)
    semestre = payload.get("semestre", {}) or {}

    if info.get("semestre"):
        semestre.setdefault("fecha_inicio", info["semestre"].get("fecha_inicio"))
        semestre.setdefault("fecha_fin", info["semestre"].get("fecha_fin"))

    if semestre.get("fecha_fin") and not semestre.get("fecha_inicio"):
        semestre["fecha_inicio"] = datetime.now().strftime("%d-%m-%Y")

    if not semestre.get("fecha_inicio") and not semestre.get("fecha_fin"):
        hoy = datetime.now()
        semestre["fecha_inicio"] = hoy.strftime("%d-%m-%Y")
        semestre["fecha_fin"] = (hoy + timedelta(days=120)).strftime("%d-%m-%Y")

    evaluaciones = payload.get("evaluaciones_conocidas", []) or []
    if not evaluaciones and info.get("evaluaciones"):
        evaluaciones = info["evaluaciones"]

    cliente = genai.Client(api_key=GENAI_KEY)

    # En demo: 1 solo resumen combinado = 1 llamada menos
    if MODO_DEMO:
        material = texto_programa + "\n\nAPUNTES:\n" + "\n\n".join(textos_apuntes)
        resumen_total = _resumir_texto(cliente, material, "material del curso", max_chars=1200)

        payload_ia = {
            "curso": payload.get("curso", {}),
            "semestre": semestre,
            "disponibilidad": payload.get("disponibilidad", {}),
            "evaluaciones_conocidas": evaluaciones,
            "texto_programa": resumen_total or texto_programa,
            "textos_apuntes": [],
            "intensidad": payload.get("intensidad", "normal"),
            "estado_animo": payload.get("estado_animo"),
        }
    else:
        resumen_programa = _resumir_texto(cliente, texto_programa, "programa", max_chars=800)
        resumen_apuntes = _resumir_texto(cliente, "\n\n".join(textos_apuntes), "apuntes", max_chars=800)

        payload_ia = {
            "curso": payload.get("curso", {}),
            "semestre": semestre,
            "disponibilidad": payload.get("disponibilidad", {}),
            "evaluaciones_conocidas": evaluaciones,
            "texto_programa": resumen_programa or texto_programa,
            "textos_apuntes": [resumen_apuntes] if resumen_apuntes else textos_apuntes,
            "intensidad": payload.get("intensidad", "normal"),
            "estado_animo": payload.get("estado_animo"),
        }

    plan = llamar_gemini_para_plan(payload_ia)
    ics_str = generar_ics_desde_plan(plan)
    return plan, ics_str

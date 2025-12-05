import base64
import json
from pathlib import Path

from backend.planificador import generar_plan_y_ics_multimodal


def _b64_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _pick_files(base_dir: Path):
    """
    Toma los ejemplos locales en la raíz del proyecto para armar el payload.
    Prioriza archivos que contengan 'programa' como programa, y otro PDF como apunte.
    """
    program = None
    apunte = None
    for pdf in base_dir.glob("*.pdf"):
        lower = pdf.name.lower()
        if "programa" in lower and program is None:
            program = pdf
        elif apunte is None:
            apunte = pdf
    return program, apunte


def main():
    base_dir = Path(__file__).resolve().parent.parent
    archivo_programa, archivo_apunte = _pick_files(base_dir)

    if not archivo_programa or not archivo_apunte:
        raise FileNotFoundError("No se encontraron PDFs en la raíz para programa/apunte.")

    entrada_programa = {
        "tipo": "programa",
        "formato": "pdf",
        "nombre": archivo_programa.name,
        "contenido_base64": _b64_file(archivo_programa),
    }
    entrada_apunte = {
        "tipo": "apunte",
        "formato": "pdf",
        "nombre": archivo_apunte.name,
        "contenido_base64": _b64_file(archivo_apunte),
    }

    payload = {
        "curso": {"nombre": "Calculo I", "codigo": "MAT1610"},
        "semestre": {},
        "disponibilidad": {
            "zona_horaria": "America/Santiago",
            "bloques": [
                {"dia": "lunes", "inicio": "19:00", "fin": "21:00"},
                {"dia": "miercoles", "inicio": "19:00", "fin": "21:00"},
                {"dia": "sabado", "inicio": "10:00", "fin": "13:00"},
            ],
        },
        "evaluaciones_conocidas": [],
        "estado_animo_texto": "Dormí poco pero estoy motivado para preparar el certamen.",
        "entradas": [entrada_programa, entrada_apunte],
    }

    plan, ics_str = generar_plan_y_ics_multimodal(payload)

    with open("plan_estudio.ics", "w", encoding="utf-8") as f:
        f.write(ics_str)

    print("Plan validado y .ics generado.")
    print("Semanas generadas:", len(plan.semanas))
    print("Resumen JSON:\n", json.dumps(plan.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from datetime import datetime
from typing import List

from parametros import ZONA_HORARIA
from modelos import PlanEstudio


def _dt_ical(fecha: str, hora: str) -> str:
    """
    Convierte fecha y hora a formato iCal.
    Acepta fechas DD-MM-YYYY o YYYY-MM-DD; el modelo a veces devuelve ISO.
    """
    formatos_fecha = ["%d-%m-%Y", "%Y-%m-%d"]
    for fmt in formatos_fecha:
        try:
            dt = datetime.strptime(f"{fecha} {hora}", f"{fmt} %H:%M")
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Formato de fecha no soportado: {fecha}")
    return dt.strftime("%d%m%YT%H%M%S")

def generar_ics_desde_plan(plan: PlanEstudio) -> str:
    lineas: List[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Organizador Academico IA//ES//",
        "CALSCALE:GREGORIAN"
    ]

    uid_contador = 0

    for semana in plan.semanas:
        for sesion in semana.sesiones:
            uid_contador += 1
            dtstart = _dt_ical(sesion.fecha, sesion.inicio)
            dtend = _dt_ical(sesion.fecha, sesion.fin)

            resumen = sesion.titulo or "Sesion de estudio"
            descripcion = ""
            if sesion.temas:
                descripcion += "Temas: " + ", ".join(sesion.temas) + "\\n"
            if sesion.output:
                descripcion += "Objetivo: " + sesion.output
            uid = sesion.id or f"W{semana.numero:02d}-S{uid_contador:02d}"

            lineas.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}@organizador-ia",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
                f"DTSTART;TZID={ZONA_HORARIA}:{dtstart}",
                f"DTEND;TZID={ZONA_HORARIA}:{dtend}",
                f"SUMMARY:{resumen}",
                f"DESCRIPTION:{descripcion}",
                "END:VEVENT"
            ])

    lineas.append("END:VCALENDAR")
    return "\n".join(lineas)

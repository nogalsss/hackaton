from planificador import llamar_gemini_para_plan
from gen_calendar import generar_ics_desde_plan

payload = {
    "curso": {"nombre": "Cálculo I", "codigo": "MAT1610"},
    "semestre": {"fecha_inicio": "09-03-2026", "fecha_fin": "10-07-2026"},
    "disponibilidad": {
        "zona_horaria": "America/Santiago",
        "bloques": [
            {"dia": "lunes", "inicio": "19:00", "fin": "21:00"},
            {"dia": "miercoles", "inicio": "19:00", "fin": "21:00"},
            {"dia": "sabado", "inicio": "10:00", "fin": "13:00"}
        ]
    },
    "evaluaciones_conocidas": [
        {"nombre": "I1", "fecha": "10-04-2026", "tipo": "certamen", "ponderacion": 0.25}
    ],
    "texto_programa": "Unidad 1: Límites... Unidad 2: Derivadas...",
    "textos_apuntes": ["Apunte 1...", "Apunte 2..."],
    "intensidad": "normal"
}

plan = llamar_gemini_para_plan(payload)

contenido_ics = generar_ics_desde_plan(plan)

with open("plan_estudio.ics", "w", encoding="utf-8") as f:
    f.write(contenido_ics)

print("Plan validado y .ics generado ✅")

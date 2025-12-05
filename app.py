import streamlit as st # type: ignore
import requests
import re
from datetime import datetime, timedelta

def procesador_ics(contenido_ics_raw: str) -> str:

    lineas = contenido_ics_raw.splitlines()
    lineas_corregidas = []
    
    lineas = [line for line in lineas if not line.startswith(('VERSION:', 'PRODID:'))]
    

    lineas_corregidas.append('BEGIN:VCALENDAR')
    lineas_corregidas.append('VERSION:2.0')
    lineas_corregidas.append('PRODID:-//TuAppOrganizadorUC//EN')

    # Bandera para saber si estamos dentro de un VEVENT y guardar la última DTSTART
    dentro_evento = False
    ultima_dtstart_value = None 
    
    # --- 2. CORRECCIÓN DE EVENTOS Y FECHAS ---
    
    for linea in lineas:
        
        # Inicia VEVENT
        if linea.strip() == 'BEGIN:VEVENT':
            dentro_evento = True
            ultima_dtstart_value = None
            lineas_corregidas.append(linea)
            continue
            
        # Fin VEVENT
        elif linea.strip() == 'END:VEVENT':
            # 3. CORRECCIÓN DE DTEND FALTANTE
            # Solo aplica la corrección si se encontró un DTSTART con VALUE=DATE (Evento de día completo)
            if dentro_evento and ultima_dtstart_value and 'VALUE=DATE' in ultima_dtstart_value: 
                
                # Extrae la fecha (Ej: 20250801)
                fecha_str = ultima_dtstart_value.split(':')[-1]
                
                try:
                    # Convierte la fecha y suma un día para DTEND
                    fecha_inicio = datetime.strptime(fecha_str, '%Y%m%d') 
                    fecha_fin = fecha_inicio + timedelta(days=1)
                    fecha_fin_str = fecha_fin.strftime('%Y%m%d')
                    
                    # Añade la línea DTEND corregida
                    lineas_corregidas.append(f'DTEND;VALUE=DATE:{fecha_fin_str}')
                except ValueError:
                    # Si falla la conversión (fecha inválida), ignora la corrección de DTEND
                    pass 
            
            dentro_evento = False
            lineas_corregidas.append(linea)
            continue

        # 2. CORRECCIÓN DE DTSTART (01AUG25 -> AAAAMMDD)
        if linea.startswith('DTSTART') and dentro_evento:
            
            # Detecta el formato no estándar (DDMESAA)
            match_date = re.search(r'VALUE=DATE:(\d{2}[A-Z]{3}\d{2})', linea)
            
            if match_date:
                fecha_vieja = match_date.group(1) # Ej: 01AUG25
                try:
                    # Convierte la fecha vieja (01AUG25) a AAAAMMDD (20250801)
                    fecha_obj = datetime.strptime(fecha_vieja, '%d%b%y') 
                    fecha_nueva = fecha_obj.strftime('%Y%m%d')
                    
                    # Reemplaza la línea DTSTART completa
                    linea_corregida = linea.replace(fecha_vieja, fecha_nueva)
                    lineas_corregidas.append(linea_corregida)
                    ultima_dtstart_value = linea_corregida # Guarda para usar en DTEND
                    continue
                except ValueError:
                    # Si falla, simplemente usa la línea original
                    pass
            
            # Si no hubo corrección o es un formato válido (como DTSTART:20251101T100000Z)
            ultima_dtstart_value = linea
            lineas_corregidas.append(linea)
            continue

        # Si no es un VEVENT, DTSTART, DTEND, simplemente lo agrega
        lineas_corregidas.append(linea)
    
    # Asegura que el archivo termina correctamente
    if 'END:VCALENDAR' not in lineas_corregidas[-1]:
        lineas_corregidas.append('END:VCALENDAR')
        
    return "\n".join(lineas_corregidas)

def descargar_y_procesar_canvas(url_canvas: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        st.info(f"Conectando a Canvas... ({url_canvas[:50]}...)")
        
        response = requests.get(url_canvas, timeout=15)
        response.raise_for_status() 
        
        contenido_ics_raw = response.text
        ics_corregido = procesador_ics(contenido_ics_raw) 
        
        return ics_corregido
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la URL de Canvas. Verifica el enlace. Detalle: {e}")
        return ""
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al procesar. Detalle: {e}")
        return ""



st.title("✨ Organizador de Estudio UC - Sincronización Canvas")

url_canvas_input = st.text_input(
    "Pega aquí el Vínculo del Feed del Calendario de Canvas:",
    placeholder="Ej: https://cursos.canvas.uc.cl/feeds/calendars/user_XXXXXXX.ics"
)

texto_ics_final_corregido = "" 

if url_canvas_input:
    texto_ics_final_corregido = descargar_y_procesar_canvas(url_canvas_input)
    
    if texto_ics_final_corregido:
        st.success("¡Sincronización exitosa! Archivo ICS corregido generado.")

        # Aquí iría el Render Plan (análisis de fechas y bloques de estudio)
        # st.subheader("Resumen de Pruebas y Bloques de Estudio Generados:")
        # ...

        # Botón export .ics
        st.download_button(
            label="✅ Descargar ICS Corregido para Google Calendar",
            data=texto_ics_final_corregido,
            file_name='canvas_organizador_corregido.ics',
            mime='text/calendar'
        )
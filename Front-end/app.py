# type:ignore
from usuarios import init_users_table, create_user, get_user, update_user
from onboarding import (
    init_onboarding_table,
    save_onboarding, get_onboarding,
    update_availability, update_mood,
    save_daily_mood, get_daily_mood,
    init_daily_mood_table, init_weekly_availability_table,
)
from cursos import get_all_courses
from datetime import date
import sys
import base64
from pathlib import Path

import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.planificador import generar_plan_y_ics_multimodal

# --------- setup inicial ----------
st.set_page_config(page_title="SmartSemester – Demo login", page_icon="📚")
# --------- estilos globales ----------
st.markdown(
    """
    <style>
    /* Más espacio horizontal en el contenido principal */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    /* Aumentar ancho de la sidebar */
    [data-testid="stSidebar"] {
        min-width: 330px !important;  /* antes se ve a ~250px */
        max-width: 350px !important;
    }

    /* Más espacio entre secciones de la sidebar */
    .sidebar-section {
        margin-bottom: 1.8rem;
    }

    /* Ajustar radio y tamaño de botones de la sidebar */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.5rem;
    }

    /* Alinear mejor los títulos */
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h2 {
        margin-top: 0.8rem;
    }


    /* Un poquito más redondeados los botones */
    .stButton > button {
        border-radius: 999px;
        padding: 0.35rem 1.2rem;
        font-weight: 500;
    }

    /* Cards reutilizables */
    .section-card {
        background-color: transparent;      /* sin bloque oscuro */
        border-radius: 0;                   /* sin esquinas redondeadas grandes */
        padding: 0.5rem 0 1.2rem 0;         /* poco padding arriba/abajo */
        border-bottom: 1px solid #1f2937;   /* solo una línea separadora abajo */
        margin-bottom: 1.5rem;              /* espacio hacia la siguiente sección */
    }


    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }

    .section-subtitle {
        font-size: 0.9rem;
        color: #9ca3af;
        margin-bottom: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Crear tablas si no existen
init_users_table()
init_onboarding_table()

init_daily_mood_table()
init_weekly_availability_table()

# Estado global de sesión
if "user" not in st.session_state:
    st.session_state["user"] = None  # aquí guardaremos un dict con id, username, email

if "screen" not in st.session_state:
    st.session_state["screen"] = "login"  # "login", "register", "onboarding", "dashboard"


# --------- helpers de UI ----------
def _archivo_a_entrada(uploaded_file, tipo_sugerido=None):
    ext = uploaded_file.name.split(".")[-1].lower()
    data = uploaded_file.getvalue()
    b64 = base64.b64encode(data).decode("utf-8")
    if ext == "pdf":
        formato = "pdf"
    elif ext in ("png", "jpg", "jpeg"):
        formato = "imagen"
    else:
        formato = "texto"
    return {
        "tipo": tipo_sugerido,
        "formato": formato,
        "nombre": uploaded_file.name,
        "contenido_base64": b64,
    }


def _mood_a_estado_animo(mood_str: str) -> str:
    mood_str = (mood_str or "").lower()
    if "mal" in mood_str or "😞" in mood_str:
        return "cansado"
    if "motivad" in mood_str or "😁" in mood_str:
        return "motivado"
    return "normal"


def _dias_a_bloques(disponibilidad_str: str):
    if not disponibilidad_str:
        return []
    mapa = {
        "lunes": "lunes",
        "martes": "martes",
        "miércoles": "miercoles",
        "miercoles": "miercoles",
        "jueves": "jueves",
        "viernes": "viernes",
        "sábado": "sabado",
        "sabado": "sabado",
        "domingo": "domingo",
    }
    dias = [d.strip().lower() for d in disponibilidad_str.split(",") if d.strip()]
    bloques = []
    for d in dias:
        dd = mapa.get(d)
        if not dd:
            continue
        bloques.append({"dia": dd, "inicio": "19:00", "fin": "21:00"})
    return bloques

def plan_a_parrafos_simple(plan):
    if not plan:
        return "No hay plan disponible."

    if isinstance(plan, list):
        sesiones = plan
    elif isinstance(plan, dict):
        # ordenar por clave numérica si aplica
        def clave_orden(k):
            try:
                return int(k)
            except:
                return 10**9
        sesiones = [plan[k] for k in sorted(plan.keys(), key=clave_orden)]
    else:
        return str(plan)

    out = []
    for i, s in enumerate(sesiones, start=1):
        if not isinstance(s, dict):
            continue

        titulo = s.get("titulo", f"Sesión {i}")
        fecha = s.get("fecha", "fecha no definida")
        inicio = s.get("inicio", "")
        fin = s.get("fin", "")
        tipo = s.get("tipo", "sesión")
        temas = s.get("temas", [])
        output = s.get("output", "")

        temas_txt = ", ".join(temas) if isinstance(temas, list) else str(temas)
        hora_txt = f" de {inicio} a {fin}" if inicio or fin else ""

        parrafo = (
            f"En la **sesión {i}** trabajaremos **{titulo}** el día **{fecha}**{hora_txt}. "
            f"Será una sesión de tipo **{tipo}**. "
            f"Los temas principales serán: {temas_txt if temas_txt else 'no especificados'}. "
            f"El objetivo es: {output if output else 'no especificado'}."
        )
        out.append(parrafo)

    return "\n\n".join(out)


def go_to(screen_name: str):
    st.session_state["screen"] = screen_name


def logout():
    st.session_state["user"] = None
    st.session_state["screen"] = "login"
    st.rerun()

# --------- sidebar ----------
with st.sidebar:
    st.title("SmartSemester 🤓")

    if st.session_state["user"]:
        user = st.session_state["user"]

        # HEADER USER
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.write(f"Sesión iniciada como **{user['username']}**")
        if user.get("email"):
            st.caption(user["email"])
        colA, colB = st.columns(2)
        with colA:
            if st.button("Editar usuario"):
                st.session_state["screen"] = "edit_user"
        with colB:
            if st.button("Cerrar sesión"):
                logout()
        st.markdown("</div>", unsafe_allow_html=True)


        data = get_onboarding(user["id"])

        # ====== SEMANA ACTUAL ======
        if data:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.subheader("📅 Semana actual")

            disponibilidad = data["availability"] or ""
            st.write(f"**Días disponibles:** {disponibilidad or 'No definido'}")

            # Estado del desplegable
            if "sidebar_edit_avail" not in st.session_state:
                st.session_state["sidebar_edit_avail"] = False

            if not st.session_state["sidebar_edit_avail"]:
                if st.button("✏️ Editar disponibilidad", key="btn_sidebar_edit"):
                    st.session_state["sidebar_edit_avail"] = True
            else:
                dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
                dias_actuales = [d.strip() for d in disponibilidad.split(",") if d.strip()]

                nueva_disponibilidad = st.multiselect(
                    "¿Qué días puedes estudiar esta semana?",
                    dias_semana,
                    default=dias_actuales,
                    key="sidebar_disp",
                )

                col_guardar, col_cancelar = st.columns(2)
                with col_guardar:
                    if st.button("Guardar", key="sidebar_disp_btn"):
                        if not nueva_disponibilidad:
                            st.warning("Selecciona al menos un día 🤓")
                        else:
                            update_availability(user["id"], ",".join(nueva_disponibilidad))
                            st.success("Disponibilidad actualizada ✅")
                            st.session_state["sidebar_edit_avail"] = False
                            st.rerun()

                with col_cancelar:
                    if st.button("Cancelar", key="sidebar_disp_cancel"):
                        st.session_state["sidebar_edit_avail"] = False
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


            # ====== MOOD HOY ======
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.subheader("🙂 Mood de hoy")

            mood_opciones = ["😞 Mal", "😐 Meh", "🙂 Bien", "😁 Motivadísimo"]
            mood_hoy_guardado = get_daily_mood(user["id"])
            mood_inicial = mood_hoy_guardado or data["mood"]
            idx = mood_opciones.index(mood_inicial) if mood_inicial in mood_opciones else 2

            mood_hoy = st.radio(
                "¿Cómo te sientes hoy?",
                mood_opciones,
                index=idx,
                key="sidebar_mood",
            )

            if st.button("Guardar mood de hoy", key="sidebar_mood_btn"):
                save_daily_mood(user["id"], mood_hoy)
                update_mood(user["id"], mood_hoy)
                st.success("Mood guardado 😊")
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("Completa tu onboarding para configurar tu semana 🙂")

    else:
        st.write("No has iniciado sesión todavía.")
        st.button("Iniciar sesión", on_click=go_to, args=("login",))
        st.button("Registrarse", on_click=go_to, args=("register",))


# --------- pantallas principales ----------
def login_screen():
    st.header("Iniciar sesión")

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        user_row = get_user(username, password)
        if user_row:
            # Guardamos datos mínimos del usuario en session_state
            st.session_state["user"] = {
                "id": user_row["id"],
                "username": user_row["username"],
                "email": user_row["email"],
            }

            # Decidir siguiente pantalla según si ya tiene onboarding o no
            onboard_data = get_onboarding(user_row["id"])
            if onboard_data:
                st.session_state["screen"] = "dashboard"
            else:
                st.session_state["screen"] = "onboarding"

            # Opcional: podríamos poner un success, pero no se verá porque rerun
            # st.success("¡Sesión iniciada! 🎉")

            # 🔁 Forzar que se vuelva a ejecutar todo el script
            st.rerun()

        else:
            st.error("Usuario o contraseña incorrectos.")



def register_screen():
    st.header("Crear una cuenta")

    with st.form("register_form"):
        username = st.text_input("Elige un usuario")
        email = st.text_input("Correo (opcional)")
        password = st.text_input("Contraseña", type="password")
        password2 = st.text_input("Repite la contraseña", type="password")
        submitted = st.form_submit_button("Registrarme")

    if submitted:
        if not username or not password:
            st.warning("El usuario y la contraseña son obligatorios.")
            return

        if password != password2:
            st.warning("Las contraseñas no coinciden.")
            return

        ok, error = create_user(username, email, password)
        if ok:
            st.success("Cuenta creada 🎉 Ahora puedes iniciar sesión.")
            go_to("login")
        else:
            st.error(error or "No se pudo crear el usuario.")


def onboarding_screen():
    st.header("🧭 Configuración de tus ramos")

    # 1) Traer TODOS los ramos desde la base
    all_courses = get_all_courses()

    if not all_courses:
        st.error("No encontré ramos en la base de datos (course_summary está vacía).")
        return

    st.subheader("1️⃣ Selecciona tus ramos para este semestre")
    st.caption(
        "Ramos a elegir para el prototipo: DPT6382, IIC2233, MAT1610, IMT2210, IMT2200."
    )

    selected = st.multiselect(
        "Escoge tus cursos:",
        options=all_courses,
        # puedes dejar sin default o preseleccionar tus 5 de demo si quieres:
        # default=["DPT6382", "IIC2233", "MAT1610", "IMT2210", "IMT2200"],
    )

    st.subheader("2️⃣ Disponibilidad semanal")
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    disponibilidad = st.multiselect("¿Qué días puedes estudiar?", dias)

    st.subheader("3️⃣ ¿Cómo te sientes hoy?")
    mood = st.radio(
        "Tu mood actual:",
        ["😞 Mal", "😐 Meh", "🙂 Bien", "😁 Motivadísimo"],
        horizontal=True
    )

    if st.button("Guardar y continuar ➡"):
        if not selected:
            st.warning("Selecciona al menos 1 ramo.")
            return

        if not disponibilidad:
            st.warning("Selecciona al menos un día disponible 🤓")
            return

        save_onboarding(
            st.session_state["user"]["id"],
            ",".join(selected),          # ej: "DPT6382,IIC2233,MAT1610"
            ",".join(disponibilidad),    # ej: "Lunes,Miércoles"
            mood
        )

        st.success("¡Onboarding completado!")
        st.session_state["screen"] = "dashboard"


def dashboard():
    user_id = st.session_state["user"]["id"]
    data = get_onboarding(user_id)

    if not data:
        st.warning("No encontré tu configuración inicial. Vuelve al onboarding.")
        if st.button("Ir al onboarding"):
            st.session_state["screen"] = "onboarding"
        return

    ramos = [r.strip() for r in data["selected_ramos"].split(",") if r.strip()]

    # 🔹 AÑADE ESTAS DOS LÍNEAS
    disponibilidad = data["availability"] or ""
    mood_resumen = data["mood"]

    st.markdown("## 📊 Tu dashboard de ramos")
    st.caption("Aquí ves tus cursos del semestre y puedes entrar al plan de cada uno.")
    st.markdown("")

    st.markdown("### 📌 Resumen rápido")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"🧠 **Ánimo actual:** {mood_resumen}")
    with col2:
        st.write(f"📆 **Días disponibles:** {disponibilidad or 'No definido'}")

    st.markdown("---")

    if not ramos:
        st.info("Aún no has seleccionado ramos. Ve al onboarding para configurarlos.")
        if st.button("Configurar ramos", key="btn_cfg_ramos"):
            st.session_state["screen"] = "onboarding"
        return

    st.subheader("Tus cursos")

    cols = st.columns(2)
    for i, code in enumerate(ramos):
        col = cols[i % 2]
        with col:
            with st.container(border=True):
                st.markdown(f"### 📘 {code}")

                st.write("Aquí después vas a ver:")
                st.write("- Progreso del plan de estudio")
                st.write("- Próximas sesiones sugeridas")
                st.write("- Archivos / apuntes asociados al ramo")

                if st.button(f"Ver plan para {code}", key=f"plan_{code}"):
                    st.session_state["current_course"] = code
                    st.session_state["screen"] = "course"
                    st.rerun()

def edit_user_screen():
    user = st.session_state["user"]
    st.header("Editar usuario")

    with st.form("edit_user_form"):
        new_username = st.text_input("Nombre de usuario", value=user["username"])
        new_email = st.text_input("Correo electrónico (opcional)", value=user.get("email") or "")
        submitted = st.form_submit_button("Guardar cambios")

    if submitted:
        if not new_username:
            st.warning("El nombre de usuario no puede estar vacío.")
            return

        update_user(user["id"], new_username=new_username, new_email=new_email or None)
        st.session_state["user"]["username"] = new_username
        st.session_state["user"]["email"] = new_email or None

        st.success("Datos actualizados ✅")

    st.markdown("")  # pequeño espacio
    if st.button("⬅ Volver al dashboard"):
        st.session_state["screen"] = "dashboard"
        st.rerun()



def course_detail_screen():
    code = st.session_state.get("current_course")

    if not code:
        st.warning("No se encontró el ramo seleccionado.")
        if st.button("Volver al dashboard"):
            st.session_state["screen"] = "dashboard"
            st.rerun()
        return

    # Cabecera
    st.markdown(f"### 📘 Plan de estudio para **{code}**")

    if st.button("⬅ Volver al dashboard"):
        st.session_state["screen"] = "dashboard"
        st.rerun()

    st.markdown("---")


    # Sección 2: generar plan real
    st.subheader("2. Generar plan de estudio (Gemini Integrated)")

    user_id = st.session_state["user"]["id"]
    onboard = get_onboarding(user_id)

    if not onboard:
        st.warning("No encontro tu onboarding. Vuelve a configurarlo.")
        return

    onboard = dict(onboard)
    disponibilidad_str = onboard.get("availability") or ""
    mood_base = onboard.get("mood") or "Bien"

    estado_animo = _mood_a_estado_animo(mood_base)
    bloques = _dias_a_bloques(disponibilidad_str)

    if not bloques:
        st.warning("Tu disponibilidad esta vacía. Edita tus días en el onboarding.")
        return
    
    uploaded_files = st.file_uploader(
    "📎 Sube programa, guías o apuntes del ramo",
    type=["pdf", "png", "jpg", "jpeg", "txt"],
    accept_multiple_files=True,
    key=f"uploader_{code}",)

    if not uploaded_files:
        st.info("Sube al menos un archivo para generar un plan real.")
        return

    entradas = [_archivo_a_entrada(f) for f in uploaded_files]

    payload = {
        "curso": {"nombre": code, "codigo": code},
        "semestre": {},  # backend completa si detecta fechas
        "disponibilidad": {"zona_horaria": "America/Santiago", "bloques": bloques},
        "evaluaciones_conocidas": [],
        "estado_animo": estado_animo,
        "entradas": entradas,
    }

    if st.button("🎯 Generar plan con IA", key=f"gen_real_{code}"):
        with st.spinner("Generando plan y calendario..."):
            try:
                plan, ics_str = generar_plan_y_ics_multimodal(payload)
                st.session_state[f"plan_{code}"] = plan
                st.session_state[f"ics_{code}"] = ics_str
                st.success("Plan generado! ✅")
            except Exception as e:
                st.error(f"Falló la generación del plan: {e}")

    plan_obj = st.session_state.get(f"plan_{code}")
    ics_guardado = st.session_state.get(f"ics_{code}")

    try:
        data_plan = plan_obj.model_dump()
    except Exception:
        data_plan = getattr(plan_obj, "dict", lambda: {})()

    # OJO: tu función simple espera sesiones directas.
    # Si tu JSON viene con "semanas", puedes aplanar así:
    sesiones = []
    for semana in data_plan.get("semanas", []):
        sesiones.extend(semana.get("sesiones", []))

    st.markdown(plan_a_parrafos_simple(sesiones))

    # Sección 3: descarga calendario real
    st.subheader("3️⃣ Exportar a calendario (real)")

    if ics_guardado:
        st.download_button(
            label="📅 Descargar plan en .ics",
            data=ics_guardado,
            file_name=f"plan_{code}.ics",
            mime="text/calendar",
            key=f"dl_{code}",
        )
    else:
        st.info("Primero genera el plan para habilitar el .ics.")

    if st.button("📅 Descargar plan en .ics (demo)"):
        st.info("Para la demo no estamos generando el archivo real, solo mostrando el flujo.")


# --------- ROUTER ---------
if st.session_state["user"]:
    if st.session_state["screen"] == "onboarding":
        onboarding_screen()
    elif st.session_state["screen"] == "dashboard":
        dashboard()
    elif st.session_state["screen"] == "course":
        course_detail_screen()
    elif st.session_state["screen"] == "edit_user":
        edit_user_screen()
    else:
        # Si por alguna razón el screen no calza, decidimos según si tiene onboarding
        user_id = st.session_state["user"]["id"]
        data = get_onboarding(user_id)
        if data:
            st.session_state["screen"] = "dashboard"
            dashboard()
        else:
            st.session_state["screen"] = "onboarding"
            onboarding_screen()
else:
    # Usuario NO logueado
    if st.session_state["screen"] == "register":
        register_screen()
    else:
        st.session_state["screen"] = "login"
        login_screen()

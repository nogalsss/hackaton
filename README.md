# 📚 SmartSemester - Dashboard Inteligente para Estudiantes de la Universidad Católica

SmartSemester es una aplicación web diseñada para ayudarte a organizar tus estudios en un solo lugar.  
Permite seleccionar tus ramos, almacenar material, registrar tu disponibilidad y tu estado de ánimo, y generar un **plan semanal de estudio** más realista y eficiente, incluso exportable a calendario.

---

## Índice
- [¿De qué trata esta aplicación?](#de-qué-trata-esta-aplicación)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [📁 Estructura del proyecto](#-estructura-del-proyecto)
- [⚙️ Requisitos e instalación](#️-requisitos-e-instalación)
- [🔐 Variables de entorno](#-variables-de-entorno)
- [🚀 Ejecución](#-ejecución)
- [🗃️ Base de datos de ramos](#️-base-de-datos-de-ramos)
- [Explicación Backend](#explicación-backend)
- [Explicación Frontend (Streamlit)](#explicación-frontend-streamlit)
- [🔀 Flujo general de la APP](#-flujo-general-de-la-app)

---

## ¿De qué trata esta aplicación?

SmartSemester nos ayuda como estudiantes a:

- ✔ Tener en un mismo lugar todo el material de estudio para nuestros ramos.
- ✔ Crear un plan semanal de estudio en base a nuestra disponibilidad y estado de ánimo.
- ✔ Mejorar la organización y gestión del tiempo.
- ✔ Mantener registros y materiales de semestres anteriores sin tenerlos dispersos en múltiples archivos.

El objetivo es entregar una planificación más humana y adaptable, considerando que nuestro rendimiento y enfoque varían según cómo nos sintamos y cuánto tiempo real tenemos disponible.

---

## Tecnologías utilizadas

| Tecnología | Uso |
|-----------|-----|
| **Python 3.10+** | Lógica del sistema y backend |
| **Streamlit** | Interfaz frontend |
| **SQLite** | Persistencia local (usuarios, onboarding y ramos) |
| **Pydantic** | Modelado estructurado del plan de estudio |
| **python-dotenv** | Carga de variables de entorno desde `.env` |
| **google-genai (Gemini)** | Generación del resumen/plan con IA |
| **Pandas** | Carga/transformación de datos de ramos |
| **SQLAlchemy** | Escritura de tablas desde el script de extracción |
| **HTML/CSS** | Estilización dentro de Streamlit |

### Librerías opcionales (para mejores lecturas de archivos)
Estas pueden no ser estrictamente necesarias según el flujo que uses:
- **PyPDF2** (lectura de PDF)
- **Pillow** (imágenes)
- **pytesseract** (OCR)

> Si usas OCR con `pytesseract`, necesitas tener Tesseract instalado en tu sistema operativo.

---

## 📁 Estructura del proyecto

```text
SmartSemester/
│── backend/
│   ├── gen_calendar.py
│   ├── modelos.py
│   ├── parametros.py
│   ├── planificador.py
│   └── __init__.py
│
│── Front-end/
│   ├── app.py
│   ├── cursos.py
│   ├── onboarding.py
│   ├── extraer_cursos.py
│   ├── usuarios.py
│   ├── ramos_uc.db
│   └── backup-ramos.sql
│
│── main.py
│── README.md
│── LICENSE
│── requirements.txt
│── .gitignore
│── .env.example

## Explicación Backend:
📍 Requisitos:
- Python 3.10 + 
- pip install -r requirements.txt

## Crea un archivo .env en la raíz basado en .env.example.
## Variables usadas por el backend:

- GENAI_KEY (requerida para IA)

- GEMINI_MODEL_RESUMEN (idealmente modelo ligero)
- GEMINI_MODEL_PLAN (modelo con mas capacidad de analisis)
- ZONA_HORARIA (opcional, por defecto America/Santiago)

🚀 Ejecución
➡ Launcher simple en la raiz del proyecto con py main.py

## 🔀 Flujo general de la APP
Usuario → Registro/Login → Onboarding → Selección de Cursos
→ Guardar disponibilidad → Guardar mood → Dashboard final


📌 Dashboard incluye
➡ Cursos / Botones para ver su plan
➡ Edición de perfil
➡ Disponibilidad semanal editable
➡ Estado de ánimo diario
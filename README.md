# SmartSemester - Dashboard Inteligente para Estudiantes de la Universidad Catolica

Esta aplicación web esta diseñada para ayudarte a organizar tus estudios, los ramos que tienes que estudiar, registrar tú estado de ánimo y así poder modificar tú plan semanal de estudio de una forma más eficiente.


---

## Índice 
- [SmartSemester - Dashboard Inteligente para Estudiantes de la Universidad Catolica](#smartsemester---dashboard-inteligente-para-estudiantes-de-la-universidad-catolica)
  - [Índice](#índice)
  - [Tecnologías utilizadas](#tecnologías-utilizadas)
  - [📁 Estructura del proyecto](#-estructura-del-proyecto)
  - [Explicación Backend:](#explicación-backend)
  - [Explicación Frontend (STREAMLIT):](#explicación-frontend-streamlit)
  - [🔀 Flujo general de la APP](#-flujo-general-de-la-app)

---
¿De qué trata esta aplicación?

SmartSemester nos ayuda como estudiantes a:
✔ Tener en mismo lugar todo el material de estudio para todos nuestros ramos
✔ Poder crear un plan semanal de estudios en base a como nos estemos sintiendo
✔ Tener una mejor organización
✔ Poder contar con todas las interrogaciones/tareas/examenes de los semestres anteriores sin necesidad de estar buscandolo todos en diferentes archivos

Nuestro objetivo es poder crear un planificación de estudios adecuada a como nos sintamos ya que eso suele afectar mucho a la hora de enofcarnos a nuestro estudios y no sabemos como gestionar bien nuestros tiempos.}


---


## Tecnologías utilizadas
| Tecnología | Uso |
|-----------|-----|
| **Python** | Backend + lógica |
| **Streamlit** | Interfaz frontend |
| **SQLite** | Base de datos |
| **Pandas** | Carga de datos de ramos |
| **HTML/CSS** | Estilización en Streamlit |
| **SQL/Requests, JSON** | Gestión |

---

## 📁 Estructura del proyecto
SmartSemester/
│── backend/
│   ├── gen_calendar.py
│   ├── modelos.py
│   ├── parametros.py
│   ├── planificador.py
│   ├── prueba.py
│
│── Front-end/
│   ├── app.py
│   ├── cursos.py
│   ├── onboarding.py
│   ├── extraer_cursos.py
│   ├── usuarios.py
│   ├── ramos_uc.db          <-- Base de datos SQLite
│   ├── backup-ramos.sql
│
│── README.md
│── LICENSE
│── requirements.txt
│── .gitignore

## Explicación Backend:
📍 Requisitos:
- Python 3.10 + 
-  pip install -r requirements.txt
  
📍 Correr backend de funcionalidades:
- python backend/planificador.py
  
## Explicación Frontend (STREAMLIT):
📍 Instalar dependencias:
- pip install streamlit
- pip install -r requirements.txt
📍 Ejecutar la app:
- streamlit run Front-end/app.py


## 🔀 Flujo general de la APP
Usuario → Registro/Login → Onboarding → Selección de Cursos
→ Guardar disponibilidad → Guardar mood → Dashboard final


📌 Dashboard incluye
➡ Cursos / Botones para ver su plan
➡ Edición de perfil
➡ Disponibilidad semanal editable
➡ Estado de ánimo diario
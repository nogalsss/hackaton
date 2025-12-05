from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from parametros import ZONA_HORARIA

TipoEvaluacion = Literal["control", "tarea", "certamen", "examen", "otro"]
TipoSesion = Literal["teoria", "ejercicios", "repaso", "evaluacion", "proyecto"]
Intensidad = Literal["suave", "normal", "intensa"]

class CursoPlan(BaseModel):
    nombre: str
    codigo: Optional[str] = None
    semestre: Optional[str] = None

class ConfiguracionPlan(BaseModel):
    fecha_inicio: str
    fecha_fin: str
    zona_horaria: str = ZONA_HORARIA
    intensidad: Intensidad = "normal"

class ResumenPlan(BaseModel):
    estrategia: str = ""
    riesgos: List[str] = Field(default_factory=list)

class EvaluacionCercana(BaseModel):
    nombre: str
    fecha: str
    tipo: TipoEvaluacion = "otro"
    ponderacion: Optional[float] = Field(default=None, ge=0, le=1)

class SesionPlan(BaseModel):
    id: str
    titulo: str
    fecha: str
    inicio: str
    fin: str
    duracion_minutos: int
    tipo: TipoSesion
    temas: List[str]
    output: Optional[str] = None
    prioridad: int = Field(1, ge=1, le=3)

class RangoFechas(BaseModel):
    inicio: str
    fin: str

class SemanaPlan(BaseModel):
    numero: int
    rango_fechas: RangoFechas
    objetivos: List[str]
    contenidos: List[str]
    evaluaciones_cercanas: List[EvaluacionCercana] = Field(default_factory=list)
    sesiones: List[SesionPlan] = Field(default_factory=list)

class PlanEstudio(BaseModel):
    curso: CursoPlan
    configuracion: ConfiguracionPlan
    resumen: ResumenPlan
    semanas: List[SemanaPlan]

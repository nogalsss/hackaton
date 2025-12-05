import re
import pandas as pd
from sqlalchemy import create_engine

SQL_FILE = "backup-ramos.sql"   # nombre del archivo .sql
OUTPUT_DB = "ramos_uc.db"       # nombre de la base sqlite

# Leer todo el archivo SQL
with open(SQL_FILE, "r", encoding="utf-8") as f:
    content = f.read()

# Buscar todos los INSERT INTO course_summary VALUES(...)
# Cada fila viene en formato:
# INSERT INTO course_summary VALUES(1,'AGC204',0,0,0,0,0,0,0,0,NULL,NULL);
pattern = r"INSERT INTO course_summary VALUES\((.*?)\);"
matches = re.findall(pattern, content)

print("Total de filas encontradas en course_summary:", len(matches))

rows = []
for m in matches:
    # m es el contenido entre paréntesis: 1,'AGC204',0,0,...,NULL,NULL
    raw_fields = m.split(",")
    fields = []
    for item in raw_fields:
        item = item.strip()
        if item.upper() == "NULL":
            fields.append(None)
        elif item.startswith("'") and item.endswith("'"):
            fields.append(item[1:-1])  # quitar comillas
        else:
            # intentar convertir a int, si falla dejar como texto
            try:
                fields.append(int(item))
            except ValueError:
                fields.append(item)
    rows.append(fields)

# Según tu ejemplo hay 12 columnas:
# (1,'AGC204',0,0,0,0,0,0,0,0,NULL,NULL)
# => id, code, + 10 métricas
columns = [
    "id",
    "code",
    "metric1",
    "metric2",
    "metric3",
    "metric4",
    "metric5",
    "metric6",
    "metric7",
    "metric8",
    "metric9",
    "metric10",
]

# Si alguna fila no tiene exactamente 12 campos, avisar
bad_rows = [r for r in rows if len(r) != len(columns)]
if bad_rows:
    print("⚠ Hay filas con cantidad distinta de columnas. Ejemplo:", bad_rows[0])
    print("Len fila:", len(bad_rows[0]), "Len columnas:", len(columns))

df = pd.DataFrame(rows, columns=columns)
print(df.head())

# Crear base sqlite y guardar la tabla
engine = create_engine(f"sqlite:///{OUTPUT_DB}")
df.to_sql("course_summary", engine, if_exists="replace", index=False)

print("✔ Base creada:", OUTPUT_DB)
print("✔ Filas en course_summary:", len(df))

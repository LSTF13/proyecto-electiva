"""Genera reportes_base.xlsx con datos de ejemplo. Ejecutar una sola vez: python crear_excel_base.py"""
import random
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from localidades import LOCALIDADES

random.seed(7)
nombres = ["Rocky", "Luna", "Max", "Mía", "Toby", "Nina", "Simba", "Kira", "Thor", "Canela", "Bruno", "Lola",
           "Zeus", "Pelusa", "Coco", "Mishi", "Duque", "Chispa", "Rex", "Frida"]
animales = ["Perro - Labrador", "Perro - Criollo", "Perro - Golden Retriever", "Perro - Pug", "Perro - Schnauzer",
            "Perro - Beagle", "Gato - Criollo", "Gato - Siamés", "Gato - Persa", "Conejo - Enano", "Loro - Amazónico"]
colores = ["Café", "Negro", "Blanco", "Dorado", "Gris", "Café con blanco", "Negro con blanco", "Atigrado", "Crema"]
cosas = ["collar rojo", "collar azul", "sin collar", "una mancha en el ojo", "chaleco verde", "cola cortada",
         "microchip", "es muy amigable", "es asustadizo, no se le acerque rápido"]
barrios = {"Usaquén": "Cedritos", "Chapinero": "Chicó", "Suba": "Niza", "Kennedy": "Timiza", "Engativá": "Santa Helenita",
           "Bosa": "Bosa Centro", "Fontibón": "Modelia", "Teusaquillo": "La Soledad", "Ciudad Bolívar": "Lucero"}

wb = Workbook()
ws = wb.active
ws.title = "Reportes"
ws.append(["Nombre mascota", "Tipo animal / raza", "Color", "Fecha y hora de pérdida", "Descripción"])
ahora = datetime(2026, 11, 20, 18, 0)
pesos = [8 if l in barrios else 2 for l in LOCALIDADES]
for _ in range(60):
    loc = random.choices(LOCALIDADES, weights=pesos)[0]
    f = ahora - timedelta(days=random.randint(0, 120), hours=random.randint(0, 23), minutes=random.choice([0, 15, 30, 45]))
    ws.append([random.choice(nombres), random.choice(animales), random.choice(colores), f,
               f"Se perdió cerca de {barrios.get(loc, 'el parque principal')}, localidad de {loc}. "
               f"Detalle: {random.choice(cosas)}."])

fuente = Font(name="Arial", size=10)
for fila in ws.iter_rows(min_row=1):
    for c in fila:
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF") if c.row == 1 else fuente
        if c.row == 1:
            c.fill = PatternFill("solid", fgColor="2F5597")
        if c.column == 4 and c.row > 1:
            c.number_format = "dd/mm/yyyy hh:mm"
        c.alignment = Alignment(vertical="top", wrap_text=(c.column == 5))
for col, ancho in zip("ABCDE", (18, 26, 20, 24, 70)):
    ws.column_dimensions[col].width = ancho
ws.freeze_panes = "A2"

ayuda = wb.create_sheet("Instrucciones")
for linea in ["La app solo lee la primera hoja («Reportes»). Orden de columnas obligatorio:",
              "Nombre mascota | Tipo animal / raza | Color | Fecha y hora de pérdida | Descripción",
              "Tipo/raza: «Perro - Labrador», «Gato - Siamés». Otros animales: «Conejo - Enano».",
              "Fecha: dd/mm/aaaa hh:mm. Para detectar la localidad, nómbrela en la descripción (ej. «Suba», «Kennedy»).",
              "No incluya teléfonos ni correos (Ley 1581 de 2012). Los datos de ejemplo de la hoja 1 son ficticios."]:
    ayuda.append([linea])
ayuda.column_dimensions["A"].width = 120
wb.save(Path(__file__).parent / "reportes_base.xlsx")
print("reportes_base.xlsx creado")

from datetime import datetime, time

import pandas as pd
import streamlit as st

import db
import loader
from localidades import LOCALIDADES, SIN_LOCALIDAD

st.set_page_config(page_title="Mascotas perdidas · Bogotá", page_icon=" ", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1100px; padding-top: 2rem;}
@media (max-width: 640px) {.block-container {padding: 1rem 0.6rem;}}
</style>""", unsafe_allow_html=True)

PAGINA = 15


def esc(t) -> str:
    return str(t).replace("[", "(").replace("]", ")").replace("$", "\\$")


@st.cache_data(show_spinner=False)
def datos(version) -> pd.DataFrame:
    return db.cargar_reportes()


def hace(fecha) -> str:
    d = (datetime.now() - fecha).days
    return "hoy" if d <= 0 else "hace 1 día" if d == 1 else f"hace {d} días"


def mostrar_alertas(alertas):
    if alertas:
        with st.expander(f"{len(alertas)} alerta(s) en los datos de origen"):
            for a in alertas[:100]:
                st.write("• " + a)
            if len(alertas) > 100:
                st.caption(f"... y {len(alertas) - 100} más.")


resultado = db.sincronizar_base()
if resultado:
    st.session_state["sync"] = resultado
df = datos(db.version())

st.sidebar.title("Mascotas perdidas")
pagina = st.sidebar.radio("Navegación", ["Feed", "Dashboard", "Añadir reporte", "Importar archivo"],
                          label_visibility="collapsed")

if "sync" in st.session_state:
    msg, alertas = st.session_state["sync"]
    st.sidebar.caption(msg)
    if alertas:
        st.sidebar.caption(f"{len(alertas)} alerta(s) al leer el Excel base")

#FEED =======================
if pagina == "Feed":
    st.title("Mascotas perdidas")
    if "sync" in st.session_state:
        mostrar_alertas(st.session_state["sync"][1])

    st.sidebar.divider()
    st.sidebar.subheader("Filtros")
    buscar = st.sidebar.text_input("Buscar texto", placeholder="nombre, descripción...")
    tipos = st.sidebar.multiselect("Tipo de animal", ["Perro", "Gato", "Otro"])
    razas = st.sidebar.multiselect("Raza", sorted(df["raza"].unique()))
    colores = st.sidebar.multiselect("Color", sorted(df["color"].unique()))
    locs = st.sidebar.multiselect("Localidad", LOCALIDADES + [SIN_LOCALIDAD])
    orden = st.sidebar.radio("Orden", ["Más recientes", "Más antiguos"], horizontal=True)

    m = pd.Series(True, index=df.index)
    if buscar:
        b = buscar.lower()
        m &= (df["nombre_mascota"].str.lower().str.contains(b, regex=False)
              | df["descripcion"].str.lower().str.contains(b, regex=False))
    if tipos:
        m &= df["tipo"].isin(tipos)
    if razas:
        m &= df["raza"].isin(razas)
    if colores:
        m &= df["color"].isin(colores)
    if locs:
        m &= df["localidad"].isin(locs)
    vista = df[m].sort_values("fecha_perdida", ascending=(orden == "Más antiguos"))

    firma = (buscar, tuple(tipos), tuple(razas), tuple(colores), tuple(locs), orden)
    if st.session_state.get("firma") != firma:
        st.session_state["firma"], st.session_state["limite"] = firma, PAGINA
    limite = st.session_state.get("limite", PAGINA)

    st.caption(f"{len(vista)} reporte(s) encontrados")
    if vista.empty:
        st.info("No hay reportes con esos filtros.")
    for r in vista.head(limite).itertuples():
        with st.container(border=True):
            st.markdown(f"### {esc(r.nombre_mascota)}")
            st.caption(f"Se perdió el {r.fecha_perdida:%d/%m/%Y a las %H:%M} · {hace(r.fecha_perdida)}")
            st.markdown(f":blue-badge[{esc(r.tipo)}] :green-badge[{esc(r.raza)}] "
                        f":orange-badge[{esc(r.color)}] :violet-badge[{esc(r.localidad)}]")
            if r.descripcion:
                st.write(r.descripcion)
    if len(vista) > limite and st.button("Ver más reportes", use_container_width=True):
        st.session_state["limite"] = limite + PAGINA
        st.rerun()

# DASHBOARD =======================
elif pagina == "Dashboard":
    st.title("Dashboard")
    if df.empty:
        st.info("Aún no hay reportes.")
        st.stop()
    hoy = pd.Timestamp.now()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reportes totales", len(df))
    c2.metric("Últimos 30 días", int((df["fecha_perdida"] >= hoy - pd.Timedelta(days=30)).sum()))
    c3.metric("Tipo más frecuente", df["tipo"].mode().iat[0])
    ident = df[df["localidad"] != SIN_LOCALIDAD]
    c4.metric("Localidad con más reportes", ident["localidad"].mode().iat[0] if len(ident) else "—")

    st.subheader("Reportes por localidad de Bogotá")
    por_loc = df["localidad"].value_counts().reindex(LOCALIDADES, fill_value=0)
    st.bar_chart(por_loc, horizontal=True, height=520)
    sin = int((df["localidad"] == SIN_LOCALIDAD).sum())
    if sin:
        st.caption(f"{sin} reporte(s) no mencionan una localidad en la descripción y no se incluyen en el gráfico.")

    a, b = st.columns(2)
    with a:
        st.subheader("Por tipo de animal")
        st.bar_chart(df["tipo"].value_counts())
        st.subheader("Colores más frecuentes")
        st.bar_chart(df["color"].value_counts().head(10))
    with b:
        st.subheader("Razas más frecuentes")
        st.bar_chart(df["raza"].value_counts().head(10))
        st.subheader("Hora del día de la pérdida")
        st.bar_chart(df["fecha_perdida"].dt.hour.value_counts().reindex(range(24), fill_value=0))

    st.subheader("Reportes por mes")
    st.line_chart(df.groupby(df["fecha_perdida"].dt.to_period("M").astype(str)).size())

# AÑADIR REPORTE =======================
elif pagina == "Añadir reporte":
    st.title("Añadir reporte")
    st.info("No escriba teléfonos ni correos. Si los incluye en la descripción, el sistema los oculta "
            "automáticamente (Ley 1581 de 2012).")
    with st.form("nuevo_reporte", clear_on_submit=True):
        nombre = st.text_input("Nombre de la mascota *")
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo de animal *", ["Perro", "Gato", "Otro"])
        raza = c2.text_input("Raza (o qué animal es, si eligió «Otro»)", placeholder="Labrador, criollo, conejo...")
        color = st.text_input("Color *", placeholder="Café con blanco")
        c3, c4 = st.columns(2)
        fecha = c3.date_input("Fecha de pérdida *", max_value=datetime.now().date())
        hora = c4.time_input("Hora aproximada *", value=time(12, 0))
        localidad = st.selectbox("Localidad donde se perdió", ["Sin especificar"] + LOCALIDADES)
        descripcion = st.text_area("Descripción (señas, collar, zona exacta...)")
        enviar = st.form_submit_button("Publicar reporte", type="primary", use_container_width=True)

    if enviar:
        momento = datetime.combine(fecha, hora)
        if not nombre.strip() or not color.strip():
            st.error("El nombre y el color son obligatorios.")
        elif momento > datetime.now():
            st.error("La fecha y hora de pérdida no pueden estar en el futuro.")
        else:
            if localidad != "Sin especificar":
                descripcion = f"{descripcion.strip()} Zona: {localidad}.".strip()
            tipo_raza = f"{tipo} - {raza.strip()}" if raza.strip() else tipo
            reg = loader.construir_registro(nombre, tipo_raza, color, momento, descripcion)
            nuevos, _ = db.insertar(pd.DataFrame([reg]))
            if nuevos:
                st.success("Reporte publicado. Ya aparece en el feed y en el dashboard.")
            else:
                st.warning("Ya existe un reporte idéntico; no se duplicó.")

# IMPORTAR =======================
else:
    st.title("Importar archivo")
    st.write("Suba un archivo **.xlsx, .xls o .csv** (UTF-8) con 5 columnas, en este orden:")
    st.code("nombre mascota, tipo animal / raza, color, fecha y hora de pérdida, descripción")
    st.caption("Ejemplo: Rocky, Perro - Labrador, Café, 15/11/2026 08:30, Se escapó en Suba con collar rojo")
    archivo = st.file_uploader("Archivo de reportes", type=["xlsx", "xls", "csv"])
    if archivo and st.button("Importar", type="primary"):
        try:
            nuevo, alertas = loader.cargar_archivo(archivo, archivo.name)
            nuevos, dup = db.insertar(nuevo)
            st.success(f"{nuevos} reportes nuevos agregados · {dup} ya existían (ignorados).")
            mostrar_alertas(alertas)
        except Exception as e:
            st.error(f"No se pudo procesar el archivo: {e}")

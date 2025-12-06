import streamlit as st
import pandas as pd
import sys
import os 
import locale 
import io 

# --- Configuración Inicial ---
st.set_page_config(
    page_title="Gestión Juridica",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------
# Configuración del LOCALE para que los meses se muestren en español
# -----------------------------------------------------------
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'es')
        except locale.Error:
            pass 

# -----------------------------------------------------------
# Lógica para la ruta de los archivos de datos (PyInstaller Fix)
# -----------------------------------------------------------

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

NOMBRE_ARCHIVO_DATOS = os.path.join(base_path, 'data.xlsx')
NOMBRE_ARCHIVO_USUARIOS = os.path.join(base_path, 'usuarios.csv')
RUTA_IMAGEN_LOGO = os.path.join(base_path, 'assets', 'CARSA LOGO.webp')

# -----------------------------------------------------------
# Funciones de Utilidad (Limpieza y Carga)
# -----------------------------------------------------------

def limpiar_nombres_columnas(df, case='upper'):
    """
    Limpia los nombres de las columnas del DataFrame: 
    quita espacios en blanco alrededor y convierte a la caja especificada.
    """
    if case == 'upper':
        df.columns = df.columns.str.strip().str.upper()
    elif case == 'lower':
        df.columns = df.columns.str.strip().str.lower()
    return df

@st.cache_data
def cargar_datos_excel():
    """Carga y limpia la base de datos principal desde el Excel."""
    try:
        df = pd.read_excel(NOMBRE_ARCHIVO_DATOS)
        df = limpiar_nombres_columnas(df, case='upper') 
        
        # Conversión de tipos
        df['FECHA_PAGO'] = pd.to_datetime(df['FECHA_PAGO'], errors='coerce')
        df['FECHA_JUICIO_ANTE'] = pd.to_datetime(df['FECHA_JUICIO_ANTE'], errors='coerce')
        df['NRO_CEDULA'] = df['NRO_CEDULA'].astype(str)
        
        # Limpieza de texto para filtrado.
        # Estas líneas están libres de caracteres invisibles.
        df['NOMBRE_CLIENTE'] = df['NOMBRE_CLIENTE'].astype(str).str.strip().str.lower() 
        df['ABOGADO'] = df['ABOGADO'].astype(str).str.strip().str.lower() 
        df['FORMA_PAGO'] = df['FORMA_PAGO'].astype(str).str.strip().str.lower() 
        
        df = df.fillna({'NOMBRE_CLIENTE': '', 'ABOGADO': '', 'FORMA_PAGO': ''})
        return df
    except FileNotFoundError:
        st.error(f"🛑 Error: No se encontró el archivo {NOMBRE_ARCHIVO_DATOS}.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al cargar o procesar el Excel. Asegúrate de que las columnas existan y el formato sea correcto. Error: {e}")
        return pd.DataFrame()

@st.cache_resource
def cargar_datos_usuarios():
    """Carga la tabla de usuarios para el login."""
    try:
        df_users = pd.read_csv(NOMBRE_ARCHIVO_USUARIOS)
        df_users = limpiar_nombres_columnas(df_users, case='lower')
        
        # Limpieza de texto para autenticación
        df_users['usuario'] = df_users['usuario'].astype(str).str.strip().str.lower() 
        df_users['filtro_abogado'] = df_users['filtro_abogado'].astype(str).str.strip().str.lower() 
        return df_users
    except FileNotFoundError:
        st.error(f"🛑 Error: No se encontró el archivo de usuarios {NOMBRE_ARCHIVO_USUARIOS}.")
        return pd.DataFrame()


# Cargar los DataFrames al inicio de la aplicación
df_base = cargar_datos_excel()
df_usuarios = cargar_datos_usuarios()

# --- FUNCIONES DE FORMATO Y EXPORTACIÓN ---

def format_guaranies(value):
    """Formatea un número a moneda (Gs.) con separador de miles y punto decimal."""
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        # Usa formateo de Python para miles con coma, luego invierte para el formato Gs.
        formatted_value = f"Gs. {int(value):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted_value
    except (ValueError, TypeError):
        return "N/A"

def to_excel(df):
    """Convierte un DataFrame a un objeto BytesIO de Excel para descarga."""
    output = io.BytesIO()
    # Usamos openpyxl como motor
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Detalle de Pagos')
    processed_data = output.getvalue()
    return processed_data

# --- Lógica de Autenticación y Session State ---

def login_form():
    """Muestra el formulario de login y maneja la autenticación."""
    
    # Inyección de estilo para el botón principal de Login (más profesional)
    st.markdown("""
        <style>
        .login-btn button {
            background-color: #000000;
            color: white !important;
            width: 100%;
            border-radius: 8px;
            padding: 10px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Gestión Juridica - CARSA")
    st.markdown("---")
    st.subheader("Iniciá sesión para continuar")

    # Centrar formulario
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        username_input = st.text_input("USUARIO", label_visibility="visible", placeholder="Ingresar Usuario")
        username = username_input.strip().lower() 
        password = st.text_input("CONTRASEÑA", type="password", label_visibility="visible")
        
        # Contenedor para aplicar el estilo de botón
        st.markdown('<div class="login-btn">', unsafe_allow_html=True)
        if st.button("Ingresá", key="login_btn"):
            if username and password:
                user_match = df_usuarios[
                    (df_usuarios['usuario'] == username) & 
                    (df_usuarios['contrasena'] == password)
                ]
                
                if not user_match.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['filtro_abogado'] = user_match['filtro_abogado'].iloc[0] 
                    st.success("¡Inicio de sesión exitoso!")
                    st.rerun() 
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                st.warning("Por favor, ingrese el usuario y la contraseña.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()


# --- FUNCIONES DE LA APLICACIÓN PRINCIPAL ---

def mostrar_dashboard_resultados(df_resultados):
    """Muestra el dashboard de resultados con todos los cálculos, formato y estilos."""
    
    if df_resultados.empty:
        st.error("Error: No hay datos de pagos para este cliente en el sistema.")
        return
        
    cliente_data = df_resultados.iloc[0]
    
    # A. Cálculo de Totales y Variables
    monto_total_cobrado = df_resultados['MONTO_TOTAL_COBRADO'].sum()
    monto_demandado = cliente_data['MONTO_DEMANDA'] 
    
    monto_demandado_val = monto_demandado if pd.notna(monto_demandado) and pd.api.types.is_numeric_dtype(type(monto_demandado)) else 0
    saldo_demandado = monto_demandado_val - monto_total_cobrado

    # B. Agregación Antes vs. Después del Juicio
    fecha_juicio = cliente_data['FECHA_JUICIO_ANTE']
    
    if pd.notna(fecha_juicio):
        df_resultados['PERIODO'] = df_resultados.apply(
            lambda row: 'antes del juicio' 
                        if pd.notna(row['FECHA_PAGO']) and row['FECHA_PAGO'] <= fecha_juicio 
                        else 'despues del juicio', 
            axis=1
        )
    else:
        df_resultados['PERIODO'] = 'sin fecha de juicio'
        
    # Lógica de Agrupación de Formas de Pago
    df_resultados['FORMA_PAGO_AGRUPADA'] = df_resultados['FORMA_PAGO'].apply(
        lambda x: 'cheque judicial' if x == 'cheque judicial' else 'efectivo/otros'
    )
    
    # Agrupación por PERIODO, AÑO, MES_NUM y MES
    df_resultados['AÑO'] = df_resultados['FECHA_PAGO'].dt.year
    df_resultados['MES'] = df_resultados['FECHA_PAGO'].dt.strftime('%B').str.title() 
    df_resultados['MES_NUM'] = df_resultados['FECHA_PAGO'].dt.month
    
    df_pivot = df_resultados.pivot_table(
        index=['PERIODO', 'AÑO', 'MES_NUM', 'MES'],
        columns='FORMA_PAGO_AGRUPADA', 
        values='MONTO_TOTAL_COBRADO',
        aggfunc='sum',
        fill_value=0,
        margins=True,
        margins_name='TOTAL COBRADO'
    ).reset_index()
    
    # Ordenamiento
    periodo_order = ['antes del juicio', 'despues del juicio', 'sin fecha de juicio', 'TOTAL COBRADO']
    df_pivot['PERIODO'] = pd.Categorical(df_pivot['PERIODO'], categories=periodo_order, ordered=True)
    df_pivot = df_pivot.sort_values(by=['PERIODO', 'AÑO', 'MES_NUM'], na_position='last')
    
    df_pivot = df_pivot.drop(columns=['MES_NUM'])

    # C. Presentación de la Cabecera de Totales (KPIs con estilo mejorado)
    
    st.subheader("Indicadores Clave de Cobro")
    col_kpi_1, col_kpi_2, col_kpi_3 = st.columns(3)

    kpi_base_style = "background-color: #293C47; border-radius: 8px; padding: 10px; text-align: center; color: white;"
    
    with col_kpi_1:
        st.markdown(
            f"<div style='{kpi_base_style}'><b>MONTO TOTAL COBRADO</b><br><h2 style='color: #FEE715;'>{format_guaranies(monto_total_cobrado)}</h2></div>", 
            unsafe_allow_html=True
        )
        
    with col_kpi_2:
        monto_demandado_display = monto_demandado_val
        st.markdown(
            f"<div style='{kpi_base_style}'><b>MONTO DEMANDADO</b><br><h2 style='color: #FEE715;'>{format_guaranies(monto_demandado_display)}</h2></div>", 
            unsafe_allow_html=True
        )

    with col_kpi_3:
        color_saldo = '#FF6B6B' if saldo_demandado > 0 else '#6BFF6B' 
        st.markdown(
            f"<div style='{kpi_base_style}'><b>SALDO PENDIENTE</b><br><h2 style='color:{color_saldo};'>{format_guaranies(saldo_demandado)}</h2></div>", 
            unsafe_allow_html=True
        )

    st.markdown("---")

    # D. Presentación de Datos del Cliente 
    with st.expander("Detalles del Cliente", expanded=True):
        col_info, col_vacio = st.columns([3, 7])
        
        with col_info:
            st.subheader(f"Cliente: {cliente_data['NOMBRE_CLIENTE'].title()}")
            st.markdown(f"**Nro Cédula**: {cliente_data['NRO_CEDULA']}")
            st.markdown("---")
            
            st.markdown(f"**Nro Juicio**: {cliente_data['NRO_JUICIO']} | **Estado**: {cliente_data['ESTADO'].title()}")
            st.markdown(f"**Abogado Asignado**: {cliente_data['ABOGADO'].title()}")
            
            fecha_juicio_str = cliente_data['FECHA_JUICIO_ANTE'].strftime('%d/%m/%Y') if pd.notna(cliente_data['FECHA_JUICIO_ANTE']) else 'N/A'
            st.markdown(f"**Fecha Juicio Ante**: {fecha_juicio_str}")
            
            ultimo_pago = df_resultados['FECHA_PAGO'].max()
            ultimo_pago_str = ultimo_pago.strftime('%d/%m/%Y') if pd.notna(ultimo_pago) else 'N/A'
            st.markdown(f"**Último cobro**: {ultimo_pago_str}")

    # E. Presentación del Detalle de Pagos
    st.subheader("HISTORIAL DE COBROS POR MES")
        
    df_display = df_pivot.copy()
    
    df_display['PERIODO'] = df_display['PERIODO'].astype(str).str.replace('_', ' ').str.title()
    
    cols_to_format = [c for c in df_display.columns if c not in ['PERIODO', 'AÑO', 'MES']]
    for col in cols_to_format:
        df_display[col] = df_display[col].apply(lambda x: format_guaranies(x) if x != 0 else '-')
    
    def highlight_total_row(row):
        style = 'background-color: #7A741D; font-weight: bold; color: white;' if row['PERIODO'] == 'Total Cobrado' else ''
        return [style] * len(row)

    styled_df = df_display.style.apply(highlight_total_row, axis=1)

    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # --- BOTÓN DE EXPORTACIÓN A EXCEL ---
    st.download_button(
        label="📥 Descargar Datos en Excel (.xlsx)",
        data=to_excel(df_pivot),
        file_name=f"detalle_pagos_{cliente_data['NRO_CEDULA']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )


def mostrar_resultados(df_filtrado_abogado):
    """Realiza la búsqueda final, maneja múltiples resultados y muestra el dashboard."""
    
    cedula = st.session_state.get('cedula', '').strip()
    nombre = st.session_state.get('nombre', '').strip().lower()

    filtro_final = pd.Series([False] * len(df_filtrado_abogado))
    
    if cedula:
        filtro_cedula = df_filtrado_abogado['NRO_CEDULA'].str.contains(cedula, case=False, na=False)
        filtro_final = filtro_final | filtro_cedula
        
    if nombre:
        filtro_nombre = df_filtrado_abogado['NOMBRE_CLIENTE'].str.contains(nombre, case=True, na=False)
        filtro_final = filtro_final | filtro_nombre

    if not cedula and not nombre:
        st.warning("Ingrese el número de cédula o el nombre del cliente para buscar.")
        return
        
    df_resultados_match = df_filtrado_abogado[filtro_final].copy()

    if df_resultados_match.empty:
        st.warning(f"No se encontraron resultados para la búsqueda '{cedula or nombre}'. Verifique los datos o su asignación.")
        return
    
    # Lógica de Manejo de Múltiples Resultados
    clientes_encontrados = df_resultados_match.drop_duplicates(subset=['NRO_CEDULA']).copy()
    
    clientes_encontrados['DISPLAY_NAME'] = clientes_encontrados.apply(
        lambda row: f"{row['NOMBRE_CLIENTE'].title()} - {row['NRO_CEDULA']}", 
        axis=1
    )
    
    cliente_seleccionado_cedula = clientes_encontrados['NRO_CEDULA'].iloc[0]
    
    if len(clientes_encontrados) > 1:
        st.info(f"Se encontraron {len(clientes_encontrados)} clientes con esta búsqueda. Seleccione uno:")
        
        cliente_seleccionado_cedula = st.selectbox(
            "Seleccione el cliente a visualizar", 
            options=clientes_encontrados['NRO_CEDULA'].tolist(), 
            index=0, 
            format_func=lambda cedula: clientes_encontrados.loc[clientes_encontrados['NRO_CEDULA'] == cedula, 'DISPLAY_NAME'].iloc[0], 
            key='cliente_selector'
        )
        st.markdown("---") 

    df_resultados_final = df_filtrado_abogado[df_filtrado_abogado['NRO_CEDULA'] == cliente_seleccionado_cedula].copy()
        
    mostrar_dashboard_resultados(df_resultados_final)


def app_principal():
    """Muestra la interfaz de búsqueda y aplica el filtro de seguridad."""
    
    filtro_abogado = st.session_state.get('filtro_abogado') 
    
    # Sidebar
    st.sidebar.markdown("## 🔍 Búsqueda de Clientes")
    
    if os.path.exists(RUTA_IMAGEN_LOGO):
        # Usamos el parámetro 'width' en lugar de 'use_column_width' para evitar la advertencia amarilla.
        st.sidebar.image(RUTA_IMAGEN_LOGO, width=250) 
    else:
        st.sidebar.title("Detalles de Cobros")
        
    # Se elimina la visualización del filtro de usuario (Usuario: TODOS/Abogado X)
    
    if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
        keys_to_delete = ['logged_in', 'filtro_abogado', 'search_active', 'cedula', 'nombre', 'cliente_selector']
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # 1. Aplicar el Filtro de Seguridad al DataFrame
    if filtro_abogado == 'todos':
        df_filtrado_abogado = df_base.copy()
    elif filtro_abogado:
        df_filtrado_abogado = df_base[df_base['ABOGADO'] == filtro_abogado].copy()
    else:
        st.warning("No se pudo aplicar el filtro de seguridad. Vuelva a iniciar sesión.")
        return
    
    # 2. Campos de Búsqueda Dual en el cuerpo principal
    st.header("Módulo de Búsqueda de Clientes")
    st.markdown("---")
    
    col_cedula, col_nombre, col_button, col_espacio = st.columns([2, 2, 1, 3])
    
    cedula_busqueda = col_cedula.text_input("NRO DE CEDULA", key='cedula_input', placeholder="Ingrese Cédula")
    nombre_busqueda = col_nombre.text_input("NOMBRE DE CLIENTE", key='nombre_input', placeholder="Ingrese Nombre")
    
    with col_button:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
        if st.button("🔎 Buscar", use_container_width=True):
            st.session_state['search_active'] = True
            st.session_state['cedula'] = cedula_busqueda
            st.session_state['nombre'] = nombre_busqueda
            
            if 'cliente_selector' in st.session_state:
                del st.session_state['cliente_selector']
            st.rerun()
            
    st.markdown("---")
        
    # 3. Mostrar resultados si la búsqueda está activa
    if st.session_state.get('search_active', False):
        mostrar_resultados(df_filtrado_abogado)


# --- Función Principal (Entry Point) ---
def main():
    """Punto de entrada de la aplicación: decide si mostrar Login o App."""
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['search_active'] = False
        st.session_state['cedula'] = ''
        st.session_state['nombre'] = ''

    if not st.session_state['logged_in']:
        login_form()
    else:
        app_principal()

if __name__ == '__main__':
    # Si logramos cargar ambos archivos, ejecutamos la aplicación
    if not df_base.empty and not df_usuarios.empty:
        main()
    elif df_base.empty:
        st.warning("La aplicación no puede iniciar porque la base de datos principal está vacía o es inaccesible.")
    elif df_usuarios.empty:
        st.warning("La aplicación no puede iniciar porque la tabla de usuarios está vacía o es inaccesible.")
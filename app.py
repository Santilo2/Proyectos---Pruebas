import streamlit as st
import pandas as pd

# --- Configuración Inicial ---
st.set_page_config(layout="wide")
NOMBRE_ARCHIVO_DATOS = 'data.xlsx'
NOMBRE_ARCHIVO_USUARIOS = 'usuarios.csv'

def limpiar_nombres_columnas(df, case='upper'):
    """
    Limpia los nombres de las columnas del DataFrame: 
    quita espacios en blanco alrededor y convierte a la caja especificada ('upper' o 'lower').
    """
    if case == 'upper':
        df.columns = df.columns.str.strip().str.upper()
    elif case == 'lower':
        df.columns = df.columns.str.strip().str.lower()
    return df

# Decorador para cargar el Excel solo una vez y almacenarlo en caché.
@st.cache_data
def cargar_datos_excel():
    """Carga y limpia la base de datos principal desde el Excel."""
    try:
        df = pd.read_excel(NOMBRE_ARCHIVO_DATOS)
        # LIMPIEZA CRUCIAL: Estandarizar encabezados a MAYÚSCULAS
        df = limpiar_nombres_columnas(df, case='upper') 
        
        df['FECHA_PAGO'] = pd.to_datetime(df['FECHA_PAGO'], errors='coerce')
        df['FECHA_JUICIO_ANTE'] = pd.to_datetime(df['FECHA_JUICIO_ANTE'], errors='coerce')
        df['NRO_CEDULA'] = df['NRO_CEDULA'].astype(str)
        
        # Aseguramos que todas las columnas relevantes estén en minúsculas para comparaciones de contenido
        df['NOMBRE_CLIENTE'] = df['NOMBRE_CLIENTE'].astype(str).str.lower()
        df['ABOGADO'] = df['ABOGADO'].astype(str).str.lower()
        df['FORMA_PAGO'] = df['FORMA_PAGO'].astype(str).str.lower()
        
        df = df.fillna({'NOMBRE_CLIENTE': '', 'ABOGADO': '', 'FORMA_PAGO': ''})
        return df
    except FileNotFoundError:
        st.error(f"🛑 Error: No se encontró el archivo {NOMBRE_ARCHIVO_DATOS}. Por favor, créalo y asegúrate de que esté en la misma carpeta.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al cargar o procesar el Excel. Asegúrate de que las columnas existan: {e}")
        return pd.DataFrame()

# Decorador para cargar la tabla de usuarios solo una vez.
@st.cache_resource
def cargar_datos_usuarios():
    """Carga la tabla de usuarios para el login."""
    try:
        df_users = pd.read_csv(NOMBRE_ARCHIVO_USUARIOS)
        # LIMPIEZA CRUCIAL: Estandarizar encabezados a MINÚSCULAS
        df_users = limpiar_nombres_columnas(df_users, case='lower')
        
        # Aseguramos que los filtros y usuarios estén en minúsculas para coincidir con la base de datos
        df_users['usuario'] = df_users['usuario'].astype(str).str.lower()
        df_users['filtro_abogado'] = df_users['filtro_abogado'].astype(str).str.lower()
        return df_users
    except FileNotFoundError:
        st.error(f"🛑 Error: No se encontró el archivo de usuarios {NOMBRE_ARCHIVO_USUARIOS}. Por favor, créalo y asegúrate de que esté en la misma carpeta.")
        return pd.DataFrame()


# Cargar los DataFrames al inicio de la aplicación
df_base = cargar_datos_excel()
df_usuarios = cargar_datos_usuarios()

# --- FUNCIONES DE FORMATO ---

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

# --- Lógica de Autenticación y Session State ---

def login_form():
    """Muestra el formulario de login y maneja la autenticación."""
    
    st.title("Ingresá")
    st.markdown("Iniciá sesión para continuar")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        # Aseguramos que el input de usuario se convierta a minúsculas
        username_input = st.text_input("USUARIO", label_visibility="visible", placeholder="CORREO ELECTRONICO")
        username = username_input.strip().lower() 
        password = st.text_input("CONTRASEÑA", type="password", label_visibility="visible")
        
        st.markdown("<style>div.stButton > button:first-child {background-color: black; color: white; width: 100%;}</style>", unsafe_allow_html=True)
        
        if st.button("Ingresá"):
            if username and password:
                # Los nombres de las columnas 'usuario' y 'contrasena' son minúsculas
                user_match = df_usuarios[
                    (df_usuarios['usuario'] == username) & 
                    (df_usuarios['contrasena'] == password)
                ]
                
                if not user_match.empty:
                    st.session_state['logged_in'] = True
                    # El filtro ya está en minúsculas
                    st.session_state['filtro_abogado'] = user_match['filtro_abogado'].iloc[0] 
                    st.success("¡Inicio de sesión exitoso!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                st.warning("Por favor, ingrese el usuario y la contraseña.")

    st.stop()


# --- FUNCIONES DE LA APLICACIÓN PRINCIPAL (TODAS ALINEADAS AQUÍ) ---

def mostrar_dashboard_resultados(df_resultados):
    """Muestra el dashboard de resultados con todos los cálculos, formato y estilos."""
    
    if df_resultados.empty:
        st.error("Error interno: No hay datos para mostrar en el dashboard.")
        return
        
    cliente_data = df_resultados.iloc[0]
    
    # A. Cálculo de Totales y Variables
    monto_total_cobrado = df_resultados['MONTO_TOTAL_COBRADO'].sum()
    monto_demandado = cliente_data['MONTO_DEMANDA'] 
    saldo_demandado = monto_demandado - monto_total_cobrado

    # B. Agregación Antes vs. Después del Juicio
    fecha_juicio = cliente_data['FECHA_JUICIO_ANTE']
    
    # Aplicamos filtro de minúsculas también aquí, aunque los datos ya vienen limpios
    df_resultados['PERIODO'] = df_resultados.apply(
        lambda row: 'antes del juicio' if pd.notna(row['FECHA_PAGO']) and row['FECHA_PAGO'] <= fecha_juicio else 'despues del juicio', 
        axis=1
    )
    
    if pd.isna(fecha_juicio):
        df_resultados['PERIODO'] = 'sin fecha de juicio'
        
    # *** NUEVA LÓGICA DE AGRUPACIÓN DE FORMAS DE PAGO ***
    # Agrupa 'cheque judicial' en su propia categoría, y todo lo demás en 'efectivo/otros'
    df_resultados['FORMA_PAGO_AGRUPADA'] = df_resultados['FORMA_PAGO'].apply(
        lambda x: 'cheque judicial' if x == 'cheque judicial' else 'efectivo/otros'
    )
    # ****************************************************
    
    # *** Agrupación y Ordenamiento para la Tabla Dinámica ***
    # 1. Crear las columnas 'AÑO', 'MES' y 'MES_NUM' dentro del DataFrame
    # MES_NUM es crucial para ordenar los meses cronológicamente.
    df_resultados['AÑO'] = df_resultados['FECHA_PAGO'].dt.year
    df_resultados['MES'] = df_resultados['FECHA_PAGO'].dt.strftime('%B')
    df_resultados['MES_NUM'] = df_resultados['FECHA_PAGO'].dt.month
    
    # 2. Agrupación por PERIODO, AÑO, MES_NUM y MES
    # Ahora usamos la columna 'FORMA_PAGO_AGRUPADA' para las columnas
    df_pivot = df_resultados.pivot_table(
        index=['PERIODO', 'AÑO', 'MES_NUM', 'MES'],
        columns='FORMA_PAGO_AGRUPADA', # <-- USAMOS LA COLUMNA AGRUPADA
        values='MONTO_TOTAL_COBRADO',
        aggfunc='sum',
        fill_value=0,
        margins=True,
        margins_name='TOTAL COBRADO'
    ).reset_index()
    
    # 3. Ordenar el DataFrame para asegurar que los meses estén en orden cronológico
    # Definir el orden deseado para PERIODO
    periodo_order = ['antes del juicio', 'despues del juicio', 'sin fecha de juicio', 'TOTAL COBRADO']
    df_pivot['PERIODO'] = pd.Categorical(df_pivot['PERIODO'], categories=periodo_order, ordered=True)

    # Ordenar por PERIODO, AÑO y MES_NUM
    df_pivot = df_pivot.sort_values(by=['PERIODO', 'AÑO', 'MES_NUM'], na_position='last')
    
    # Eliminar MES_NUM antes de la visualización
    df_pivot = df_pivot.drop(columns=['MES_NUM'])
    # ********************************************************************

    # C. Presentación de la Cabecera de Totales (KPIs con estilo)
    
    st.subheader("Indicadores Clave de Cobro")
    col_kpi_1, col_kpi_2, col_kpi_3 = st.columns(3)

    kpi_style = "background-color: #7A741D; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 20px; color: white;"
    
    with col_kpi_1:
        st.markdown(f"<div style='{kpi_style}'><b>MONTO TOTAL COBRADO</b><br><h2>{format_guaranies(monto_total_cobrado)}</h2></div>", unsafe_allow_html=True)
        
    with col_kpi_2:
        # Aseguramos que 'MONTO_DEMANDA' exista y sea un valor numérico
        monto_demandado_display = monto_demandado if pd.notna(monto_demandado) else 0 
        st.markdown(f"<div style='{kpi_style}'><b>MONTO DEMANDADO</b><br><h2>{format_guaranies(monto_demandado_display)}</h2></div>", unsafe_allow_html=True)

    with col_kpi_3:
        color_saldo = '#FFB5B5' if saldo_demandado > 0 else '#B5FFB5'
        # Usamos el estilo base y solo cambiamos el color del texto del KPI del saldo
        st.markdown(f"<div style='{kpi_style}'><b>SALDO PENDIENTE</b><br><h2 style='color:{color_saldo};'>{format_guaranies(saldo_demandado)}</h2></div>", unsafe_allow_html=True)

    st.markdown("---")

    # D. Presentación de Datos del Cliente 
    with st.expander("Detalles del Cliente", expanded=True):
        col_info, col_tabla = st.columns([3, 7])
        
        with col_info:
            st.subheader("Datos del Cliente")
            st.markdown(f"**Cliente**: {cliente_data['NOMBRE_CLIENTE'].title()}")
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
    st.subheader("DETALLE DE PAGOS POR PERÍODO, AÑO, MES Y FORMA (CHEQUE JUDICIAL / EFECTIVO-OTROS)")
        
    df_display = df_pivot.copy()
    
    # Capitalizamos los periodos para la visualización
    df_display['PERIODO'] = df_display['PERIODO'].astype(str).str.title()
    
    cols_to_format = [c for c in df_display.columns if c not in ['PERIODO', 'AÑO', 'MES']]
    for col in cols_to_format:
        df_display[col] = df_display[col].apply(lambda x: format_guaranies(x) if x != 0 else '-')
    
    def highlight_total_row(row):
        # La fila de TOTAL COBRADO es la de margen que se capitaliza a 'Total Cobrado'
        style = 'background-color: #293C47; font-weight: bold; color: white;' if row['PERIODO'] == 'Total Cobrado' else ''
        return [style] * len(row)

    styled_df = df_display.style.apply(highlight_total_row, axis=1)

    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def mostrar_resultados(df_filtrado_abogado):
    """Realiza la búsqueda final, maneja múltiples resultados y muestra el dashboard."""
    
    cedula = st.session_state.get('cedula', '').strip()
    # Ya convertimos a minúsculas para la búsqueda
    nombre = st.session_state.get('nombre', '').strip().lower()

    filtro_final = pd.Series([False] * len(df_filtrado_abogado))
    
    if cedula:
        # Filtro de cédula (solo números o texto)
        filtro_cedula = df_filtrado_abogado['NRO_CEDULA'].str.contains(cedula, case=False, na=False)
        filtro_final = filtro_final | filtro_cedula
        
    if nombre:
        # Filtro de nombre (ya en minúsculas)
        filtro_nombre = df_filtrado_abogado['NOMBRE_CLIENTE'].str.contains(nombre, case=True, na=False)
        filtro_final = filtro_final | filtro_nombre

    if not cedula and not nombre:
        st.warning("Ingrese el número de cédula o el nombre del cliente para buscar.")
        return
        
    df_resultados_match = df_filtrado_abogado[filtro_final].copy()

    if df_resultados_match.empty:
        st.warning(f"No se encontraron resultados para la búsqueda '{cedula or nombre}'.")
        return
    
    # *** Lógica de Manejo de Múltiples Resultados (CORREGIDA) ***
    clientes_encontrados = df_resultados_match.drop_duplicates(subset=['NRO_CEDULA']).copy()
    
    # Crear un nombre de visualización combinado
    clientes_encontrados['DISPLAY_NAME'] = clientes_encontrados.apply(
        lambda row: f"{row['NOMBRE_CLIENTE'].title()} - {row['NRO_CEDULA']}", 
        axis=1
    )
    
    # Inicializar la cédula seleccionada con el primer resultado
    cliente_seleccionado_cedula = clientes_encontrados['NRO_CEDULA'].iloc[0]
    
    # Si se encontraron múltiples clientes, se pide al usuario que elija
    if len(clientes_encontrados) > 1:
        st.subheader(f"Se encontraron {len(clientes_encontrados)} clientes. Seleccione uno:")
        
        # Usamos NRO_CEDULA como valor interno y la función de formato para la etiqueta visual
        cliente_seleccionado_cedula = st.selectbox(
            "Seleccione el cliente a visualizar", 
            options=clientes_encontrados['NRO_CEDULA'].tolist(), # Las opciones son las cédulas únicas
            index=0, # Selecciona el primero por defecto
            # La función de formato busca el DISPLAY_NAME correspondiente a la cédula
            format_func=lambda cedula: clientes_encontrados.loc[clientes_encontrados['NRO_CEDULA'] == cedula, 'DISPLAY_NAME'].iloc[0], 
            key='cliente_selector'
        )
    # *** FIN DE LÓGICA DE SELECCIÓN ***

    # Filtro final basado en la cédula seleccionada (funciona con el valor del selectbox o el valor por defecto)
    df_resultados_final = df_filtrado_abogado[df_filtrado_abogado['NRO_CEDULA'] == cliente_seleccionado_cedula].copy()
        
    # Mostrar el dashboard
    mostrar_dashboard_resultados(df_resultados_final)


def app_principal():
    """Muestra la interfaz de búsqueda y aplica el filtro de seguridad."""
    
    filtro_abogado = st.session_state.get('filtro_abogado') # Ya está en minúsculas
    
    st.sidebar.title("Bienvenido al Sistema")
    # Capitalizamos la primera letra del nombre del abogado para mostrarlo bonito en el sidebar
    abogado_display = filtro_abogado.title() if filtro_abogado != 'todos' else 'TODOS'
    st.sidebar.info(f"Filtro de Seguridad Activo: {abogado_display}")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.session_state['filtro_abogado'] = None
        st.session_state['search_active'] = False
        st.session_state['cedula'] = ''
        st.session_state['nombre'] = ''
        # Limpiar cualquier estado de selección para evitar errores al volver a iniciar
        if 'cliente_selector' in st.session_state:
            del st.session_state['cliente_selector']
        st.rerun()

    # 1. Aplicar el Filtro de Seguridad al DataFrame
    if filtro_abogado == 'todos':
        df_filtrado_abogado = df_base.copy()
    elif filtro_abogado:
        # El filtro_abogado y la columna 'ABOGADO' ya están en minúsculas
        df_filtrado_abogado = df_base[df_base['ABOGADO'] == filtro_abogado].copy()
    else:
        st.warning("No se pudo aplicar el filtro de seguridad. Vuelva a iniciar sesión.")
        return
    
    st.header("Módulo de Búsqueda de Clientes")
    st.markdown("---")
    
    # 2. Campos de Búsqueda Dual
    col_cedula, col_nombre, col_button, col_espacio = st.columns([2, 2, 1, 3])
    
    cedula_busqueda = col_cedula.text_input("NRO DE CEDULA", key='cedula_input')
    nombre_busqueda = col_nombre.text_input("NOMBRE DE CLIENTE", key='nombre_input')
    
    if col_button.button("🔎 Buscar", use_container_width=True):
        st.session_state['search_active'] = True
        st.session_state['cedula'] = cedula_busqueda
        st.session_state['nombre'] = nombre_busqueda
        # Limpiar el selector anterior para forzar la selección si es necesario
        if 'cliente_selector' in st.session_state:
            del st.session_state['cliente_selector']
        st.rerun()
        
    st.markdown("---")
        
    if st.session_state.get('search_active', False):
        mostrar_resultados(df_filtrado_abogado)


# --- Función Principal ---
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
    # Si uno de los archivos falla, detenemos la ejecución y mostramos el error del archivo faltante
    else:
        st.stop()
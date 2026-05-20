import streamlit as st
import requests
import os
from streamlit_option_menu import option_menu

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Heladería Profesional", layout="wide", page_icon="🍦")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* --- FUENTE GLOBAL --- */
    html, body, .main, .block-container {
        font-family: 'Outfit', sans-serif !important;
    }

    /* --- FONDO PRINCIPAL (contraste oscuro) --- */
    .stApp {
        background-color: #f0f2f6;
    }
    
    /* --- FORZAR TEXTO OSCURO EN EL CUERPO PRINCIPAL --- */
    .main .block-container p,
    .main .block-container label,
    .main .block-container div,
    .main .block-container span,
    .main .block-container li,
    .stMarkdown p,
    .stMarkdown span,
    .stMarkdown li {
        color: #1a1a2e !important;
    }

    /* --- SIDEBAR ROSA INTENSO --- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e91e8c 0%, #c2185b 100%);
        border-right: 3px solid #ad1457;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* --- ENCABEZADOS DE SECCIÓN --- */
    .section-header {
        background: linear-gradient(135deg, #e91e8c, #f06292);
        color: white !important;
        padding: 20px 25px;
        border-radius: 16px;
        margin-bottom: 28px;
        box-shadow: 0 6px 20px rgba(233, 30, 140, 0.3);
    }
    .section-header h1, .section-header p {
        color: white !important;
        margin: 0;
    }
    .section-header h1 { font-size: 1.8rem; font-weight: 700; }
    .section-header p { font-size: 0.95rem; opacity: 0.9; margin-top: 4px; }

    /* --- TARJETAS DE HELADOS --- */
    .flavor-card {
        background: white;
        padding: 25px 20px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border: 2px solid #f8bbd0;
        margin-bottom: 10px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .flavor-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 10px 25px rgba(233, 30, 140, 0.2);
        border-color: #e91e8c;
    }
    .flavor-icon { font-size: 2.8rem; margin-bottom: 8px; }
    .flavor-name { font-size: 1.3rem; font-weight: 700; color: #c2185b !important; }
    .flavor-price { font-size: 1.25rem; color: #2e7d32 !important; font-weight: 600; margin: 4px 0; }
    .flavor-stock { font-size: 0.9rem; color: #555 !important; }

    /* --- CHAT: FONDO BLANCO Y TEXTO OSCURO --- */
    [data-testid="stChatMessage"] {
        background-color: white !important;
        border: 1px solid #e0e0e0;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 10px;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div {
        color: #1a1a2e !important;
    }

    /* --- INPUT DE CHAT --- */
    [data-testid="stChatInput"] textarea {
        color: #1a1a2e !important;
        background-color: white !important;
    }

    /* --- FILAS DE VENTAS / COMPRAS --- */
    .item-row {
        background: white;
        border: 1px solid #f8bbd0;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
    }
    .item-row .item-name {
        font-size: 1rem;
        font-weight: 600;
        color: #1a1a2e !important;
    }
    .item-row .item-meta {
        font-size: 0.85rem;
        color: #555 !important;
        margin-top: 2px;
    }

    /* --- TABS --- */
    .stTabs [data-baseweb="tab"] {
        color: #555 !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #e91e8c !important;
        border-bottom: 2px solid #e91e8c;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES API ---
def check_api():
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        return r.status_code == 200
    except:
        return False

def get_inventario():
    try:
        r = requests.get(f"{API_URL}/inventario")
        return r.json() if r.status_code == 200 else []
    except:
        return []

def get_ventas():
    try:
        r = requests.get(f"{API_URL}/ventas")
        return r.json() if r.status_code == 200 else []
    except:
        return []

def get_compras():
    try:
        r = requests.get(f"{API_URL}/compras")
        return r.json() if r.status_code == 200 else []
    except:
        return []

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='text-align:center; color:white;'>🍦 Heladería</h1>", unsafe_allow_html=True)

    if not check_api():
        st.error("⚠️ Servidor Offline")
    else:
        st.success("✅ Servidor Online")

    selected = option_menu(
        menu_title=None,
        options=["Panel IA", "Inventario", "Ventas", "Compras"],
        icons=["robot", "box-seam", "cart-check", "bag-plus"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "white", "font-size": "17px"},
            "nav-link": {"font-size": "15px", "color": "white", "text-align": "left",
                         "margin": "2px 0", "--hover-color": "rgba(255,255,255,0.2)"},
            "nav-link-selected": {"background-color": "white", "color": "#e91e8c", "font-weight": "700"},
        }
    )

    st.divider()
    st.markdown("<p style='color:white; font-weight:600;'>🎙️ Agente de Voz</p>", unsafe_allow_html=True)
    try:
        status_res = requests.get(f"{API_URL}/ai/status", timeout=1).json()
        voice_active = status_res.get("voice_active", False)
    except:
        voice_active = False

    on = st.toggle("Activar Micro", value=voice_active)
    if on != voice_active:
        try:
            requests.post(f"{API_URL}/ai/voice/toggle", json={"active": on})
            st.rerun()
        except:
            st.error("Error al conectar con la IA")
    
    if voice_active:
        st.markdown("<span style='color:#90EE90;'>● Escuchando...</span>", unsafe_allow_html=True)

# ======================= PÁGINAS =======================

# --- PANEL IA ---
if selected == "Panel IA":
    st.markdown('<div class="section-header"><h1>🤖 Asistente Inteligente</h1><p>Pregunta por el menú, disponibilidad o realiza pedidos</p></div>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "¡Hola! 👋 Soy tu asistente de heladería. Puedes preguntarme sobre nuestros sabores disponibles, precios o decirme qué quieres pedir. ¿En qué te ayudo hoy?"}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe aquí tu pregunta o pedido..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    res = requests.post(f"{API_URL}/ai/chat", json={"message": prompt}, timeout=60)
                    response = res.json().get("reply", "No pude procesar eso.")
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    msg_err = "No pude conectarme con la IA. Verifica que el servidor esté activo."
                    st.error(msg_err)

# --- INVENTARIO ---
elif selected == "Inventario":
    st.markdown('<div class="section-header"><h1>📦 Gestión de Inventario</h1><p>Controla tus sabores y existencias</p></div>', unsafe_allow_html=True)

    with st.expander("➕ Agregar nuevo sabor"):
        with st.form("new_flavor"):
            cols = st.columns(3)
            n_name = cols[0].text_input("Nombre del sabor")
            n_price = cols[1].number_input("Precio ($)", min_value=0.0, step=100.0)
            n_stock = cols[2].number_input("Stock inicial", min_value=0, step=1)
            if st.form_submit_button("✅ Agregar", use_container_width=True):
                r = requests.post(f"{API_URL}/inventario", json={"nombre": n_name, "precio": n_price, "stock": n_stock})
                st.success("Sabor agregado.") if r.status_code == 200 else st.error("Error al agregar.")
                st.rerun()

    sabores = get_inventario()
    if not sabores:
        st.info("No hay sabores en el inventario.")
    else:
        cols = st.columns(3)
        for idx, s in enumerate(sabores):
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="flavor-card">
                    <div class="flavor-icon">🍦</div>
                    <div class="flavor-name">{s['nombre']}</div>
                    <div class="flavor-price">${s['precio']:,.0f}</div>
                    <div class="flavor-stock">Stock disponible: {s['stock']} uds</div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✏️ Editar", key=f"edit_{s['id']}", use_container_width=True):
                    st.session_state.edit_id = s["id"]
                    st.session_state.edit_data = s
                if c2.button("🗑️ Borrar", key=f"del_{s['id']}", use_container_width=True):
                    requests.delete(f"{API_URL}/inventario/{s['id']}")
                    st.rerun()

        if "edit_id" in st.session_state:
            st.divider()
            st.markdown("### ✏️ Editar Sabor")
            with st.form("edit_form"):
                d = st.session_state.edit_data
                cols = st.columns(3)
                en = cols[0].text_input("Nombre", value=d["nombre"])
                ep = cols[1].number_input("Precio", value=float(d["precio"]), step=100.0)
                es = cols[2].number_input("Stock", value=int(d["stock"]), step=1)
                if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                    requests.put(f"{API_URL}/inventario", json={"id": d["id"], "nombre": en, "precio": ep, "stock": es})
                    del st.session_state.edit_id
                    st.rerun()

# --- VENTAS ---
elif selected == "Ventas":
    st.markdown('<div class="section-header"><h1>💰 Registro de Ventas</h1><p>Registra pedidos de forma manual</p></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🛒 Nueva Venta", "📜 Historial"])

    with tab1:
        sabores = get_inventario()
        items_venta = []
        total = 0
        if not sabores:
            st.info("No hay sabores disponibles.")
        else:
            # Encabezado de tabla
            h1, h2, h3 = st.columns([4, 2, 2])
            h1.markdown("**🍦 Sabor**")
            h2.markdown("**Cantidad**")
            h3.markdown("**Subtotal**")
            st.divider()

            for s in sabores:
                c1, c2, c3 = st.columns([4, 2, 2])
                # Texto forzado con markdown HTML para garantizar visibilidad
                c1.markdown(
                    f"<p style='color:#1a1a2e; font-size:1rem; font-weight:600; margin:10px 0;'>"
                    f"{s['nombre']}<br>"
                    f"<span style='color:#888; font-size:0.85rem;'>${s['precio']:,.0f} c/u · Stock: {s['stock']}</span>"
                    f"</p>",
                    unsafe_allow_html=True
                )
                cant = c2.number_input("", min_value=0, max_value=s["stock"], key=f"v_{s['id']}", label_visibility="collapsed")
                sub = cant * s["precio"]
                c3.markdown(
                    f"<p style='color:#2e7d32; font-weight:700; font-size:1rem; margin:10px 0;'>${sub:,.0f}</p>",
                    unsafe_allow_html=True
                )
                if cant > 0:
                    items_venta.append({"idSabor": s["id"], "cantidad": cant})
                    total += sub

            st.divider()
            st.markdown(f"<h2 style='color:#1a1a2e;'>Total: <span style='color:#2e7d32;'>${total:,.0f}</span></h2>", unsafe_allow_html=True)
            if st.button("🛒 Finalizar Venta", use_container_width=True, disabled=total == 0):
                res = requests.post(f"{API_URL}/ventas", json={"items": items_venta})
                if res.status_code == 200:
                    st.balloons()
                    st.success(f"✅ Venta #{res.json()['venta_id']} registrada por ${res.json()['total']:,.0f}")
                    st.rerun()
                else:
                    st.error(res.json().get("detail", "Error al procesar."))

    with tab2:
        ventas_h = get_ventas()
        if not ventas_h:
            st.info("No hay ventas registradas aún.")
        for v in ventas_h:
            with st.expander(f"🧾 Venta #{v['id']} — {v['fecha']} — **${v['total']:,.0f}**"):
                for item in v["items"]:
                    st.markdown(
                        f"<p style='color:#1a1a2e;'>• <b>{item['nombre']}</b> × {item['cantidad']} "
                        f"<span style='color:#888;'>(${item['precio_unitario']:,.0f} c/u)</span></p>",
                        unsafe_allow_html=True
                    )

# --- COMPRAS ---
elif selected == "Compras":
    st.markdown('<div class="section-header"><h1>🚚 Abastecimiento y Compras</h1><p>Gestiona la entrada de mercancía</p></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["➕ Registrar Compra", "📋 Historial"])

    with tab1:
        sabores = get_inventario()
        items_compra = []
        total_costo = 0
        if not sabores:
            st.info("No hay sabores en el sistema.")
        else:
            h1, h2 = st.columns([4, 2])
            h1.markdown("**🍦 Sabor**")
            h2.markdown("**Cantidad a comprar**")
            st.divider()

            for s in sabores:
                c1, c2 = st.columns([4, 2])
                c1.markdown(
                    f"<p style='color:#1a1a2e; font-size:1rem; font-weight:600; margin:10px 0;'>"
                    f"{s['nombre']}<br>"
                    f"<span style='color:#888; font-size:0.85rem;'>Stock actual: {s['stock']} uds</span>"
                    f"</p>",
                    unsafe_allow_html=True
                )
                cant = c2.number_input("", min_value=0, step=1, key=f"c_{s['id']}", label_visibility="collapsed")
                if cant > 0:
                    items_compra.append({"sabor_id": s["id"], "cantidad_comprada": cant})
                    total_costo += cant * s["precio"]

            st.divider()
            st.markdown(f"<h2 style='color:#1a1a2e;'>Inversión total: <span style='color:#1565c0;'>${total_costo:,.0f}</span></h2>", unsafe_allow_html=True)
            if st.button("📦 Registrar Entrada", use_container_width=True, disabled=total_costo == 0):
                res = requests.post(f"{API_URL}/compras", json={"items": items_compra, "total_compra": total_costo})
                if res.status_code == 200:
                    st.success("✅ Inventario reabastecido correctamente.")
                    st.rerun()
                else:
                    st.error("Error al registrar la compra.")

    with tab2:
        compras_h = get_compras()
        if not compras_h:
            st.info("No hay compras registradas aún.")
        for c in compras_h:
            with st.expander(f"📦 Compra #{c['id']} — {c['fecha']} — **${c['total_compra']:,.0f}**"):
                for item in c["items"]:
                    st.markdown(
                        f"<p style='color:#1a1a2e;'>• <b>{item['nombre']}</b> × {item['cantidad_comprada']} unidades</p>",
                        unsafe_allow_html=True
                    )
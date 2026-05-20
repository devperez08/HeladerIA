from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sqlite3
import sys
import os
import time
import json
import re
import subprocess
import threading
from API.ai_logic import extraer_datos_pedido, hablar

# Ajustar rutas para importar db/database.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from DataBase.Conexion import DB_PATH

app = FastAPI(title="Heladeria Unificada API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

voice_agent_process = None
voice_agent_active = False

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- LOGICA INTERNA ---
def realizar_venta_interna(items: List[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        total_venta = 0.0
        lista_detalle = []
        
        for item in items:
            id_sabor = item.get("idSabor")
            cantidad = item.get("cantidad")
            sabor = conn.execute("SELECT nombre, stock, precio FROM sabores WHERE id = ?", (id_sabor,)).fetchone()
            if not sabor: 
                raise Exception(f"ID {id_sabor} no existe")
            if sabor["stock"] < cantidad:
                raise Exception(f"Stock insuficiente para {sabor['nombre']}")
            
            total_venta += (sabor["precio"] * cantidad)
            lista_detalle.append((id_sabor, cantidad, sabor["precio"]))
        
        cursor.execute("INSERT INTO ventas (total) VALUES (?)", (total_venta,))
        venta_id = cursor.lastrowid
        
        for det in lista_detalle:
            cursor.execute("INSERT INTO detalle_ventas (venta_id, sabor_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)", (venta_id, det[0], det[1], det[2],))
        
        conn.commit()
        return {"mensaje": "Venta realizada", "venta_id": venta_id, "total": total_venta}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- MODELOS ---
class Sabor(BaseModel):
    id : int
    nombre : str
    precio : float
    stock : int

class NuevoSabor(BaseModel):
    nombre: str
    precio : float
    stock : int

class VentaItem(BaseModel):
    idSabor: int
    cantidad: int

class Venta(BaseModel):
    items: List[VentaItem]

class ItemCompra(BaseModel):
    sabor_id: int
    cantidad_comprada: int

class Compra(BaseModel):
    items: List[ItemCompra]
    total_compra: float

class AIChatRequest(BaseModel):
    message: str

class AIVoiceToggle(BaseModel):
    active: bool

# --- RUTAS ---
@app.get("/health")
def root():
    return {"status": "online", "service": "heladeria_api"}

@app.get("/inventario")
def inventario():
    conn = get_db_connection()
    try:
        sabores = conn.execute('SELECT * FROM sabores').fetchall()
        return [dict(row) for row in sabores]
    finally:
        conn.close()

@app.post("/inventario")
def agregar_sabor(sabor: NuevoSabor):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO sabores (nombre, precio, stock) VALUES (?, ?, ?)", 
                     (sabor.nombre, sabor.precio, sabor.stock))
        conn.commit()
        return {"mensaje": "Sabor agregado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.put("/inventario")
def actualizar_sabor(sabor: Sabor):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE sabores SET nombre=?, precio=?, stock=? WHERE id=?", 
                     (sabor.nombre, sabor.precio, sabor.stock, sabor.id))
        conn.commit()
        return {"mensaje": "Sabor actualizado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.delete("/inventario/{sabor_id}")
def eliminar_sabor(sabor_id: int):
    conn = get_db_connection()
    try:
        # Verificar ventas
        venta_check = conn.execute("SELECT COUNT(*) FROM detalle_ventas WHERE sabor_id = ?", (sabor_id,)).fetchone()
        if venta_check[0] > 0:
            raise HTTPException(status_code=400, detail="No se puede eliminar un sabor con ventas.")
        
        conn.execute("DELETE FROM sabores WHERE id = ?", (sabor_id,))
        conn.commit()
        return {"mensaje": "Sabor eliminado"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/ventas")
def registrar_venta(venta: Venta):
    try:
        return realizar_venta_interna([item.dict() for item in venta.items])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/ventas")
def listar_ventas():
    conn = get_db_connection()
    try:
        ventas = conn.execute('SELECT * FROM ventas ORDER BY fecha DESC').fetchall()
        resultado = []
        for v in ventas:
            detalles = conn.execute('SELECT dv.*, s.nombre FROM detalle_ventas dv JOIN sabores s ON dv.sabor_id = s.id WHERE dv.venta_id = ?', (v["id"],)).fetchall()
            venta_dict = dict(v)
            venta_dict["items"] = [dict(d) for d in detalles]
            resultado.append(venta_dict)
        return resultado
    finally:
        conn.close()

@app.post("/compras")
def registrar_compra(compra: Compra):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("INSERT INTO compras (total_compra) VALUES (?)", (compra.total_compra,))
        compra_id = cursor.lastrowid
        for item in compra.items:
            cursor.execute("INSERT INTO detalle_compras (compra_id, sabor_id, cantidad_comprada) VALUES (?, ?, ?)", (compra_id, item.sabor_id, item.cantidad_comprada,))
        conn.commit()
        return {"mensaje": "Compra registrada con éxito", "compra_id": compra_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- RUTAS DE IA ---

# Mapa de palabras numéricas a dígitos
PALABRAS_NUMEROS = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "veinte": 20, "treinta": 30, "cincuenta": 50, "cien": 100,
}

def extraer_cantidad(texto: str) -> int:
    """Extrae un número del texto, soportando dígitos y palabras."""
    # Primero buscar dígitos (ej: "9 helados")
    match = re.search(r'\b(\d+)\b', texto)
    if match:
        return max(1, int(match.group(1)))
    # Luego buscar palabras numéricas
    texto_lower = texto.lower()
    for palabra, valor in PALABRAS_NUMEROS.items():
        if re.search(rf'\b{palabra}\b', texto_lower):
            return valor
    return 1

def detectar_pedido(mensaje: str, sabores: list):
    """
    Detecta si el mensaje es un pedido usando Python puro.
    Retorna (sabor_dict, cantidad) si es pedido, (None, 0) si es consulta.
    """
    msg_lower = mensaje.lower()
    
    # 1. Detectar si parece una pregunta (Consulta) - Lista ampliada y más flexible
    palabras_pregunta = [
        "que", "qué", "como", "cómo", "hay", "tienes", "disponible", 
        "precio", "cuanto", "cuánto", "uanto", "uánto", "costar", "cuesta", "valen", 
        "lista", "menu", "menú", "?", "informacion", "info"
    ]
    parece_pregunta = any(p in msg_lower for p in palabras_pregunta)

    # 2. Palabras clave que indican intención de compra EXPLICITA
    palabras_compra = ["quiero", "dame", "quisiera", "deme", "pido", "necesito", 
                       "compro", "me das", "me da", "ponme", "párame", "tráeme", "vende", "véndeme", "registrar"]
    intencion_compra = any(p in msg_lower for p in palabras_compra)
    
    # 3. Detectar si hay un número o palabra numérica (ej: "un", "9")
    tiene_numero = bool(re.search(r'\b\d+\b', msg_lower))
    if not tiene_numero:
        for palabra in PALABRAS_NUMEROS:
            if re.search(rf'\b{palabra}\b', msg_lower):
                tiene_numero = True
                break

    # LÓGICA DE DECISIÓN REFORZADA:
    # Si parece pregunta, solo es pedido si hay una intención de compra MUY explícita (ej: "¿Me vendes 2?")
    if parece_pregunta and not intencion_compra:
        return None, 0

    # Si no hay intención de compra Y no hay un número claro, es consulta.
    if not intencion_compra and not tiene_numero:
        return None, 0
    
    # 4. Buscar qué sabor menciona el mensaje
    sabor_encontrado = None
    mejor_match_len = 0
    for s in sabores:
        nombre_lower = s["nombre"].lower()
        # Coincidencia exacta o palabra completa para evitar falsos positivos
        if re.search(rf'\b{re.escape(nombre_lower)}\b', msg_lower):
            if len(nombre_lower) > mejor_match_len:
                sabor_encontrado = s
                mejor_match_len = len(nombre_lower)

    if sabor_encontrado:
        # Si hay intención de compra, procedemos.
        # Si NO hay intención pero hay un número y un sabor (ej: "2 de fresa"), procedemos.
        return sabor_encontrado, extraer_cantidad(mensaje)
    
    return None, 0


@app.post("/ai/chat")
def ai_chat(request: AIChatRequest):
    import ollama as _ollama

    # 1. Siempre consultar el catálogo fresco de la BD
    conn = get_db_connection()
    sabores_rows = conn.execute('SELECT id, nombre, precio, stock FROM sabores').fetchall()
    conn.close()
    sabores = [dict(s) for s in sabores_rows]
    modelo = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

    # 2. DETECCIÓN 100% PYTHON — sin depender del modelo para lógica de negocio
    sabor_encontrado, cantidad = detectar_pedido(request.message, sabores)
    print(f"DEBUG Python detectó: sabor={sabor_encontrado and sabor_encontrado['nombre']}, cantidad={cantidad}")

    # 3. ES UN PEDIDO → procesar venta con datos reales de la BD
    if sabor_encontrado and cantidad > 0:
        if sabor_encontrado["stock"] < cantidad:
            return {"reply": f"⚠️ Solo tenemos **{sabor_encontrado['stock']} unidades** de **{sabor_encontrado['nombre']}** disponibles. ¿Quieres pedir esa cantidad?"}

        try:
            resultado = realizar_venta_interna([{"idSabor": sabor_encontrado["id"], "cantidad": cantidad}])
            return {
                "reply": (
                    f"✅ ¡Pedido registrado!\n\n"
                    f"**{cantidad}x {sabor_encontrado['nombre']}**\n"
                    f"Precio unitario: **${sabor_encontrado['precio']:,.0f}**\n"
                    f"Total: **${resultado['total']:,.0f}** · Venta #**{resultado['venta_id']}**\n\n"
                    f"¡Que lo disfrutes! 🍦"
                )
            }
        except Exception as e:
            return {"reply": f"⚠️ Error al registrar el pedido: {str(e)}"}

    # 3.5 CASO ESPECIAL: Quiso pedir algo pero el sabor no existe (Detección en Python)
    palabras_compra = ["quiero", "dame", "quisiera", "pido", "vende", "compra"]
    if any(p in request.message.lower() for p in palabras_compra) and not sabor_encontrado:
        lista_sabores = ", ".join([s["nombre"] for s in sabores])
        return {"reply": f"🍦 Lo siento, no tenemos ese sabor. Nuestros sabores actuales son: **{lista_sabores}**."}

    # 4. ES UNA CONSULTA → LLM responde amigablemente (Prompt Minimalista)
    catalogo_resumen = ", ".join([f"{s['nombre']} (${s['precio']:,.0f})" for s in sabores])
    respuesta_prompt = f"""Vendedor de heladería. 
Catálogo: {catalogo_resumen}
Cliente: {request.message}
Responde breve (1 frase):"""

    try:
        resp = _ollama.chat(
            model=modelo,
            messages=[{'role': 'user', 'content': respuesta_prompt}]
        )
        return {"reply": resp['message']['content'].strip()}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}

@app.get("/ai/status")
def ai_status():
    return {"voice_active": voice_agent_active}

@app.post("/ai/voice/toggle")
def ai_voice_toggle(request: AIVoiceToggle):
    global voice_agent_process, voice_agent_active
    if request.active:
        if not voice_agent_active:
            # Usar sys.executable para asegurar que usa el mismo entorno (VENV)
            log_file = open("voice_agent.log", "a")
            voice_agent_process = subprocess.Popen(
                [sys.executable, "Local_agent_voz.py"],
                stdout=log_file,
                stderr=log_file
            )
            voice_agent_active = True
            return {"mensaje": "Agente encendido", "active": True}
    else:
        if voice_agent_active and voice_agent_process:
            print("🛑 Deteniendo agente de voz...")
            voice_agent_process.kill() # Forzar detención inmediata
            voice_agent_process.wait() # Asegurar cierre de recursos
            voice_agent_process = None
            voice_agent_active = False
            return {"mensaje": "Agente apagado", "active": False}
        return {"mensaje": "Agente ya estaba apagado", "active": False}
    return {"active": voice_agent_active}
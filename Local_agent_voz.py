import ollama
import requests
import json
import subprocess
import pyaudio
from vosk import Model, KaldiRecognizer

import os

# --- CONFIGURACIÓN ---
API_URL = os.getenv("API_URL", "http://localhost:8000")
MODELO = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
PIPER_BIN = "./piper/piper" # Ajusta según tu ruta de Piper
VOZ_MODELO = "voz_es.onnx"

# Cargar el modelo de Vosk
print("Cargando modelo de escucha Vosk...")
modelo_escucha = Model("modelo_vosk")

def escuchar_cliente():
    """Captura el audio del micrófono y lo convierte a texto de forma offline."""
    if not os.path.exists("modelo_vosk"):
        print("❌ ERROR: No se encontró la carpeta 'modelo_vosk'.")
        return ""
    
    try:
        reconocedor = KaldiRecognizer(modelo_escucha, 16000)
    except Exception as e:
        print(f"❌ ERROR al inicializar KaldiRecognizer: {e}")
        return ""
        
    microfono = pyaudio.PyAudio()
    
    stream = microfono.open(format=pyaudio.paInt16, channels=1, 
                            rate=16000, input=True, frames_per_buffer=8192)
    
    print("\n🎤 Escuchando... (Habla ahora)")
    stream.start_stream()

    texto_capturado = ""
    try:
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if reconocedor.AcceptWaveform(data):
                resultado = json.loads(reconocedor.Result())
                texto_capturado = resultado.get("text", "")
                if texto_capturado:
                    print(f"✅ Cliente dijo: {texto_capturado}")
                    break
            else:
                # Opcional: Imprimir lo que va entendiendo en tiempo real
                parcial = json.loads(reconocedor.PartialResult())
                if parcial.get("partial"):
                    print(f"Reading...: {parcial.get('partial')}", end="\r")
                    
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        microfono.terminate()
        
    return texto_capturado

def hablar(texto):
    print(f"🤖 Agente dice: {texto}")
    if not os.path.exists(PIPER_BIN):
        print(f"❌ ERROR: No se encontró el binario de Piper en {PIPER_BIN}")
        return
    if not os.path.exists(VOZ_MODELO):
        print(f"❌ ERROR: No se encontró el modelo de voz {VOZ_MODELO}")
        return

    clean_text = texto.replace('"', '').replace('#', '')
    try:
        cmd = f'echo "{clean_text}" | {PIPER_BIN} --model {VOZ_MODELO} --output_file salida.wav'
        subprocess.run(cmd, shell=True, check=True)
        subprocess.run("aplay -q salida.wav", shell=True)
    except Exception as e:
        print(f"❌ Error en TTS/Audio: {e}")

def decodificar_y_vender(texto_cliente, catalogo_sabores):
    """Convierte la voz a JSON usando Ollama y valida con FastAPI."""
    # Formato más claro para modelos pequeños
    mensaje_sistema = f"""
    Eres un asistente que solo extrae datos.
    Lista de sabores disponibles:
    {catalogo_sabores}

    Instrucciones:
    1. Escucha el sabor que pide el cliente.
    2. Busca el ID correspondiente en la lista de arriba.
    3. Si dice "un", "una" o no dice cantidad, usa 1.
    4. Responde SOLO con JSON: {{"idSabor": ID, "cantidad": CANTIDAD}}
    5. Si el sabor no existe, responde: {{"error": "no_existe"}}
    """

    # Forzamos a Llama 3.2 a devolver formato JSON
    respuesta_ia = ollama.chat(
        model=MODELO, 
        messages=[
            {'role': 'system', 'content': mensaje_sistema},
            {'role': 'user', 'content': texto_cliente}
        ],
        format="json"
    )

    texto_json = respuesta_ia['message']['content']
    print(f"DEBUG IA: {texto_json}") # Para ver qué generó Ollama

    try:
        datos_pedido = json.loads(texto_json)
        print(f"DEBUG: JSON procesado: {datos_pedido}")

        if "error" in datos_pedido or not datos_pedido.get("idSabor"):
            return "Lo siento, no logré entender qué sabor quieres. ¿Puedes repetirlo?"

        payload_api = {
            "items": [
                {
                    "idSabor": int(datos_pedido.get("idSabor")),
                    "cantidad": int(datos_pedido.get("cantidad", 1))
                }
            ]
        }

        print(f"DEBUG: Enviando a API: {payload_api}")
        respuesta_api = requests.post(f"{API_URL}/ventas", json=payload_api)

        if respuesta_api.status_code == 200:
            print("DEBUG: Venta exitosa")
            return "¡Excelente elección! Pedido procesado y descontado del inventario."
        else:
            error_msg = respuesta_api.json().get("detail", "Error desconocido")
            print(f"DEBUG: Error API ({respuesta_api.status_code}): {error_msg}")
            return f"Hubo un problema: {error_msg}"

    except json.JSONDecodeError:
        return "Hubo un problema interno procesando tu pedido, por favor intenta de nuevo."

# --- BUCLE PRINCIPAL ---
def iniciar_agente():
    # 1. Obtenemos el catálogo real desde la ruta correcta (/inventario)
    print("Conectando con la base de datos de la heladería...")
    try:
        respuesta_catalogo = requests.get(f"{API_URL}/inventario")
        if respuesta_catalogo.status_code == 200:
            lista_sabores = respuesta_catalogo.json()
            # Formateamos el catálogo sin mostrar el stock directamente para evitar confusiones de la IA
            catalogo_sabores = ", ".join([f'ID {s["id"]}: {s["nombre"]}' for s in lista_sabores])
        else:
            print(f"❌ Error API: {respuesta_catalogo.status_code}")
            catalogo_sabores = "Error al obtener catálogo."
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se pudo conectar a la API. ¿Está Uvicorn encendido?")
        return

    print(f"Catálogo cargado: {catalogo_sabores}")
    print("📢 Reproduciendo saludo inicial...")
    hablar("Hola, bienvenido a la heladería. ¿Qué sabor te gustaría llevar hoy?")
    
    while True:
        # 1. Refrescar el catálogo en cada iteración para detectar nuevos sabores/precios
        try:
            res_cat = requests.get(f"{API_URL}/inventario")
            if res_cat.status_code == 200:
                lista_sabores = res_cat.json()
                catalogo_sabores = "\n".join([f'- Sabor: {s["nombre"]} (ID: {s["id"]})' for s in lista_sabores])
            else:
                catalogo_sabores = "Error al obtener catálogo."
        except:
            catalogo_sabores = "Error de conexión con API."

        usuario_input = escuchar_cliente()
        
        if "salir" in usuario_input.lower() or "adiós" in usuario_input.lower():
            hablar("Hasta luego. Vuelve pronto.")
            break
            
        if usuario_input: 
            respuesta_final = decodificar_y_vender(usuario_input, catalogo_sabores)
            hablar(respuesta_final)

if __name__ == "__main__":
    iniciar_agente()
import ollama
import json
import subprocess
import os

# --- CONFIGURACIÓN ---
MODELO = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
PIPER_BIN = "./piper/piper"
VOZ_MODELO = "voz_es.onnx"

def hablar(texto):
    """Convierte el texto en voz usando Piper y lo reproduce localmente."""
    print(f"\n🤖 Agente dice: {texto}")
    clean_text = texto.replace('"', '').replace('#', '')
    try:
        # Asegurarse de que el directorio del binario es correcto
        cmd = f'echo "{clean_text}" | {PIPER_BIN} --model {VOZ_MODELO} --output_file salida.wav'
        subprocess.run(cmd, shell=True, check=True)
        subprocess.run("aplay -q salida.wav", shell=True)
    except Exception as e:
        print(f"Error en TTS/Audio: {e}")

def extraer_datos_pedido(texto_cliente, catalogo_sabores):
    """Usa Ollama para extraer sabor e ID del texto del cliente."""
    try:
        mensaje_sistema = f"""
        Eres un extractor de datos de una heladería profesional. 
        Tu único objetivo es extraer el sabor y la cantidad del pedido basándote en este catálogo: 
        {catalogo_sabores}
        
        Responde ÚNICAMENTE con un JSON válido con esta estructura exacta: {{"idSabor": ID_NUMERICO, "cantidad": CANTIDAD_NUMERICA}}
        
        Reglas:
        1. Mapea palabras de cantidad: "un", "una", "uno" -> 1, "dos" -> 2, "tres" -> 3, etc.
        2. Si el cliente NO especifica cantidad (ej: "quiero fresa"), usa cantidad 1.
        3. NUNCA uses el stock del producto como cantidad.
        4. Si el usuario dice algo que no es un pedido o no está en el catálogo, responde: {{"error": "No entendí"}}
        """

        respuesta_ia = ollama.chat(
            model=MODELO, 
            messages=[
                {'role': 'system', 'content': mensaje_sistema},
                {'role': 'user', 'content': texto_cliente}
            ],
            format="json"
        )

        return json.loads(respuesta_ia['message']['content'])
    except Exception as e:
        print(f"Error en Ollama: {e}")
        return {"error": str(e)}

from flask import Flask, request, jsonify, render_template
from groq import Groq
import base64
import os

app = Flask(__name__, template_folder="templates", static_folder=".")

# ==============================
# CONFIGURACIÓN API KEY (SEGURA)
# ==============================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY no configurada")
    client = None
else:
    client = Groq(api_key=GROQ_API_KEY)

MODELO_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
MODELO_TEXTO  = "llama-3.3-70b-versatile"


# ==============================
# FUNCIONES
# ==============================

def imagen_a_base64(file):
    try:
        img_bytes = file.read()
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        print("Error imagen:", e)
        return None


# ==============================
# RUTAS
# ==============================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():

    # 🔥 Evita crash si no hay API KEY
    if not client:
        return jsonify({"error": "❌ API KEY no configurada en el servidor"})

    falla = request.form.get("falla", "").strip()
    file = request.files.get("imagen")

    if not falla and not file:
        return jsonify({"error": "⚠️ Ingresa texto o imagen"})

    prompt = f"""
Eres un experto en diagnóstico técnico de actuadores Rotork (IQ3, CK y Pakscan).

Analiza la siguiente falla:
{falla}

Responde en español técnico con:
- Diagnóstico
- Causas probables
- Acciones recomendadas
"""

    try:
        if file:
            img_b64 = imagen_a_base64(file)

            if not img_b64:
                return jsonify({"error": "❌ Error procesando imagen"})

            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
            modelo = MODELO_VISION

        else:
            messages = [{
                "role": "user",
                "content": prompt
            }]
            modelo = MODELO_TEXTO

        response = client.chat.completions.create(
            model=modelo,
            messages=messages,
            max_tokens=1200,
            temperature=0.3
        )

        resultado = response.choices[0].message.content

        return jsonify({
            "resultado": resultado
        })

    except Exception as e:
        return jsonify({"error": f"❌ Error: {str(e)}"})


# ==============================
# MAIN (IMPORTANTE PARA RAILWAY)
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 🔥 CLAVE
    app.run(host="0.0.0.0", port=port)
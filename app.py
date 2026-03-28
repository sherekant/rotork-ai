from flask import Flask, request, jsonify, render_template
from groq import Groq
import base64
import os

app = Flask(__name__, template_folder="templates", static_folder=".")

# ==============================
# CONFIG API KEY (ROBUSTO)
# ==============================
def get_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("❌ GROQ_API_KEY no encontrada en entorno")
        return None

    try:
        return Groq(api_key=api_key)
    except Exception as e:
        print("❌ Error creando cliente:", e)
        return None


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

    client = get_client()

    if not client:
        return jsonify({"error": "❌ API KEY no configurada en el servidor (Railway)"})

    falla = request.form.get("falla", "").strip()
    file = request.files.get("imagen")

    if not falla and not file:
        return jsonify({"error": "⚠️ Ingresa texto o imagen"})

    prompt = f"""
Eres experto en diagnóstico técnico de actuadores Rotork (IQ3, CK y Pakscan).

Analiza la siguiente falla:
{falla}

Responde con:
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
            messages = [{"role": "user", "content": prompt}]
            modelo = MODELO_TEXTO

        response = client.chat.completions.create(
            model=modelo,
            messages=messages,
            max_tokens=1200
        )

        return jsonify({
            "resultado": response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
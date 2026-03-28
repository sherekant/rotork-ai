from flask import Flask, request, jsonify, render_template
from groq import Groq
import base64
import os

app = Flask(__name__, template_folder="templates", static_folder=".")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MODELO_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
MODELO_TEXTO  = "llama-3.3-70b-versatile"

def imagen_a_base64(file):
    try:
        # Leer directamente sin procesar con PIL
        img_bytes = file.read()
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        print("Error imagen:", e)
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analizar", methods=["POST"])
def analizar():
    falla = request.form.get("falla", "").strip()
    file = request.files.get("imagen")

    if not falla and not file:
        return jsonify({"error": "⚠️ Ingresa texto o imagen"})

    prompt = f"""
Eres experto en diagnóstico de actuadores Rotork.

Analiza esta falla:
{falla}

Responde con:
- Diagnóstico
- Causas
- Acciones
"""

    try:
        if file:
            img_b64 = imagen_a_base64(file)

            if not img_b64:
                return jsonify({"error": "Error imagen"})

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
            model = MODELO_VISION
        else:
            messages = [{"role": "user", "content": prompt}]
            model = MODELO_TEXTO

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1200
        )

        return jsonify({
            "resultado": response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
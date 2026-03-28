from flask import Flask, render_template, request, jsonify
import os
from groq import Groq

app = Flask(__name__)

# Leer API KEY desde Railway
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("⚠️ API KEY NO CONFIGURADA")
    client = None
else:
    print("✅ API KEY detectada")
    client = Groq(api_key=GROQ_API_KEY)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/analizar', methods=['POST'])
def analizar():
    if not client:
        return jsonify({
            "respuesta": "❌ API KEY no configurada en Railway"
        })

    try:
        descripcion = request.form.get('descripcion', '')
        sistema = request.form.get('sistema', 'General')

        prompt = f"""
Eres un experto en actuadores Rotork.

Sistema: {sistema}

Falla reportada:
{descripcion}

Entrega:
- Diagnóstico claro
- Posible causa
- Acción recomendada
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )

        return jsonify({
            "respuesta": response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({
            "respuesta": f"❌ Error: {str(e)}"
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
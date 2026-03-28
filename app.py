from flask import Flask, render_template, request, jsonify
import os
from groq import Groq

app = Flask(__name__)

# 🔑 Leer API KEY desde Railway
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

print("GROQ_API_KEY:", GROQ_API_KEY)

# Crear cliente
client = Groq(api_key=GROQ_API_KEY)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/analizar', methods=['POST'])
def analizar():
    try:
        descripcion = request.form.get('descripcion', '')

        if not descripcion:
            return jsonify({
                "respuesta": "⚠️ Debes escribir una falla"
            })

        prompt = f"""
Eres un ingeniero experto en actuadores Rotork.

Analiza la siguiente falla:

{descripcion}

Entrega:
- Diagnóstico
- Posibles causas
- Recomendaciones técnicas claras
"""

        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        respuesta = response.choices[0].message.content

        return jsonify({
            "respuesta": respuesta
        })

    except Exception as e:
        return jsonify({
            "respuesta": f"❌ Error: {str(e)}"
        })


# 🔥 IMPORTANTE PARA RAILWAY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
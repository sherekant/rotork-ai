from flask import Flask, request, jsonify, render_template
from groq import Groq
import requests
from bs4 import BeautifulSoup
import base64
import os

app = Flask(__name__)

# ── API KEY desde variable de entorno Railway ─────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY no configurada")
    client = None
else:
    print("✅ GROQ_API_KEY detectada")
    client = Groq(api_key=GROQ_API_KEY)

MODELO_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
MODELO_TEXTO  = "llama-3.3-70b-versatile"

# ── Traducciones español → inglés ─────────────────────────────────────────────
TRADUCCIONES = {
    "fase perdida":                   "loss of phase",
    "perdida de fase":                "loss of phase",
    "falla de fase":                  "phase failure",
    "lazo abierto":                   "open loop",
    "fallo de comunicacion":          "communication failure",
    "no comunica":                    "communication loss",
    "sin comunicacion":               "no communication",
    "falla de alimentacion":          "power supply failure",
    "falla de motor":                 "motor fault",
    "motor parado":                   "motor stall",
    "traba de torque":                "torque trip",
    "falla de torque":                "torque fault",
    "valvula trabada":                "valve stuck",
    "no abre":                        "fails to open",
    "no cierra":                      "fails to close",
    "no responde":                    "no response",
    "falla de posicion":              "position fault",
    "falla de bateria":               "battery fault",
    "bateria baja":                   "low battery",
    "falla de encoder":               "encoder fault",
    "modo local":                     "local mode",
    "bloqueado en local":             "locked in local",
    "falla de suministro de control": "control supply failure",
    "falla de suministro":            "supply failure",
    "csupfail":                       "control supply fail",
    "c.sup fail":                     "control supply fail",
    "falla de condensador":           "capacitor fault",
    "direccion duplicada":            "duplicate address",
    "falla de nodo":                  "node fault",
    "nodo perdido":                   "node lost",
    "fcu perdida":                    "FCU lost",
    "fcus en cero":                   "FCUs at zero",
    "falla de lazo":                  "loop fault",
    "lazo partido":                   "loop break",
    "ruptura de lazo":                "loop break",
    "sin fcus":                       "no FCUs",
    "autobucle":                      "autoloop",
    "falla de red":                   "network fault",
}

KEYWORDS = {
    "master": [
        "pakscan","master","fcu","fcus","lazo","loop","direccion","address",
        "bus","tk816","tk","p3","mk2","nodo","node","autobucle","autoloop",
        "ruptura","break","red de campo","fieldbus"
    ],
    "ck": [
        "ck","c.sup","csup","control supply","csupfail","condensador",
        "capacitor","ck range","actuador ck"
    ],
    "iq3": [
        "iq3","iq 3","motor stall","torque trip","encoder","bateria",
        "battery","limit switch","final de carrera","iq range"
    ],
}


def traducir(texto):
    t = texto.lower()
    for es, en in TRADUCCIONES.items():
        t = t.replace(es, en)
    return t


def detectar_sistema(texto):
    t = texto.lower()
    for kw in KEYWORDS["master"]:
        if kw in t:
            return "master"
    for kw in KEYWORDS["ck"]:
        if kw in t:
            return "ck"
    for kw in KEYWORDS["iq3"]:
        if kw in t:
            return "iq3"
    return "iq3"


def buscar_en_rotork(sistema, falla_original, falla_traducida):
    snippets = []
    headers  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    nombres_busqueda = {
        "iq3":    "Rotork IQ3 actuator",
        "ck":     "Rotork CK actuator",
        "master": "Rotork Pakscan Master Station",
    }
    for termino in [falla_traducida, falla_original]:
        try:
            query = f'{nombres_busqueda.get(sistema,"")} {termino} fault troubleshooting manual'
            url   = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
            resp  = requests.get(url, headers=headers, timeout=8)
            soup  = BeautifulSoup(resp.text, "html.parser")
            for g in soup.find_all("div", class_="BNeawe")[:6]:
                text = g.get_text()
                if len(text) > 60 and text not in snippets:
                    snippets.append(text[:350])
            if len(snippets) >= 4:
                break
        except Exception:
            continue
    return "\n".join(snippets[:5]) if snippets else ""


def imagen_a_base64(file):
    img_bytes = file.read()
    return base64.b64encode(img_bytes).decode("utf-8")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():
    if not client:
        return jsonify({"error": "❌ GROQ_API_KEY no configurada en Railway."})

    falla           = request.form.get("falla", "").strip()
    sistema_forzado = request.form.get("sistema_forzado", "auto").strip()
    file            = request.files.get("imagen")

    if not falla and not file:
        return jsonify({"error": "⚠️ Escribe la falla o adjunta una imagen del equipo."})

    # Detectar sistema
    if sistema_forzado and sistema_forzado != "auto":
        sistema = sistema_forzado
    else:
        sistema = detectar_sistema(falla) if falla else "iq3"

    nombres = {
        "iq3":    "Actuador Rotork IQ3",
        "ck":     "Actuador Rotork CK",
        "master": "Pakscan Master Station",
    }

    falla_traducida = traducir(falla) if falla else ""
    contexto_web    = buscar_en_rotork(sistema, falla, falla_traducida) if falla else ""
    contexto_str    = f"\nCONTEXTO TÉCNICO DE ROTORK.COM:\n{contexto_web}\n" if contexto_web else ""

    prompt = f"""Eres ROTORK EXPERT AI, especialista exclusivo en diagnóstico técnico de equipos Rotork.

EQUIPOS QUE CONOCES:
- Actuadores Rotork IQ3 (IQ3, IQ3 Pro, IQT3)
- Actuadores Rotork CK (CK, CKC, CKIS)
- Pakscan Master Station (TK816, TK316, P3, Mk2) y FCUs

CONOCIMIENTO TÉCNICO:

ROTORK IQ3:
  - Alarmas: Torque Trip, Motor Stall, Phase Loss, Thermostat, Battery Low, Encoder Fault
  - Menús: Status, Alarms, Data Logger, Position, Torque
  - Protocolos: HART, Profibus, Foundation Fieldbus, Modbus, Pakscan

ROTORK CK:
  - Alarmas: C.SUP FAIL, Motor Fault, Position Fault
  - Indicadores: LEDs rojo/verde/amarillo, display LCD
  - Fallas comunes: pérdida suministro de control, falla de condensador

PAKSCAN MASTER STATION:
  - Red de lazo de campo de 2 hilos (NO Ethernet, NO IP)
  - Gestiona hasta 240 FCUs por lazo
  - Direcciones (1-240) son de los FCUs, NO del Master
  - Alarmas: Duplicate Address, Loop Break, FCU Lost, Communication Fault
  - Autobucle: diagnóstico del lazo sin actuadores

REGLAS:
- Responde SIEMPRE en español técnico industrial
- Basate en manuales oficiales Rotork
- Sé preciso y práctico — el técnico está en campo

SISTEMA: {nombres.get(sistema, sistema.upper())}
FALLA: {falla if falla else "(ver imagen adjunta)"}
BÚSQUEDA EN INGLÉS: {falla_traducida if falla_traducida else "(análisis de imagen)"}
{contexto_str}
{"ANALIZA LA IMAGEN: identifica 1) Modelo del equipo Rotork, 2) Alarmas/códigos en display, 3) Estado de LEDs, 4) Posición del actuador, 5) Condiciones anormales." if file else ""}

Responde EXACTAMENTE con este formato en español:

SISTEMA IDENTIFICADO:
[Equipo y modelo Rotork]

DIAGNÓSTICO:
[Descripción técnica — máximo 2 oraciones]

CAUSAS PROBABLES:
- [Causa principal]
- [Causa secundaria]
- [Causa terciaria si aplica]

ACCIONES CORRECTIVAS:
1. [Primera acción en campo]
2. [Segunda verificación]
3. [Acción si persiste]

VERIFICACIONES ADICIONALES:
- [Parámetro a verificar]
- [Menú o herramienta Rotork]

NIVEL DE URGENCIA: [CRÍTICO / ALTO / MEDIO / BAJO]
[Justificación en una oración]

---
Fuente: Manuales técnicos oficiales Rotork | {nombres.get(sistema, "")}
"""

    try:
        if file:
            img_b64  = imagen_a_base64(file)
            messages = [
                {
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
                }
            ]
            modelo = MODELO_VISION
        else:
            messages = [
                {
                    "role": "system",
                    "content": "Eres ROTORK EXPERT AI, especialista en diagnóstico técnico de equipos Rotork IQ3, CK y Pakscan. Respondes siempre en español técnico industrial."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            modelo = MODELO_TEXTO

        response  = client.chat.completions.create(
            model=modelo,
            messages=messages,
            max_tokens=1500,
            temperature=0.3
        )
        resultado = response.choices[0].message.content

        return jsonify({
            "resultado":  resultado,
            "sistema":    nombres.get(sistema, sistema.upper()),
            "traduccion": falla_traducida if falla_traducida != falla else ""
        })

    except Exception as e:
        return jsonify({"error": f"❌ Error: {str(e)}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 52)
    print("  ROTORK AI — ASISTENTE DE DIAGNÓSTICO v2.0")
    print("  Powered by Groq (gratuito)")
    print(f"  Puerto: {port}")
    print("=" * 52)
    app.run(host="0.0.0.0", port=port, debug=False)

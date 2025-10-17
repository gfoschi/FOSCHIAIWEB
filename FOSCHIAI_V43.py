from flask import Flask, render_template_string, request, jsonify, session, send_file
from flask_session import Session
import os, uuid, json, re, io
from datetime import datetime
from openai import OpenAI
import requests
from gtts import gTTS

# ---------------- CONFIG ----------------
APP_NAME = "FOSCHI IA WEB"
CREADOR = "Gustavo Enrique Foschi"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Variables de entorno para Render
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
app.secret_key = "FoschiWebKey"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ---------------- FUNCIONES ----------------
def generar_respuesta(mensaje, usuario):
    mensaje_lower = mensaje.lower()
    if "quien te creó" in mensaje_lower or "quién te creó" in mensaje_lower or \
       "quien te hizo" in mensaje_lower or "quién te hizo" in mensaje_lower:
        return {"texto": f"Fui creada por {CREADOR}, con mucho cariño 😄.", "imagenes": []}

    if "borrar historial" in mensaje_lower or "borra historial" in mensaje_lower:
        historial_path = os.path.join(DATA_DIR, f"{usuario}.json")
        if os.path.exists(historial_path):
            os.remove(historial_path)
        return {"texto": "🧹 Listo, limpié todo el historial. Empezamos de nuevo.", "imagenes": []}

    # Buscar imágenes
    imagenes = []
    if "imagen" in mensaje_lower or "foto" in mensaje_lower:
        query = mensaje.replace("imagen", "").replace("foto", "").strip()
        imagenes = buscar_imagen_google(query)

    # Generar respuesta GPT
    try:
        prompt = f"Eres FOSCHI IA, una asistente cálida, inteligente y con voz femenina. Usuario: {usuario}\nMensaje: {mensaje}\nRespuesta:"
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=800
        )
        texto = resp.choices[0].message.content.strip()
        texto = hacer_links_clicleables(texto)
        return {"texto": texto, "imagenes": imagenes}
    except Exception as e:
        return {"texto": f"No pude generar respuesta: {e}", "imagenes": imagenes}

def hacer_links_clicleables(texto):
    return re.sub(r'(https?://[^\s]+)', r'<a href="\1" target="_blank">\1</a>', texto)

def guardar_en_historial(usuario, entrada, respuesta_texto):
    historial_path = os.path.join(DATA_DIR, f"{usuario}.json")
    datos = []
    if os.path.exists(historial_path):
        with open(historial_path, "r", encoding="utf-8") as f:
            try:
                datos = json.load(f)
            except:
                datos = []
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    datos.append({"fecha": ahora, "usuario": entrada, "foschi": respuesta_texto})
    with open(historial_path, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def cargar_historial(usuario):
    historial_path = os.path.join(DATA_DIR, f"{usuario}.json")
    if not os.path.exists(historial_path):
        return []
    with open(historial_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def buscar_imagen_google(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query, "searchType": "image", "num": 3}
    try:
        r = requests.get(url, params=params, timeout=5)
        resultados = r.json()
        return [item["link"] for item in resultados.get("items", [])]
    except:
        return []

# ---------------- RUTA TTS (voz femenina) ----------------
@app.route("/tts")
def tts():
    texto = request.args.get("texto", "")
    tts_obj = gTTS(text=texto, lang="es", tld="com")  # voz femenina neutra
    archivo = io.BytesIO()
    tts_obj.write_to_fp(archivo)
    archivo.seek(0)
    return send_file(archivo, mimetype="audio/mpeg")

# ---------------- HTML ----------------
# ---------------- HTML ----------------
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
<title>{{APP_NAME}}</title>
<style>
body{font-family:Arial;background:#000;color:#fff;margin:0;padding:0;}
#chat{width:100%;height:70vh;overflow-y:scroll;padding:10px;background:#111;}
.message{margin:5px 0;padding:8px 12px;border-radius:15px;max-width:80%;word-wrap:break-word;opacity:0;transition:opacity 1s;}
.message.show{opacity:1;}
.user{background:#3300ff;color:#fff;margin-left:auto;text-align:right;}
.ai{background:#00ffff;color:#000;margin-right:auto;text-align:left;}
a{color:#0033ff;}
img{max-width:300px;border-radius:10px;margin:5px 0;}
input,button{padding:10px;font-size:16px;margin:5px;border:none;border-radius:5px;}
input[type=text]{width:70%;background:#222;color:#fff;}
button{background:#333;color:#fff;cursor:pointer;}
button:hover{background:#555;}
#vozBtn{float:right;margin-right:20px;}
small{color:#aaa;}
</style>
</head>
<body>
<h2 style="text-align:center;">🤖 {{APP_NAME}} <button id="vozBtn" onclick="toggleVoz()">🔊 Voz activada</button></h2>

<div id="chat"></div>
<input type="text" id="mensaje" placeholder="Escribí tu mensaje o hablá" />
<button onclick="enviar()">Enviar</button>
<button onclick="hablar()">🎤 Hablar</button>
<button onclick="verHistorial()">🗂️ Ver historial</button>

<script>
let usuario_id="{{usuario_id}}";
let vozActiva = true;

function hablarTexto(texto){
  if(!vozActiva) return;
  let audio = new Audio("/tts?texto="+encodeURIComponent(texto));
  audio.play();
}

function toggleVoz(){
  vozActiva = !vozActiva;
  const btn = document.getElementById("vozBtn");
  btn.textContent = vozActiva ? "🔊 Voz activada" : "🔇 Silenciada";
}

function agregar(msg,cls, imagenes=[]){
  let c=document.getElementById("chat");
  let div = document.createElement("div");
  div.className = "message " + cls;
  div.innerHTML = msg;
  c.appendChild(div);
  setTimeout(()=>div.classList.add("show"),50);
  imagenes.forEach(url => {
      let img = document.createElement("img");
      img.src = url;
      div.appendChild(img);
  });
  c.scrollTop = c.scrollHeight;
  if(cls==="ai") hablarTexto(msg);
}

function enviar(){
  let msg=document.getElementById("mensaje").value.trim();
  if(!msg) return;
  agregar(msg,"user");
  document.getElementById("mensaje").value="";
  fetch("/preguntar",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({mensaje:msg,usuario_id:usuario_id})})
  .then(r=>r.json()).then(data=>{
      agregar(data.texto,"ai", data.imagenes);
      if(data.borrar_historial){document.getElementById("chat").innerHTML="";}
  });
}

function verHistorial(){
  fetch("/historial/"+usuario_id)
  .then(r=>r.json()).then(data=>{
      document.getElementById("chat").innerHTML="";
      if(data.length===0){agregar("No hay historial todavía.","ai");return;}
      data.forEach(e=>{
          agregar(`<small>${e.fecha}</small><br>${e.usuario}`,"user");
          agregar(`<small>${e.fecha}</small><br>${e.foschi}`,"ai");
      });
  });
}

function hablar(){
  if('webkitSpeechRecognition' in window){
      const recognition=new webkitSpeechRecognition();
      recognition.lang='es-AR';
      recognition.continuous=false;
      recognition.interimResults=false;
      recognition.onresult=function(event){
          let speech=event.results[0][0].transcript;
          document.getElementById("mensaje").value=speech;
          enviar();
      }
      recognition.onerror=function(e){console.log(e);}
      recognition.start();
  }else{alert("Tu navegador no soporta reconocimiento de voz.");}
}

// Saludo inicial
window.onload=function(){
  let saludo = "👋 Hola, soy FOSCHI IA, tu asistente con voz. ¿En qué puedo ayudarte hoy?";
  agregar(saludo,"ai");
};
</script>
</body>
</html>
"""

# ---------------- RUTAS ----------------
@app.route("/")
def index():
    if "usuario_id" not in session:
        session["usuario_id"] = str(uuid.uuid4())
    return render_template_string(HTML_TEMPLATE, APP_NAME=APP_NAME, usuario_id=session["usuario_id"])

@app.route("/preguntar", methods=["POST"])
def preguntar():
    data = request.get_json()
    mensaje = data.get("mensaje","")
    usuario_id = data.get("usuario_id", str(uuid.uuid4()))

    respuesta = generar_respuesta(mensaje, usuario_id)
    texto = respuesta["texto"]
    imagenes = respuesta["imagenes"]
    borrar_historial = "borrar historial" in mensaje.lower() or "borra historial" in mensaje.lower()

    if not borrar_historial:
        guardar_en_historial(usuario_id, mensaje, texto)

    return jsonify({"texto": texto, "imagenes": imagenes, "borrar_historial": borrar_historial})

@app.route("/historial/<usuario_id>")
def historial(usuario_id):
    datos = cargar_historial(usuario_id)
    return jsonify(datos)

# ---------------- MAIN ----------------
if __name__=="__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

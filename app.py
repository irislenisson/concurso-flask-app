import os
import locale
import json
import time
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Imports locais
try:
    from constants import UFS_SIGLAS, REGIOES, REGEX_BANCAS
    from services.scraper import raspar_dados_online, filtrar_concursos, extrair_link_final
except ImportError:
    # Fallback para evitar crash se arquivos não estiverem prontos
    UFS_SIGLAS = []
    REGIOES = {}
    REGEX_BANCAS = None

# --- CONFIGURAÇÃO ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')

# Correção de Proxy para o Render (IP Real)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# 1. Performance
Compress(app)

# 2. Segurança (Rate Limiting)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "200 per minute"],
    storage_uri="memory://"
)

CORS(app)

DB_FILE = os.path.join(basedir, 'concursos.json')
CACHE_TIMEOUT = 3600 
CACHE_MEMORIA = { "timestamp": 0, "dados": [] }

# --- GERENCIAMENTO DE DADOS ---
def obter_dados():
    global CACHE_MEMORIA
    agora = time.time()

    def hidratar_cache(dados):
        for item in dados:
            if isinstance(item.get('tokens'), list):
                item['tokens'] = set(item['tokens'])
        return dados

    if CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        return CACHE_MEMORIA["dados"]

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                if agora - conteudo.get('timestamp', 0) < CACHE_TIMEOUT:
                    CACHE_MEMORIA["dados"] = hidratar_cache(conteudo.get('dados', []))
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except: pass

    novos_dados = raspar_dados_online()
    if novos_dados:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": agora, "dados": novos_dados}, f, ensure_ascii=False)
        except: pass
        CACHE_MEMORIA["dados"] = hidratar_cache(novos_dados)
        CACHE_MEMORIA["timestamp"] = agora
        return CACHE_MEMORIA["dados"]
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                dados_disco = conteudo.get('dados', [])
                if dados_disco:
                    CACHE_MEMORIA["dados"] = hidratar_cache(dados_disco)
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except: pass

    return []

# --- ROTAS ---
@app.after_request
def add_header(response):
    if request.path.startswith('/static'):
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
    return response

# ... (imports e configurações anteriores permanecem iguais) ...

@app.route('/')
def index():
    # Captura o termo de busca da URL
    query = request.args.get('q')
    
    meta = {}
    if query:
        termo_limpo = query.strip()
        # REBRANDING AQUI:
        meta['title'] = f"Concurso: {termo_limpo} | Concurso Ideal"
        meta['description'] = f"Veja vagas, salários e editais para {termo_limpo} no Concurso Ideal."
    else:
        # TÍTULO PADRÃO DA MARCA:
        meta['title'] = None 
        meta['description'] = None

    return render_template(
        'index.html', 
        meta_title=meta['title'], 
        meta_description=meta['description']
    )

    # Passa as variáveis para o template
    return render_template(
        'index.html', 
        meta_title=meta['title'], 
        meta_description=meta['description']
    )

@app.route('/termos')
def termos(): return render_template('termos.html')

@app.route('/privacidade')
def privacidade(): return render_template('privacidade.html')

@app.route('/robots.txt')
def robots(): return Response("User-agent: *\nAllow: /", mimetype="text/plain")

# ROTA ADS.TXT (NOVA) - Obrigatória para AdSense
@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(basedir, 'ads.txt')

@app.route('/sitemap.xml')
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://concurso-app-2.onrender.com/</loc><changefreq>daily</changefreq></url>
      <url><loc>https://concurso-app-2.onrender.com/termos</loc><changefreq>monthly</changefreq></url>
      <url><loc>https://concurso-app-2.onrender.com/privacidade</loc><changefreq>monthly</changefreq></url>
    </urlset>"""
    return Response(xml, mimetype="application/xml")

@app.route('/ping')
@limiter.exempt
def ping():
    return jsonify({
        "status": "ok",
        "cache_timestamp": CACHE_MEMORIA.get("timestamp", 0),
        "itens_cache": len(CACHE_MEMORIA.get("dados", []))
    }), 200

@app.route('/api/link-profundo', methods=['POST'])
@limiter.limit("20 per minute") 
def api_link_profundo():
    data = request.json or {}
    return jsonify({'url': extrair_link_final(data.get('url', ''), data.get('tipo', 'edital'))})

@app.route('/api/buscar', methods=['POST'])
@limiter.limit("60 per minute")
def api_buscar():
    data = request.json or {}
    
    try: 
        import re
        s_raw = str(data.get('salario_minimo', ''))
        s_clean = re.sub(r'[^\d,]', '', s_raw)
        s_min = float(s_clean.replace(',', '.')) if s_clean else 0.0
    except: 
        s_min = 0.0

    palavras = [p.strip() for p in data.get('palavra_chave', '').split(',') if p.strip()]
    excluir = [p.strip() for p in data.get('excluir_palavra', '').split(',') if p.strip()]
    ufs = set(data.get('ufs', []))
    
    for reg in data.get('regioes', []):
        if reg == 'Nacional': ufs.add('Nacional/Outro')
        elif reg in REGIOES: ufs.update(REGIOES[reg])
    
    todos = obter_dados()
    res = filtrar_concursos(todos, s_min, palavras, list(ufs), excluir)
    return jsonify(res)

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
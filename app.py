import os
import locale
from flask import Flask, jsonify, render_template, Response
from flask_cors import CORS

# Imports locais (funcionam porque estão na mesma pasta raiz)
from constants import UFS_SIGLAS, REGIOES, REGEX_BANCAS
from services.scraper import raspar_dados_online, filtrar_concursos, extrair_link_final

# --- CONFIGURAÇÃO ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

DB_FILE = os.path.join(basedir, 'concursos.json')
CACHE_TIMEOUT = 3600 

CACHE_MEMORIA = { "timestamp": 0, "dados": [] }

# --- GERENCIAMENTO DE DADOS ---
def obter_dados():
    global CACHE_MEMORIA
    import time, json
    agora = time.time()

    def hidratar_cache(dados):
        for item in dados:
            if isinstance(item.get('tokens'), list):
                item['tokens'] = set(item['tokens'])
        return dados

    # 1. Cache Memória
    if CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        return CACHE_MEMORIA["dados"]

    # 2. Cache Disco
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                if agora - conteudo.get('timestamp', 0) < CACHE_TIMEOUT:
                    CACHE_MEMORIA["dados"] = hidratar_cache(conteudo.get('dados', []))
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except: pass

    # 3. Web Scraper
    novos_dados = raspar_dados_online()
    if novos_dados:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": agora, "dados": novos_dados}, f, ensure_ascii=False)
        except: pass
        CACHE_MEMORIA["dados"] = hidratar_cache(novos_dados)
        CACHE_MEMORIA["timestamp"] = agora
        return CACHE_MEMORIA["dados"]
    
    return []

# --- ROTAS ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/termos')
def termos(): return render_template('termos.html')

@app.route('/privacidade')
def privacidade(): return render_template('privacidade.html')

@app.route('/robots.txt')
def robots(): return Response("User-agent: *\nAllow: /", mimetype="text/plain")

@app.route('/api/link-profundo', methods=['POST'])
def api_link_profundo():
    from flask import request
    data = request.json or {}
    return jsonify({'url': extrair_link_final(data.get('url', ''), data.get('tipo', 'edital'))})

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    from flask import request
    data = request.json or {}
    
    # Tratamento de salário
    try: s_min = float(str(data.get('salario_minimo', '')).replace('.', '').replace(',', '.'))
    except: s_min = 0.0

    # Tratamento de listas
    palavras = [p.strip() for p in data.get('palavra_chave', '').split(',') if p.strip()]
    excluir = [p.strip() for p in data.get('excluir_palavra', '').split(',') if p.strip()]
    ufs = set(data.get('ufs', []))
    
    # Lógica de Regiões
    for reg in data.get('regioes', []):
        if reg == 'Nacional': ufs.add('Nacional/Outro')
        elif reg in REGIOES: ufs.update(REGIOES[reg])
    
    todos = obter_dados()
    res = filtrar_concursos(todos, s_min, palavras, list(ufs), excluir)
    return jsonify(res)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
import os
import time
import json
import locale
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS

# Importa as listas do arquivo constants.py da raiz
from constants import (
    UFS_SIGLAS, REGIOES
)

# Importa as funções de lógica da pasta services
from services.scraper import (
    raspar_dados_online, filtrar_concursos, extrair_link_final
)

# --- CONFIGURAÇÃO INICIAL ---
basedir = os.path.abspath(os.path.dirname(__file__))
# Atenção: template_folder='templates' porque agora organizamos os HTMLs na pasta templates
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# --- SISTEMA DE PERSISTÊNCIA E CACHE ---
DB_FILE = os.path.join(basedir, 'concursos.json')
CACHE_TIMEOUT = 3600  # 60 minutos (Mantido vivo por Ping externo)

CACHE_MEMORIA = {
    "timestamp": 0,
    "dados": []
}

# --- GERENCIADOR DE DADOS (CACHE/JSON) ---
def obter_dados():
    global CACHE_MEMORIA
    agora = time.time()

    # Função auxiliar para garantir que 'tokens' sejam sets (performance)
    def hidratar_cache(dados):
        for item in dados:
            if isinstance(item.get('tokens'), list):
                item['tokens'] = set(item['tokens'])
        return dados

    # 1. Tenta Memória RAM
    if CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        print(f"--> Usando CACHE em memória (expira em {int(CACHE_TIMEOUT - (agora - CACHE_MEMORIA['timestamp']))}s)")
        return CACHE_MEMORIA["dados"]

    # 2. Tenta Arquivo JSON
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                ts_arquivo = conteudo.get('timestamp', 0)
                dados_disco = conteudo.get('dados', [])
                
                if agora - ts_arquivo < CACHE_TIMEOUT and dados_disco:
                    print("--> Usando JSON do Disco")
                    CACHE_MEMORIA["dados"] = hidratar_cache(dados_disco)
                    CACHE_MEMORIA["timestamp"] = ts_arquivo
                    return CACHE_MEMORIA["dados"]
        except Exception as e:
            print(f"Erro lendo JSON local: {e}")

    # 3. Baixa da Web (Fallback)
    print("--> Baixando dados novos do site...")
    novos_dados = raspar_dados_online()
    
    if novos_dados:
        # Salva JSON
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": agora, "dados": novos_dados}, f, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar JSON local: {e}")

        # Salva RAM
        CACHE_MEMORIA["dados"] = hidratar_cache(novos_dados)
        CACHE_MEMORIA["timestamp"] = agora
        return CACHE_MEMORIA["dados"]

    # 4. Fallback de Emergência (Usa dados velhos se raspagem falhar)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                dados_disco = conteudo.get('dados', [])
                if dados_disco:
                    print("--> Falha na raspagem, usando dados antigos do disco.")
                    CACHE_MEMORIA["dados"] = hidratar_cache(dados_disco)
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except: pass

    return []

# --- ROTAS ---

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/termos')
def termos():
    return render_template('termos.html')

@app.route('/privacidade')
def privacidade():
    return render_template('privacidade.html')

@app.route('/robots.txt')
def robots():
    content = "User-agent: *\nAllow: /\nSitemap: https://concurso-app-2.onrender.com/sitemap.xml"
    return Response(content, mimetype="text/plain")

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
def ping():
    return jsonify({
        "status": "ok",
        "cache_timestamp": CACHE_MEMORIA.get("timestamp", 0),
        "itens_cache": len(CACHE_MEMORIA.get("dados", []))
    }), 200

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.route('/api/link-profundo', methods=['POST'])
def api_link_profundo():
    data = request.json or {}
    url_concurso = data.get('url', '')
    tipo = data.get('tipo', 'edital')
    if not url_concurso or url_concurso == '#': return jsonify({'url': '#'})
    
    # Chama o serviço
    url_final = extrair_link_final(url_concurso, tipo)
    return jsonify({'url': url_final})

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    data = request.json or {}
    
    try:
        s_raw = str(data.get('salario_minimo', ''))
        s_clean = re.sub(r'[^\d,]', '', s_raw).replace(',', '.')
        salario_minimo = float(s_clean) if s_clean else 0.0
    except: salario_minimo = 0.0

    palavra_chave_raw = data.get('palavra_chave', '')
    lista_palavras_chave = [p.strip() for p in palavra_chave_raw.split(',') if p.strip()]

    excluir_str = data.get('excluir_palavra', '')
    excluir_palavras = [p.strip() for p in excluir_str.split(',') if p.strip()]

    ufs_selecionadas = data.get('ufs', []) 
    regioes_selecionadas = data.get('regioes', []) 

    conjunto_ufs_alvo = set(ufs_selecionadas)
    for reg in regioes_selecionadas:
        if reg == 'Nacional': conjunto_ufs_alvo.add('Nacional/Outro')
        elif reg in REGIOES: conjunto_ufs_alvo.update(REGIOES[reg])
    
    lista_final_ufs = list(conjunto_ufs_alvo)
    
    # DEBUG NO LOG
    print(f"=== Busca: Salário > {salario_minimo} | UFs: {lista_final_ufs} | Chaves: {lista_palavras_chave}")

    # Chama o gerenciador de dados e o filtro do serviço
    todos_dados = obter_dados()
    resultados = filtrar_concursos(todos_dados, salario_minimo, lista_palavras_chave, lista_final_ufs, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
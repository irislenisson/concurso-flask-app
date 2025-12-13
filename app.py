import os
import locale
import json
import time
import threading
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, Response, send_from_directory, url_for, session, redirect, make_response
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import quote
from flask_caching import Cache

# --- INTEGRAÇÃO GOOGLE SHEETS ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    gspread = None
    print("--> Aviso: Biblioteca gspread não encontrada. Planilhas desativadas.")

# --- IMPORTS LOCAIS ---
try:
    from constants import UFS_SIGLAS, REGIOES, REGEX_BANCAS
    from services.scraper import raspar_dados_online, filtrar_concursos, extrair_link_final
except ImportError:
    UFS_SIGLAS = []
    REGIOES = {}
    REGEX_BANCAS = None
    print("--> Aviso: Erro ao importar módulos locais (constants ou scraper).")

# --- CONFIGURAÇÃO ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = os.environ.get('SECRET_KEY', 'chave_padrao_dev_segura')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Otimizações de Servidor (Proxy e Compressão)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
Compress(app)

# Configuração do Cache (Memória RAM)
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300 # 5 minutos padrão
})

# Configuração do Limiter (Proteção contra Abuse)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "200 per minute"],
    storage_uri="memory://"
)

CORS(app)

# Arquivos de Persistência Local
DB_FILE = os.path.join(basedir, 'concursos.json')
LEADS_FILE = os.path.join(basedir, 'leads.txt')
CACHE_TIMEOUT = 3600 
CACHE_MEMORIA = { "timestamp": 0, "dados": [] }

# --- DECORATOR DE SEGURANÇA (ADMIN) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

# --- FUNÇÕES AUXILIARES DO GOOGLE SHEETS ---

def get_gspread_client():
    """Conecta ao Google Sheets se as credenciais existirem."""
    if not gspread: return None
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if not creds_json: return None
    
    try:
        creds_dict = json.loads(creds_json)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"--> [GSPREAD ERROR] {e}")
        return None

def salvar_lead_sheets(email):
    """Salva o lead na aba principal."""
    client = get_gspread_client()
    if not client: return
    try:
        try: sheet = client.open("Leads Concurso Ideal").sheet1
        except: return
        
        data_hora = time.strftime('%d/%m/%Y %H:%M:%S')
        sheet.append_row([data_hora, email])
    except Exception as e:
        print(f"--> Erro ao salvar lead: {e}")

def salvar_busca_completa_sheets(payload):
    """Salva os termos pesquisados para análise (BI)."""
    client = get_gspread_client()
    if not client: return
    try:
        try: sheet = client.open("Leads Concurso Ideal").worksheet("Termos")
        except: sheet = client.open("Leads Concurso Ideal").sheet1
        
        data_hora = time.strftime('%d/%m/%Y %H:%M:%S')
        # Monta a linha com os novos campos (incluindo Níveis)
        sheet.append_row([
            data_hora, 
            payload.get('palavra_chave', ''), 
            payload.get('salario_minimo', ''), 
            ", ".join(payload.get('regioes', [])), 
            ", ".join(payload.get('ufs', [])), 
            ", ".join(payload.get('niveis', [])), # <--- NOVO CAMPO
            payload.get('excluir_palavra', '')
        ])
    except Exception as e:
        print(f"--> Erro ao salvar busca: {e}")

def salvar_report_sheets(texto_erro):
    """Salva reportes de erro dos usuários."""
    client = get_gspread_client()
    if not client: return
    try:
        try: sheet = client.open("Leads Concurso Ideal").worksheet("Report")
        except: sheet = client.open("Leads Concurso Ideal").sheet1
        
        data_hora = time.strftime('%d/%m/%Y %H:%M:%S')
        sheet.append_row([data_hora, "ERRO REPORTADO", texto_erro])
    except: pass

# --- GERENCIAMENTO DE DADOS (CACHE + JSON + SCRAPER) ---

def obter_dados(force=False):
    global CACHE_MEMORIA
    agora = time.time()

    def hidratar_cache(dados):
        # Converte listas de volta para sets para performance do filtro
        for item in dados:
            if isinstance(item.get('tokens'), list):
                item['tokens'] = set(item['tokens'])
            if isinstance(item.get('niveis'), list):
                item['niveis'] = set(item['niveis'])
        return dados

    # 1. Verifica Cache em Memória RAM
    if not force and CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        return CACHE_MEMORIA["dados"]

    # 2. Verifica Arquivo JSON Local
    if not force and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                if agora - conteudo.get('timestamp', 0) < CACHE_TIMEOUT:
                    CACHE_MEMORIA["dados"] = hidratar_cache(conteudo.get('dados', []))
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except: pass

    # 3. Executa Scraper Online (Se cache expirou ou não existe)
    novos_dados = raspar_dados_online()
    if novos_dados:
        # Prepara dados para salvar (converte sets para listas)
        dados_json = []
        for item in novos_dados:
            item_serializavel = item.copy()
            item_serializavel['tokens'] = list(item_serializavel['tokens'])
            item_serializavel['niveis'] = list(item_serializavel['niveis'])
            dados_json.append(item_serializavel)

        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": agora, "dados": dados_json}, f, ensure_ascii=False)
        except: pass
        
        CACHE_MEMORIA["dados"] = hidratar_cache(novos_dados)
        CACHE_MEMORIA["timestamp"] = agora
        return CACHE_MEMORIA["dados"]
    
    return CACHE_MEMORIA.get("dados", [])

# --- ROTAS DA APLICAÇÃO ---

@app.after_request
def add_header(response):
    """Adiciona headers de cache para arquivos estáticos."""
    if request.path.startswith('/static'):
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
    return response

@app.route('/ir')
def redirecionar_externo():
    """Redireciona para o link final (Edital/Inscrição)."""
    target_url = request.args.get('url')
    tipo = request.args.get('tipo', 'edital')
    if not target_url: return redirect('/')
    try:
        final_url = extrair_link_final(target_url, tipo)
        return redirect(final_url)
    except:
        return redirect(target_url)

@app.route('/')
def index():
    """Página Principal (Home) com SEO Google Jobs."""
    query = request.args.get('q')
    meta = {}
    
    # --- PREPARAÇÃO DO SCHEMA.ORG (GOOGLE JOBS) ---
    dados_brutos = obter_dados()
    schema_jobs = []
    hoje_iso = datetime.now().strftime('%Y-%m-%d')
    
    # Processa os primeiros 40 itens para o Googlebot
    for item in dados_brutos[:40]:
        try:
            data_fim_iso = datetime.strptime(item.get('data_fim', ''), '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            data_fim_iso = None 

        job = {
            "titulo": item.get('texto'),
            "data_postagem": hoje_iso,
            "validade": data_fim_iso,
            "local": item.get('uf', 'BR'),
            "salario": item.get('salario_num', 0),
            "url": url_for('redirecionar_externo', url=item.get('link'), tipo='edital', _external=True)
        }
        schema_jobs.append(job)
    # ---------------------------------------------

    if query:
        termo = query.strip()
        meta['title'] = f"Concurso: {termo} | CONCURSO IDEAL"
        meta['description'] = f"Veja vagas, salários e editais para {termo} no Concurso Ideal."
    else:
        meta['title'] = None
        meta['description'] = None
        
    return render_template('index.html', 
                           meta_title=meta['title'], 
                           meta_description=meta['description'], 
                           schema_jobs=schema_jobs)

# --- ROTAS DE PÁGINAS ESTÁTICAS (COM CACHE) ---

@app.route('/sobre')
@cache.cached(timeout=3600) 
def sobre():
    return render_template('sobre.html')

@app.route('/contato')
@cache.cached(timeout=3600)
def contato():
    return render_template('contato.html')

@app.route('/termos')
@cache.cached(timeout=3600)
def termos():
    return render_template('termos.html')

@app.route('/privacidade')
@cache.cached(timeout=3600)
def privacidade():
    return render_template('privacidade.html')

# --- ROTAS DE ADMINISTRAÇÃO ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/admin')
        else:
            return render_template('login.html', erro="Senha incorreta!")
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
@login_required
def admin_panel():
    leads = []
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if ' - ' in line:
                        parts = line.strip().split(' - ')
                        leads.append({'data': parts[0], 'email': parts[1]})
        except: pass
    
    dados = CACHE_MEMORIA.get('dados', [])
    ts = CACHE_MEMORIA.get('timestamp', 0)
    idade = int((time.time() - ts) / 60) if ts > 0 else 0

    return render_template('admin.html', 
                           leads=reversed(leads), 
                           total_leads=len(leads), 
                           total_concursos=len(dados), 
                           cache_age=idade)

@app.route('/admin/download_leads')
@login_required
def download_leads():
    if not os.path.exists(LEADS_FILE): return "Vazio", 404
    with open(LEADS_FILE, 'r', encoding='utf-8') as f: content = f.read()
    response = make_response("Data,Email\n" + content.replace(' - ', ','))
    response.headers["Content-Disposition"] = "attachment; filename=leads.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/admin/force_update')
@login_required
def force_update():
    obter_dados(force=True)
    cache.clear() 
    return redirect('/admin')

# --- ROTAS DE UTILIDADE / SEO ---

@app.route('/robots.txt')
@cache.cached(timeout=86400)
def robots():
    return Response("User-agent: *\nAllow: /", mimetype="text/plain")

@app.route('/ads.txt')
@cache.cached(timeout=86400)
def ads_txt():
    return send_from_directory(basedir, 'ads.txt')

@app.route('/sitemap.xml')
@cache.cached(timeout=3600)
def sitemap():
    """Gera Sitemap dinâmico para o Google."""
    xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_content.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    estaticas = [('index', 'daily', '1.0'), ('sobre', 'monthly', '0.8'), ('contato', 'monthly', '0.8'), ('termos', 'yearly', '0.5'), ('privacidade', 'yearly', '0.5')]
    
    for endpoint, freq, prio in estaticas:
        try:
            url = url_for(endpoint, _external=True)
            xml_content.append(f'<url><loc>{url}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
        except: pass
    
    # Páginas dinâmicas de busca
    dados = obter_dados()
    urls_adicionadas = set()
    for item in dados:
        termo_limpo = item['texto'].split('-')[0].strip()
        if len(termo_limpo) > 4 and termo_limpo not in urls_adicionadas:
            urls_adicionadas.add(termo_limpo)
            link_dinamico = url_for('index', _external=True) + f"?q={quote(termo_limpo)}"
            xml_content.append(f'<url><loc>{link_dinamico}</loc><changefreq>daily</changefreq><priority>0.7</priority></url>')
            
    xml_content.append('</urlset>')
    return Response('\n'.join(xml_content), mimetype="application/xml")

@app.route('/ping')
@limiter.exempt
def ping():
    return jsonify({ "status": "ok", "cache_timestamp": CACHE_MEMORIA.get("timestamp", 0) }), 200

# --- API (ENDPOINTS JSON) ---

@app.route('/api/link-profundo', methods=['POST'])
@limiter.limit("20 per minute") 
def api_link_profundo():
    data = request.json or {}
    return jsonify({'url': extrair_link_final(data.get('url', ''), data.get('tipo', 'edital'))})

@app.route('/api/buscar', methods=['POST'])
@limiter.limit("60 per minute")
def api_buscar():
    """API Principal de Busca (Processa filtros e retorna JSON)."""
    data = request.json or {}
    
    # Tratamento de Salário
    try: 
        import re
        s_raw = str(data.get('salario_minimo', ''))
        s_clean = re.sub(r'[^\d,]', '', s_raw)
        s_min = float(s_clean.replace(',', '.')) if s_clean else 0.0
    except: s_min = 0.0

    # Coleta de Filtros
    palavras = [p.strip() for p in data.get('palavra_chave', '').split(',') if p.strip()]
    excluir = [p.strip() for p in data.get('excluir_palavra', '').split(',') if p.strip()]
    ufs_list = data.get('ufs', [])
    regioes_list = data.get('regioes', [])
    niveis_list = data.get('niveis', []) # <--- FILTRO DE ESCOLARIDADE (Novo)
    
    # Salva Termos no Sheets (BI)
    if any([data.get('palavra_chave'), data.get('salario_minimo'), ufs_list, regioes_list, excluir, niveis_list]):
        payload_sheets = {
            'palavra_chave': data.get('palavra_chave', ''),
            'salario_minimo': data.get('salario_minimo', ''),
            'regioes': regioes_list,
            'ufs': ufs_list,
            'niveis': niveis_list,
            'excluir_palavra': data.get('excluir_palavra', '')
        }
        threading.Thread(target=salvar_busca_completa_sheets, args=(payload_sheets,)).start()

    # Expande Regiões
    ufs = set(ufs_list)
    for reg in regioes_list:
        if reg == 'Nacional': ufs.add('Nacional/Outro')
        elif reg in REGIOES: ufs.update(REGIOES[reg])
    
    # Executa Filtro
    todos = obter_dados()
    res = filtrar_concursos(todos,
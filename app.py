import os
import locale
import json
import time
import threading
from functools import wraps
from flask import Flask, request, jsonify, render_template, Response, send_from_directory, url_for, session, redirect, make_response
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import quote

# Imports Google Sheets (Protegido contra erro)
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    gspread = None

# Imports locais
try:
    from constants import UFS_SIGLAS, REGIOES, REGEX_BANCAS
    from services.scraper import raspar_dados_online, filtrar_concursos, extrair_link_final
except ImportError:
    UFS_SIGLAS = []
    REGIOES = {}
    REGEX_BANCAS = None

# --- CONFIGURAÇÃO ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = os.environ.get('SECRET_KEY', 'chave_padrao_dev_segura')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
Compress(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "200 per minute"],
    storage_uri="memory://"
)

CORS(app)

DB_FILE = os.path.join(basedir, 'concursos.json')
LEADS_FILE = os.path.join(basedir, 'leads.txt')
CACHE_TIMEOUT = 3600 
CACHE_MEMORIA = { "timestamp": 0, "dados": [] }

# --- DECORATOR ADMIN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

# --- FUNÇÕES GOOGLE SHEETS (BI & LEADS) ---

def get_gspread_client():
    """Conecta ao Google Sheets"""
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
    """Salva Lead na aba 'Sheet1'"""
    client = get_gspread_client()
    if not client: return

    try:
        sheet = client.open("Leads Concurso Ideal").sheet1
        data_hora = time.strftime('%d/%m/%Y %H:%M:%S')
        sheet.append_row([data_hora, email])
        print(f"--> [SHEETS] Lead {email} salvo!")
    except Exception as e:
        print(f"--> [SHEETS LEAD ERROR] {e}")

def salvar_busca_completa_sheets(payload):
    """
    Salva TODOS os filtros da busca para Inteligência de Negócio.
    Espera uma aba chamada 'Termos' ou 'Buscas'.
    """
    client = get_gspread_client()
    if not client: return

    try:
        # Tenta abrir aba 'Termos', se não, cria ou usa sheet1
        try:
            sheet = client.open("Leads Concurso Ideal").worksheet("Termos")
        except:
            # Se você ainda não criou a aba, ele vai salvar na primeira mesmo
            sheet = client.open("Leads Concurso Ideal").sheet1
        
        # Prepara os dados para ficarem bonitos na planilha
        data_hora = time.strftime('%d/%m/%Y %H:%M:%S')
        palavra = payload.get('palavra_chave', '')
        salario = payload.get('salario_minimo', '')
        
        # Transforma listas em strings separadas por vírgula
        regioes = ", ".join(payload.get('regioes', []))
        ufs = ", ".join(payload.get('ufs', []))
        excluir = payload.get('excluir_palavra', '')

        # Salva a linha completa
        # Ordem: Data | Palavra | Salário | Regiões | UFs | Excluídas
        sheet.append_row([data_hora, palavra, salario, regioes, ufs, excluir])
        
        print(f"--> [BI] Busca registrada: {palavra} | {ufs}")
    except Exception as e:
        print(f"--> [SHEETS BI ERROR] {e}")

# --- GERENCIAMENTO DE DADOS ---
def obter_dados(force=False):
    global CACHE_MEMORIA
    agora = time.time()

    def hidratar_cache(dados):
        for item in dados:
            if isinstance(item.get('tokens'), list):
                item['tokens'] = set(item['tokens'])
        return dados

    if not force and CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        return CACHE_MEMORIA["dados"]

    if not force and os.path.exists(DB_FILE):
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
    
    return CACHE_MEMORIA.get("dados", [])

# --- ROTAS ---
@app.after_request
def add_header(response):
    if request.path.startswith('/static'):
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
    return response

@app.route('/ir')
def redirecionar_externo():
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
    query = request.args.get('q')
    meta = {}
    if query:
        termo = query.strip()
        meta['title'] = f"Concurso: {termo} | CONCURSO IDEAL"
        meta['description'] = f"Veja vagas, salários e editais para {termo} no Concurso Ideal."
    else:
        meta['title'] = None
        meta['description'] = None
    return render_template('index.html', meta_title=meta['title'], meta_description=meta['description'])

@app.route('/sobre')
def sobre(): return render_template('sobre.html')

@app.route('/contato')
def contato(): return render_template('contato.html')

@app.route('/termos')
def termos(): return render_template('termos.html')

@app.route('/privacidade')
def privacidade(): return render_template('privacidade.html')

# --- ADMIN ---
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
        with open(LEADS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ' - ' in line:
                    parts = line.strip().split(' - ')
                    leads.append({'data': parts[0], 'email': parts[1]})
    
    dados = CACHE_MEMORIA.get('dados', [])
    ts = CACHE_MEMORIA.get('timestamp', 0)
    idade = int((time.time() - ts) / 60) if ts > 0 else 0

    return render_template('admin.html', leads=reversed(leads), total_leads=len(leads), total_concursos=len(dados), cache_age=idade)

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
    return redirect('/admin')

@app.route('/robots.txt')
def robots(): return Response("User-agent: *\nAllow: /", mimetype="text/plain")

@app.route('/ads.txt')
def ads_txt(): return send_from_directory(basedir, 'ads.txt')

@app.route('/sitemap.xml')
def sitemap():
    xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_content.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    estaticas = [('index', 'daily', '1.0'), ('sobre', 'monthly', '0.8'), ('contato', 'monthly', '0.8'), ('termos', 'yearly', '0.5'), ('privacidade', 'yearly', '0.5')]
    for endpoint, freq, prio in estaticas:
        try:
            url = url_for(endpoint, _external=True)
            xml_content.append(f'<url><loc>{url}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
        except: pass
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

# --- API BUSCA ---
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
    except: s_min = 0.0

    # Extrai filtros
    palavras = [p.strip() for p in data.get('palavra_chave', '').split(',') if p.strip()]
    excluir = [p.strip() for p in data.get('excluir_palavra', '').split(',') if p.strip()]
    ufs_list = data.get('ufs', [])
    regioes_list = data.get('regioes', [])
    
    # Prepara payload para salvar no Sheets (só se tiver algum filtro)
    tem_filtro = any([data.get('palavra_chave'), data.get('salario_minimo'), ufs_list, regioes_list, excluir])
    
    if tem_filtro:
        payload_sheets = {
            'palavra_chave': data.get('palavra_chave', ''),
            'salario_minimo': data.get('salario_minimo', ''),
            'regioes': regioes_list,
            'ufs': ufs_list,
            'excluir_palavra': data.get('excluir_palavra', '')
        }
        # Dispara thread paralela para não travar o usuário
        threading.Thread(target=salvar_busca_completa_sheets, args=(payload_sheets,)).start()

    # Lógica de Filtragem
    ufs = set(ufs_list)
    for reg in regioes_list:
        if reg == 'Nacional': ufs.add('Nacional/Outro')
        elif reg in REGIOES: ufs.update(REGIOES[reg])
    
    todos = obter_dados()
    res = filtrar_concursos(todos, s_min, palavras, list(ufs), excluir)
    return jsonify(res)

# --- ERROS ---
@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e): return render_template('500.html'), 500

# --- NEWSLETTER ---
@app.route('/api/newsletter', methods=['POST'])
@limiter.limit("5 per minute")
def api_newsletter():
    data = request.json or {}
    email = data.get('email', '').strip()
    
    if not email or '@' not in email: return jsonify({'error': 'E-mail inválido'}), 400
    
    print(f"\n{'='*40}\n🎯 NOVO LEAD: {email}\n{'='*40}\n")
    
    try:
        with open(LEADS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {email}\n")
    except: pass

    threading.Thread(target=salvar_lead_sheets, args=(email,)).start()

    return jsonify({'message': 'Sucesso!'})

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
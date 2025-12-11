import os
import locale
import json
import time
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template, Response, send_from_directory, url_for
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import quote

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

# --- FUNÇÃO DE ENVIO DE E-MAIL (COM SUPORTE A SSL/465) ---
def enviar_emails_sistema(email_usuario):
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    admin_email = "concursoideal@icloud.com"

    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
        print("--> [ERRO] Variáveis SMTP faltando no Render.")
        return

    try:
        print(f"--> [EMAIL] Tentando conectar em {smtp_server}:{smtp_port}...")
        
        # Lógica inteligente para Portas (465 SSL vs 587 TLS)
        if smtp_port == 465:
            # Conexão SSL Direta (Mais segura e menos bloqueada)
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # Conexão TLS Padrão (Geralmente bloqueada em free tier)
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

        server.login(smtp_user, smtp_pass)

        # 1. E-MAIL PARA O ADMIN (VOCÊ)
        msg_admin = MIMEMultipart()
        msg_admin['From'] = f"Sistema Concurso Ideal <{smtp_user}>"
        msg_admin['To'] = admin_email
        msg_admin['Subject'] = f"🔔 Novo Lead: {email_usuario}"
        corpo_admin = f"<h2>Novo Cadastro!</h2><p>O usuário <strong>{email_usuario}</strong> se cadastrou na newsletter.</p>"
        msg_admin.attach(MIMEText(corpo_admin, 'html'))
        server.sendmail(smtp_user, admin_email, msg_admin.as_string())
        print(f"--> [SUCESSO] Aviso enviado para o Admin ({admin_email})")

        # 2. E-MAIL PARA O USUÁRIO (BOAS-VINDAS)
        msg_user = MIMEMultipart()
        msg_user['From'] = f"Concurso Ideal <{smtp_user}>"
        msg_user['To'] = email_usuario
        msg_user['Subject'] = "Bem-vindo ao Concurso Ideal! 🚀"
        
        corpo_user = f"""
        <div style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #007bff;">Obrigado por se cadastrar!</h2>
            <p>Olá,</p>
            <p>Recebemos seu interesse em receber as melhores vagas de concursos públicos.</p>
            <p>Em breve, você receberá atualizações selecionadas diretamente no seu e-mail.</p>
            <br>
            <p>Atenciosamente,<br><strong>Equipe Concurso Ideal</strong></p>
            <p><small><a href="https://concurso-app-2.onrender.com">Acesse o site</a></small></p>
        </div>
        """
        msg_user.attach(MIMEText(corpo_user, 'html'))
        server.sendmail(smtp_user, email_usuario, msg_user.as_string())
        print(f"--> [SUCESSO] Boas-vindas enviada para o Usuário ({email_usuario})")

        server.quit()

    except Exception as e:
        print(f"--> [ERRO CRÍTICO NO ENVIO] {e}")

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
    except: s_min = 0.0

    palavras = [p.strip() for p in data.get('palavra_chave', '').split(',') if p.strip()]
    excluir = [p.strip() for p in data.get('excluir_palavra', '').split(',') if p.strip()]
    ufs = set(data.get('ufs', []))
    for reg in data.get('regioes', []):
        if reg == 'Nacional': ufs.add('Nacional/Outro')
        elif reg in REGIOES: ufs.update(REGIOES[reg])
    
    todos = obter_dados()
    res = filtrar_concursos(todos, s_min, palavras, list(ufs), excluir)
    return jsonify(res)

@app.route('/api/newsletter', methods=['POST'])
@limiter.limit("5 per minute")
def api_newsletter():
    data = request.json or {}
    email = data.get('email', '').strip()
    
    if not email or '@' not in email:
        return jsonify({'error': 'E-mail inválido'}), 400
    
    try:
        with open(LEADS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {email}\n")
    except: pass

    # Envia e-mail em segundo plano
    thread = threading.Thread(target=enviar_emails_sistema, args=(email,))
    thread.start()

    return jsonify({'message': 'Sucesso! Você receberá novidades.'})

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
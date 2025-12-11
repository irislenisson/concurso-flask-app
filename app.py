import re
import os
import time
import json
import locale
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAÇÃO INICIAL ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=basedir, static_folder=basedir)
CORS(app)

# --- SISTEMA DE PERSISTÊNCIA E CACHE ---
DB_FILE = os.path.join(basedir, 'concursos.json')
CACHE_TIMEOUT = 3600  # 60 minutos (com Keep-Alive)

CACHE_MEMORIA = {
    "timestamp": 0,
    "dados": []
}

# --- LISTAS DE REFERÊNCIA ---
UFS_SIGLAS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

REGIOES = {
    'Norte': ['AM', 'RR', 'AP', 'PA', 'TO', 'RO', 'AC'],
    'Nordeste': ['MA', 'PI', 'CE', 'RN', 'PE', 'PB', 'SE', 'AL', 'BA'],
    'Centro-Oeste': ['MT', 'MS', 'GO', 'DF'],
    'Sudeste': ['SP', 'RJ', 'ES', 'MG'],
    'Sul': ['PR', 'RS', 'SC'],
}

# --- REGEX E PADRÕES DE EXTRAÇÃO (APRIMORADOS) ---
REGEX_SALARIOS = [
    r'R\$\s*([\d\.]+,\d{2})',
    r'at[eé]\s*R\$\s*([\d\.]+,\d{2})',
    r'inicial\s*R\$\s*([\d\.]+,\d{2})',
    r'remunera[cç][aã]o\s*(?:de)?\s*R\$\s*([\d\.]+,\d{2})',
    r'([\d\.]+,\d{2})\s*(?:reais|bruto|l[ií]quido)?'
]

REGEX_DATAS = [
    r'\b(\d{2}/\d{2}/\d{4})\b',     # completo
    r'\b(\d{2}/\d{2}/\d{2})\b',     # dois dígitos
    r'\b(\d{2}/\d{2})\b'            # sem ano
]

REGEX_UF = re.compile(r'\b(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b', re.IGNORECASE)

RAW_BANCAS = """
1dn, 2dn, 3dn, 4dn, 5dn, 6dn, 7dn, 8dn, 9dn, abare, abcp, acafe, acaplam, access, acep, actio, adm&tec, advise, 
agata, agirh, agu, air, ajuri, alfa, alternative, amac, amazul, ameosc, 
amigapublica, anima, aocp, apice, aprender, ares, arespcj, aroeira, asconprev, 
asperhs, assege, assconpp, atena, auctor, avalia, avaliar, avalias, avancar, 
avancasp, avmoreira, banpara, bigadvice, biorio, bios, brb, caip, calegariox, 
carlosbittencourt, ccv, ceaf, cebraspe, cec, cefet, ceperj, cepros, ceps, 
cepuerj, cesgranrio, cespe, cetap, cetrede, cetro, cev, cfc, ciee, ciesp, 
ciscopar, cislipa, ckm, cl, click, cmm, coelhoneto, cogeps, comagsul, compec, 
comperve, comvest, concepca, coned, conesul, conpass, conscam, consel, conesp, 
consesp, consulplan, consulpam, consultec, contemax, coperve, copese, copeve, 
covest, creative, crescer, csc, ctd, cursiva, dae, darwin, decorp, dedalus, 
depsec, direcao, directa, educapb, educax, egp, ejud, ejef, epl, epbazi, esaf, 
esmarn, espm, espp, ethos, evo, exata, exatus, excelencia, exercito, fab.mil, 
facet, facto, fade, fadenor, fadesp, fadurpe, fae, faed, faepesul, faepol, 
fafipa, fama, fapec, faperp, fapeu, fastef, fat, faurgs, fcc, fcm, fcpc, fec, 
fema, femperj, fenaz, fenix, fepese, fesmip, fgv, fidesa, fiocruz, fip, fjpf, 
flem, fluxo, fmp, fmz, fps, framinas, fronte, fsa, fspss, fujb, fucap, fucapsul, 
fumarc, funatec, funcefet, funcepe, fundape, fundatec, fundect, fundec, fundep, 
fundepes, funece, funec, funiversa, funjab, funrio, funtef, funvapi, furb, furg, 
fuvest, gama, ganzaroli, gsa, gsassessoria, group, gualimp, hcrp, hl, iad, 
iadhed, iamspe, ian, iasp, iat, ibade, ibam, ibc, ibdo, ibec, ibeg, ibest, ibfc, 
ibgp, ibido, ibptec, icap, icece, ideap, idecan, idep, idesg, idesul, idht, idib, 
ieds, iesap, ieses, ifbaiano, ifc, iff, ifsul, igdrh, igecs, igeduc, igetec, 
imam, imagine, imparh, inaz, inqc, incp, indec, indepac, ineaa, inep, iniciativa, 
inovaty, institutomais, intec, integri, intelectus, iobv, ioplan, ipad, ipefae, 
isba, isae, iset, itame, itco, iuds, jbo, jcm, jk, jlz, jota, jvl, klc, lasalle, 
legalle, legatus, lj, magnus, makiyama, maranatha, master, maxima, mds, metodo, 
metrocapital, metropole, mgs, mouramelo, movens, mpf, mpt, msconcursos, mds, 
nc.ufpr, nbs, nce, nemesis, noroeste, nossorumo, ntcs, nubes, objetiva, officium, 
omni, omini, opgp, orhion, paqtcpb, patativa, perfas, pge, pgt, planexcon, 
planejar, policon, pontua, pr-4, pr4, prime, proam, profnit, progep, progepe, 
progesp, prograd, promun, promunicipio, publiconsult, puc, qconcursos, quadrix, 
rbo, referencia, reis, rhs, scgas, schnorr, sead, seap, secplan, seduc, segplan, 
selecon, seletiva, semasa, senai, seprod, serctam, ses, seta, shdias, sigma, 
sipros, sousandrade, spdm, srh, status, sugep, sustente, tupy, tj-ap, uece, 
ueg, uel, uem, uepb, uepa, uerj, uerr, uespi, ufabc, ufac, ufam, ufba, ufca, 
ufcg, ufersa, uff, ufgd, ufla, ufma, ufmg, ufmt, ufop, ufpa, ufpe, ufpel, ufpr, 
ufr, ufrb, ufrgs, ufrj, ufrn, ufrpe, ufrr, ufrrj, ufsba, ufsc, ufscar, ufsj, 
ufsm, uftm, ufv, una, unama, uneb, unemat, unesp, unespar, unesc, unibave, 
unicamp, unicentro, unichristus, unifal, unifap, unifase, unifei, unifesp, 
unifeso, unifil, unilab, unilavras, unimontes, unioeste, unipalmares, unirio, 
unisul, unitins, univali, univasf, univida, uniuv, uno, unoesc, upe, urca, usp, 
utfpr, verbena, vicentenelson, vunesp, wedo, wisdom, zambini
"""

TERMOS_BANCAS = [t.strip() for t in RAW_BANCAS.replace('\n', ',').split(',') if t.strip()]
REGEX_BANCAS = re.compile(r'|'.join(map(re.escape, TERMOS_BANCAS)), re.IGNORECASE)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

# --- FUNÇÕES DE EXTRAÇÃO INTELIGENTE ---

def formatar_real(valor):
    if valor <= 0: return "Ver Edital/Variável"
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_salario(texto):
    for padrao in REGEX_SALARIOS:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            try:
                # Remove pontos de milhar e troca vírgula decimal por ponto
                return float(m.group(1).replace('.', '').replace(',', '.'))
            except: pass
    return 0.0

def extrair_data(texto):
    hoje = datetime.now().date()
    ano_atual = hoje.year
    for padrao in REGEX_DATAS:
        m = re.findall(padrao, texto)
        if m:
            data_str = m[-1]
            try:
                partes = data_str.split('/')
                if len(partes) == 2:  
                    data_str = f"{partes[0]}/{partes[1]}/{ano_atual}"
                elif len(partes) == 3 and len(partes[2]) == 2:
                    partes[2] = "20" + partes[2]
                    data_str = "/".join(partes)
                data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                return data_obj
            except: pass
    return None

def extrair_uf(texto):
    m = REGEX_UF.search(texto)
    if m:
        return m.group(0).upper()
    m2 = re.search(r'prefeitura de ([A-Za-zà-ú]+)', texto, re.IGNORECASE)
    if m2:
        return "Nacional/Outro"
    return "Nacional/Outro"

# --- RASPAGEM, PROCESSAMENTO E CACHE COM FALLBACK ---

def raspar_dados_online():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    print("--> Iniciando raspagem online (Lógica Otimizada)...")
    try:
        resp = requests.get(URL_BASE, timeout=30, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        itens_brutos = soup.find_all('div', class_='ca')
        
        lista_processada = []
        hoje = datetime.now().date()

        for c in itens_brutos:
            texto = c.get_text(separator=' ', strip=True)
            link_original = "#"
            try:
                tag_link = c.find('a')
                if tag_link and 'href' in tag_link.attrs:
                    link_original = tag_link['href']
            except: pass

            data_fim_obj = extrair_data(texto)
            salario_num = extrair_salario(texto)
            uf_detectada = extrair_uf(texto)

            data_str = "Indefinida"
            if data_fim_obj:
                if data_fim_obj < hoje: continue
                data_str = data_fim_obj.strftime('%d/%m/%Y')

            # Otimização: set de tokens para busca rápida
            texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
            tokens_set = list(set(texto_limpo.split()))

            lista_processada.append({
                'texto': texto,
                'texto_lower': texto.lower(),
                'tokens': tokens_set,
                'link': link_original,
                'data_fim': data_str,
                'salario_num': salario_num,
                'salario_formatado': formatar_real(salario_num),
                'uf': uf_detectada
            })
        
        lista_processada.sort(key=lambda x: x['salario_num'], reverse=True)
        print(f"--> Raspagem concluída: {len(lista_processada)} concursos ativos.")
        return lista_processada

    except Exception as e:
        print(f"--> ERRO CRÍTICO NA RASPAGEM: {e}")
        return []

def obter_dados():
    global CACHE_MEMORIA
    agora = time.time()

    # Função auxiliar para hidratar tokens (list -> set)
    def hidratar_cache(dados):
        for item in dados:
            if isinstance(item.get('tokens'), list):
                item['tokens'] = set(item['tokens'])
        return dados

    # 1. Verifica Cache em Memória
    if CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        print(f"--> Usando CACHE em memória (expira em {int(CACHE_TIMEOUT - (agora - CACHE_MEMORIA['timestamp']))}s)")
        return CACHE_MEMORIA["dados"]

    # 2. Verifica Cache em Disco (JSON)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                ts_arquivo = conteudo.get('timestamp', 0)
                dados_disco = conteudo.get('dados', [])
                
                # Se estiver dentro do timeout, usa direto
                if agora - ts_arquivo < CACHE_TIMEOUT and dados_disco:
                    print("--> Usando JSON do Disco (ainda dentro do TTL)")
                    CACHE_MEMORIA["dados"] = hidratar_cache(dados_disco)
                    CACHE_MEMORIA["timestamp"] = ts_arquivo
                    return CACHE_MEMORIA["dados"]
        except Exception as e:
            print(f"Erro lendo JSON local: {e}")

    # 3. Baixa da Web
    print("--> Baixando dados novos do site...")
    novos_dados = raspar_dados_online()
    
    if novos_dados:
        # Salva no JSON (com tokens como lista)
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": agora, "dados": novos_dados}, f, ensure_ascii=False)
            print(f"--> JSON salvo com {len(novos_dados)} registros.")
        except Exception as e:
            print(f"Erro ao salvar JSON local: {e}")

        # Salva na RAM (com tokens como set)
        CACHE_MEMORIA["dados"] = hidratar_cache(novos_dados)
        CACHE_MEMORIA["timestamp"] = agora
        return CACHE_MEMORIA["dados"]

    # 4. Fallback: Se raspagem falhou, usa cache antigo do disco
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                dados_disco = conteudo.get('dados', [])
                if dados_disco:
                    print("--> Falha na raspagem, usando dados antigos do disco como fallback.")
                    CACHE_MEMORIA["dados"] = hidratar_cache(dados_disco)
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except Exception as e:
            print(f"Erro no fallback do JSON local: {e}")

    print("--> Nenhum dado disponível (raspagem falhou e JSON vazio).")
    return []

def filtrar_concursos(todos_dados, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0

    # Pré-computa set de exclusão para performance
    set_exclusao = set(p.lower() for p in excluir_palavras) if excluir_palavras else None

    for item in todos_dados:
        # Filtro Exclusão Otimizado (Set)
        if set_exclusao and 'tokens' in item:
            if not set_exclusao.isdisjoint(item['tokens']): continue
        elif excluir_palavras and any(ex.lower() in item['texto_lower'] for ex in excluir_palavras):
            continue

        # Filtro Palavra-Chave (String Search - mais seguro para frases)
        if lista_palavras_chave:
            encontrou = any(chave.lower() in item['texto_lower'] for chave in lista_palavras_chave)
            if not encontrou: continue

        # Filtro Salário
        if salario_min > 0 and item['salario_num'] < salario_min:
            continue

        # Filtro UF Estrito
        if modo_restritivo:
            if item['uf'] not in lista_ufs_alvo:
                continue

        resultados.append({
            'Salário': item['salario_formatado'],
            'UF': item['uf'],
            'Data Fim Inscrição': item['data_fim'],
            'Informações do Concurso': item['texto'],
            'Link': item['link']
        })

    print(f"--> Filtro aplicado: salario_min={salario_min}, palavras={lista_palavras_chave}, ufs={lista_ufs_alvo}, excluir={excluir_palavras}.")
    print(f"--> Concursos retornados após filtro: {len(resultados)}")
    return resultados

def extrair_link_final(url_base, tipo):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url_base, timeout=10, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        todos_links = soup.find_all('a', href=True)
        
        candidato_melhor = None

        if tipo == 'edital':
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                if 'edital' in text or 'abertura' in text or href.endswith('.pdf'):
                    if 'facebook' not in href and 'twitter' not in href:
                        candidato_melhor = a['href']
                        if href.endswith('.pdf'): break
                            
        elif tipo == 'inscricao':
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                if REGEX_BANCAS.search(href) or REGEX_BANCAS.search(text):
                    if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                        return a['href']

            termos_fortes = ['inscriç', 'inscreva', 'ficha', 'candidato', 'eletrônico', 'formulário', 'site']
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                if any(t in text for t in termos_fortes):
                    if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                        candidato_melhor = a['href']
                        break

        return candidato_melhor if candidato_melhor else url_base
    except:
        return url_base

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

@app.errorhandler(500)
def internal_server_error(e):
    return "<h1>Erro no Servidor</h1><p>Tente novamente em instantes.</p>", 500

@app.route('/api/link-profundo', methods=['POST'])
def api_link_profundo():
    data = request.json or {}
    url_concurso = data.get('url', '')
    tipo = data.get('tipo', 'edital')
    if not url_concurso or url_concurso == '#': return jsonify({'url': '#'})
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

    # LOG DE DEBUG DA BUSCA
    conjunto_ufs_alvo = set(ufs_selecionadas)
    for reg in regioes_selecionadas:
        if reg == 'Nacional': conjunto_ufs_alvo.add('Nacional/Outro')
        elif reg in REGIOES: conjunto_ufs_alvo.update(REGIOES[reg])
    
    lista_final_ufs = list(conjunto_ufs_alvo)

    print("=== Nova busca recebida ===")
    print(f"Salário mínimo bruto: {data.get('salario_minimo')}")
    print(f"Salário mínimo numérico: {salario_minimo}")
    print(f"Palavras-chave: {lista_palavras_chave}")
    print(f"Excluir: {excluir_palavras}")
    print(f"UFs selecionadas: {ufs_selecionadas}")
    print(f"Regiões selecionadas: {regioes_selecionadas}")
    print(f"UFs finais consideradas: {lista_final_ufs}")
    
    todos_dados = obter_dados()
    resultados = filtrar_concursos(todos_dados, salario_minimo, lista_palavras_chave, lista_final_ufs, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
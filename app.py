import re
import os
import time
import json
import locale
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# Configuração do App
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=basedir, static_folder=basedir)
CORS(app)

# Configurações de Persistência
DB_FILE = os.path.join(basedir, 'concursos.json')
CACHE_TIMEOUT = 3600  # 60 minutos (com Keep-Alive)

# Cache em Memória
CACHE_MEMORIA = {
    "timestamp": 0,
    "dados": []
}

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

def formatar_real(valor):
    if valor <= 0: return "Ver Edital/Variável"
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def raspar_dados_online():
    headers = {'User-Agent': 'Mozilla/5.0'}
    print("--> Iniciando raspagem online...")
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

            datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
            data_str = "Indefinida"
            if datas:
                try:
                    data_fim_obj = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                    if data_fim_obj < hoje: continue
                    data_str = data_fim_obj.strftime('%d/%m/%Y')
                except: pass

            salario_num = 0.0
            m = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
            if m:
                try:
                    salario_num = float(m.group(1).replace('.', '').replace(',', '.'))
                except: salario_num = 0.0

            uf_detectada = 'Nacional/Outro'
            for sigla in UFS_SIGLAS:
                if re.search(r'\b' + re.escape(sigla) + r'\b', texto):
                    uf_detectada = sigla
                    break

            lista_processada.append({
                'texto': texto,
                'texto_lower': texto.lower(),
                'link': link_original,
                'data_fim': data_str,
                'salario_num': salario_num,
                'salario_formatado': formatar_real(salario_num),
                'uf': uf_detectada
            })
        
        lista_processada.sort(key=lambda x: x['salario_num'], reverse=True)
        return lista_processada
    except Exception as e:
        print(f"Erro raspagem: {e}")
        return []

def obter_dados():
    global CACHE_MEMORIA
    agora = time.time()

    if CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        print(f"--> Usando CACHE (Expira em {int(CACHE_TIMEOUT - (agora - CACHE_MEMORIA['timestamp']))}s)")
        return CACHE_MEMORIA["dados"]

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                if agora - conteudo.get('timestamp', 0) < CACHE_TIMEOUT:
                    print("--> Usando JSON do Disco")
                    CACHE_MEMORIA["dados"] = conteudo.get('dados', [])
                    CACHE_MEMORIA["timestamp"] = conteudo.get('timestamp', 0)
                    return CACHE_MEMORIA["dados"]
        except: pass

    print("--> Baixando dados novos...")
    novos_dados = raspar_dados_online()
    CACHE_MEMORIA["dados"] = novos_dados
    CACHE_MEMORIA["timestamp"] = agora
    
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": agora, "dados": novos_dados}, f, ensure_ascii=False)
    except: pass

    return novos_dados

def filtrar_concursos(todos_dados, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0

    for item in todos_dados:
        if excluir_palavras and any(ex.lower() in item['texto_lower'] for ex in excluir_palavras):
            continue

        if lista_palavras_chave:
            encontrou = any(chave.lower() in item['texto_lower'] for chave in lista_palavras_chave)
            if not encontrou: continue

        if salario_min > 0 and item['salario_num'] < salario_min:
            continue

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

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/termos')
def termos():
    return "<h1>Termos de Uso</h1><p>Conteúdo em construção...</p>"

@app.route('/privacidade')
def privacidade():
    return "<h1>Política de Privacidade</h1><p>Conteúdo em construção...</p>"

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

    conjunto_ufs_alvo = set(ufs_selecionadas)
    for reg in regioes_selecionadas:
        if reg == 'Nacional': conjunto_ufs_alvo.add('Nacional/Outro')
        elif reg in REGIOES: conjunto_ufs_alvo.update(REGIOES[reg])
    
    lista_final_ufs = list(conjunto_ufs_alvo)
    
    todos_dados = obter_dados()
    resultados = filtrar_concursos(todos_dados, salario_minimo, lista_palavras_chave, lista_final_ufs, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
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
CACHE_TIMEOUT = 900  # 15 minutos

# Cache em Memória (RAM) para acesso instantâneo
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
ibade, objetiva, cespe, cebraspe, ibam, fgv, vunesp, ibfc, idecan, institutomais, 
consulpam, aocp, selecon, fcc, consulplan, ibgp, rbo, igeduc, fundep, fafipa, 
ufrj, pr4, pr-4, avalias, quadrix, legalle, fundatec, nossorumo, amigapublica, 
access, 2dn, omni, facet, cesgranrio, seprod, shdias, idib, consesp, epl, itame, 
funatec, igecs, cefet, publiconsult, ibdo, indepac, msconcursos, fuvest, 
concepcao, lasalle, ctd, carlosbittencourt, avalia, faed, cogeps, fepese, 
avancasp, unifil, ieds, advise, imam, upe, fapec, icap, patativa, uel, iad, 
klc, legatus, ibido, uespi, compec, unicentro, aroeira, ieses, ufpr, educapb, 
uepb, adm&tec, imparh, funvapi, verbena, uece, sousandrade, fumarc, creative, 
sigma, conscam, funece, vicentenelson, furb, cetap, gsassessoria, master, agirh, 
fab.mil, uni.rv, promun, ufma, amac, idht, wedo, fenix, iadhed, uneb, fadesp, 
ufac, ufpe, cetro, unisul, planexcon, ameosc, esaf, dedalus, excelencia, ciee, 
ufmt, cev, funrio, comperve, direcao, fenaz, ibest, abcp, fcm, facape, uerr, 
exercito, copeve, urca, funiversa, iasp, sipros, metodo, usp, faepesul, conesul, 
caip, cetrede, ejud, ian, gsa, cmm, ufrgs, ipefae, iuds, covest, acep, fec, 
consultec, nce, fade, air, unesp, pge, spdm, gualimp, fapems, seap, pontua, 
mpt, cfc, ceperj, ejef, ceps, promunicipio, maranatha, tj-ap, lj, cepros, 
nemesis, fcpc, idesul, fucap, ajuri, ganzaroli, actio, metrocapital, ifsul, 
ufrpe, ufsc, planejar, ufv, metropole, ufam, ufgd, uerj, ufscar, inep, ufla, 
coseac, biorio, movens, faurgs, qconcursos, ares, idesg, tupy, fadenor, mds, 
unesc, fema, serctam, seduc, dae, senai, bigadvice, iniciativa, opgp, alternative, 
perfas, ioplan, cursiva, csc, unicamp, calegariox, schnorr, centec, hcrp, unoesc, 
status, directa, apice, ccv, aprender, mga, assconpp, ufrb, ufrr, omini, iat, 
iff, inqc, ibeg, ineaa, conpass, ibc, framinas, iobv, ufsm, makiyama, puc, 
ufop, unifal, fmz, fesmip, ufba, paqtcpb, integri, unimontes, uff, progepe, 
funjab, fmp, fae, fip, zambini, acafe, reis, fgr, exatus, coned, brb, acaplam, 
fjpf, unifase, referencia, assege, jvl, iasd, unique, econrio, ifbaiano, ufr, 
isba, ufsba, ciesp, mpf, unifeso, esmarn, unichristus, fps, sead, ses, fsa, 
furg, ceaf, ibec, jbo, auctor, darwin, profnit, espm, asconprev, ntcs, fspss, 
avmoreira, univali, fastef, fundepes, ideap, imagine, atena, amazul, fundect, 
banpara, alfa, iamspe, unibave, faepol, nbs, seletiva, crescer, semasa, progesp, 
fiocruz, uva, uri, ethos, consel, jota, epbazi, ckm, rhs, scgas, proam, unespar, 
ufersa, fundape, egp, uem, prograd, inaz, ufca, agata, ciscopar, prime, unilavras, 
igdrh, coelhoneto, progep, segplan, funcepe, funvapi, unifei, indec, orhion, 
nubes, click, iesap, depsec, una, femperj, cislipa, agu, unifesp, sustente, 
uniuv, mgs, utfpr, srh, contemax, funec, copese, funtef, anima, noroeste, ufsj, 
unilab, funcefet, sugep, comvest, ufcg, uepa, coperve, udesc, ueg, fujb, isae, 
ifc, fapese, fadurpe, ufabc, ufpa, ufrrj, ufmg, cepuerj, unemat, unirio, fundec, 
consep, fidesa, unitins, officium, ufpel, cec, unifap, unama, seta, mouramelo, 
magnus, jcm, ipad, igetec, fluxo, fdrh, faperp, fapeu, espp, fat, asperhs, pgt, 
group, idep, uno, educax, fama, comagsul, fronte, jlz, avaliar, exata, flem, 
ibptec, secplan, iset, evo, wisdom, jk, univida, intec, policon, icece, fucapsul, 
avancar, bios, inovaty, fenix, facto, hl, gama, decorp, cl, maxima, arespcj, 
intelectus, abare, univasf, itco
"""

TERMOS_BANCAS = [t.strip() for t in RAW_BANCAS.replace('\n', ',').split(',') if t.strip()]
REGEX_BANCAS = re.compile(r'|'.join(map(re.escape, TERMOS_BANCAS)), re.IGNORECASE)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

def formatar_real(valor):
    if valor <= 0: return "Ver Edital/Variável"
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

# --- 1. FUNÇÃO DE RASPAGEM E PROCESSAMENTO (ETL) ---
# Baixa o HTML, processa tudo e retorna uma lista de dicionários limpos
def raspar_dados_online():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
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
            
            # Extrai Link
            link_original = "#"
            try:
                tag_link = c.find('a')
                if tag_link and 'href' in tag_link.attrs:
                    link_original = tag_link['href']
            except: pass

            # Extrai Data
            datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
            data_fim_obj = None
            data_str = "Indefinida"
            
            if datas:
                try:
                    data_fim_obj = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                    if data_fim_obj < hoje: continue # Ignora vencidos
                    data_str = data_fim_obj.strftime('%d/%m/%Y')
                except: pass

            # Extrai Salário
            salario_num = 0.0
            m = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
            if m:
                try:
                    salario_num = float(m.group(1).replace('.', '').replace(',', '.'))
                except: salario_num = 0.0

            # Extrai UF
            uf_detectada = 'Nacional/Outro'
            for sigla in UFS_SIGLAS:
                if re.search(r'\b' + re.escape(sigla) + r'\b', texto):
                    uf_detectada = sigla
                    break

            # Adiciona item limpo à lista
            lista_processada.append({
                'texto': texto,
                'texto_lower': texto.lower(), # Otimização para busca
                'link': link_original,
                'data_fim': data_str,
                'salario_num': salario_num,
                'salario_formatado': formatar_real(salario_num),
                'uf': uf_detectada
            })
        
        # Ordena por maior salário
        lista_processada.sort(key=lambda x: x['salario_num'], reverse=True)
        print(f"--> Raspagem concluída. {len(lista_processada)} itens processados.")
        return lista_processada

    except Exception as e:
        print(f"--> ERRO CRÍTICO NA RASPAGEM: {e}")
        return []

# --- 2. GERENCIADOR DE DADOS (CACHE + JSON) ---
def obter_dados():
    global CACHE_MEMORIA
    agora = time.time()

    # A. Verifica Memória RAM (Mais rápido)
    if CACHE_MEMORIA["dados"] and (agora - CACHE_MEMORIA["timestamp"] < CACHE_TIMEOUT):
        print("--> Fonte: Memória RAM")
        return CACHE_MEMORIA["dados"]

    # B. Verifica Arquivo JSON (Persistência)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                ts_arquivo = conteudo.get('timestamp', 0)
                
                # Se o arquivo for recente (< 15 min), carrega ele para RAM
                if agora - ts_arquivo < CACHE_TIMEOUT:
                    print("--> Fonte: Arquivo JSON (Disco)")
                    CACHE_MEMORIA["dados"] = conteudo.get('dados', [])
                    CACHE_MEMORIA["timestamp"] = ts_arquivo
                    return CACHE_MEMORIA["dados"]
        except Exception as e:
            print(f"--> Erro ao ler JSON: {e}")

    # C. Se tudo falhar ou expirar: Raspa Online e Salva
    print("--> Fonte: Web Scraping (Atualizando...)")
    novos_dados = raspar_dados_online()
    
    # Salva na RAM
    CACHE_MEMORIA["dados"] = novos_dados
    CACHE_MEMORIA["timestamp"] = agora
    
    # Salva no Disco (JSON)
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": agora, "dados": novos_dados}, f, ensure_ascii=False)
    except Exception as e:
        print(f"--> Erro ao salvar JSON: {e}")

    return novos_dados

# --- 3. FILTRAGEM (Agora trabalha com dicionários limpos) ---
def filtrar_concursos(todos_dados, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0

    for item in todos_dados:
        # Filtro de Exclusão
        if excluir_palavras and any(ex.lower() in item['texto_lower'] for ex in excluir_palavras):
            continue

        # Filtro Palavra Chave (OU)
        if lista_palavras_chave:
            encontrou = any(chave.lower() in item['texto_lower'] for chave in lista_palavras_chave)
            if not encontrou: continue

        # Filtro Salário
        if salario_min > 0 and item['salario_num'] < salario_min:
            continue

        # Filtro UF
        if modo_restritivo:
            if item['uf'] not in lista_ufs_alvo and item['uf'] != 'Nacional/Outro':
                continue

        # Formata para o Front (Mapeia chaves do dict interno para chaves do front)
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
    
    # 1. Obtém dados (Memória > JSON > Web)
    todos_dados = obter_dados()
    
    # 2. Filtra na lista de dicionários
    resultados = filtrar_concursos(todos_dados, salario_minimo, lista_palavras_chave, list(conjunto_ufs_alvo), excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except: pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
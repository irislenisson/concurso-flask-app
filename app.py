import re
import os
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

# --- LISTA DE BANCAS (FORMATO TEXTO BLINDADO) ---
# Estratégia: Usar texto puro (triple quotes) evita erros de sintaxe (vírgulas faltantes)
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

# Processamento Automático: Converte o texto acima em lista, removendo quebras de linha
TERMOS_BANCAS = [t.strip() for t in RAW_BANCAS.replace('\n', ',').split(',') if t.strip()]

# Compila a Regex para busca rápida
REGEX_BANCAS = re.compile(r'|'.join(map(re.escape, TERMOS_BANCAS)), re.IGNORECASE)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

def buscar_concursos():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        print("--> Baixando dados da lista...")
        resp = requests.get(URL_BASE, timeout=30, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.find_all('div', class_='ca')
    except Exception as e:
        print(f"--> ERRO: {e}")
        return []

def formatar_real(valor):
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def filtrar_concursos(concursos, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    hoje = datetime.now().date()
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0

    for c in concursos:
        texto = c.get_text(separator=' ', strip=True)
        texto_lower = texto.lower()
        
        link_original = "#"
        try:
            tag_link = c.find('a')
            if tag_link and 'href' in tag_link.attrs:
                link_original = tag_link['href']
        except: pass

        datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
        data_formatada = "Indefinida"
        if datas:
            try:
                data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                if data_fim < hoje: continue 
                data_formatada = data_fim.strftime('%d/%m/%Y')
            except: pass 

        if excluir_palavras and any(ex.lower() in texto_lower for ex in excluir_palavras): 
            continue

        if lista_palavras_chave:
            encontrou_alguma = any(chave.lower() in texto_lower for chave in lista_palavras_chave)
            if not encontrou_alguma:
                continue

        salario = 0.0
        m = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
        if m:
            try:
                salario = float(m.group(1).replace('.', '').replace(',', '.'))
            except: salario = 0.0
        
        if salario_min > 0 and salario < salario_min: continue

        uf_detectada = 'Nacional/Outro'
        for sigla in UFS_SIGLAS:
            if re.search(r'\b' + re.escape(sigla) + r'\b', texto):
                uf_detectada = sigla
                break
        
        if modo_restritivo:
            if uf_detectada not in lista_ufs_alvo:
                continue

        resultados.append({
            'Salário': formatar_real(salario) if salario > 0 else "Ver Edital/Variável",
            'UF': uf_detectada,
            'Data Fim Inscrição': data_formatada,
            'Informações do Concurso': texto,
            'Link': link_original,
            'raw_salario': salario
        })

    resultados.sort(key=lambda x: x['raw_salario'], reverse=True)
    for r in resultados: del r['raw_salario']

    return resultados

def extrair_link_final(url_base, tipo):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
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
            # FASE 1: Busca via Regex (Lista de Bancas)
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                
                # Se encontrar qualquer termo da nossa lista na URL ou Texto
                if REGEX_BANCAS.search(href) or REGEX_BANCAS.search(text):
                    if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                        return a['href']

            # FASE 2: Busca Genérica
            termos_fortes = ['inscriç', 'inscreva', 'ficha', 'candidato', 'eletrônico', 'formulário', 'site']
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                
                if any(t in text for t in termos_fortes):
                    if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                        candidato_melhor = a['href']
                        break

        return candidato_melhor if candidato_melhor else url_base

    except Exception as e:
        print(f"Erro deep link: {e}")
        return url_base

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/link-profundo', methods=['POST'])
def api_link_profundo():
    data = request.json or {}
    url_concurso = data.get('url', '')
    tipo = data.get('tipo', 'edital')
    
    if not url_concurso or url_concurso == '#':
        return jsonify({'url': '#'})

    url_final = extrair_link_final(url_concurso, tipo)
    return jsonify({'url': url_final})

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    data = request.json or {}
    
    try:
        s_raw = str(data.get('salario_minimo', ''))
        s_clean = re.sub(r'[^\d,]', '', s_raw)
        s_clean = s_clean.replace(',', '.')
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
        if reg == 'Nacional':
            conjunto_ufs_alvo.add('Nacional/Outro')
        elif reg in REGIOES:
            conjunto_ufs_alvo.update(REGIOES[reg])
    
    lista_final_ufs = list(conjunto_ufs_alvo)
    
    todos = buscar_concursos()
    resultados = filtrar_concursos(todos, salario_minimo, lista_palavras_chave, lista_final_ufs, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
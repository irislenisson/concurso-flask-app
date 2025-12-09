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

# --- LISTA DE BANCAS (ORGANIZADA DE A-Z) ---
# Dica: Para adicionar uma nova, basta inserir na ordem alfabética e colocar uma vírgula.
RAW_BANCAS = """
2dn, 4dn, 7dn, 8dn, abare, abcp, acafe, acaplam, access, acep, actio, adm&tec, advise, agata, 
agirh, agu, air, ajuri, alfa, alternative, amac, amazul, ameosc, amigapublica, 
anima, aocp, apice, aprender, ares, arespcj, aroeira, asconprev, asperhs, 
assege, assconpp, atena, auctor, avalia, avaliar, avalias, avancar, avancasp, 
avmoreira, banpara, bigadvice, biorio, bios, brb, caip, calegariox, 
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

# Tratamento Automático da Lista
TERMOS_BANCAS = [t.strip() for t in RAW_BANCAS.replace('\n', ',').split(',') if t.strip()]
REGEX_BANCAS = re.compile(r'|'.join(map(re.escape, TERMOS_BANCAS)), re.IGNORECASE)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

def buscar_concursos():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
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
                
                # Otimização: Regex roda C-level, muito rápido
                if REGEX_BANCAS.search(href) or REGEX_BANCAS.search(text):
                    if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                        return a['href']

            # FASE 2: Busca Genérica (Backup)
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
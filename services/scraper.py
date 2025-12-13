import re
import requests
import random
import logging
import unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Fallback de Constantes
try:
    from constants import URL_BASE, REGEX_DATAS, REGEX_UF
except ImportError:
    URL_BASE = "https://www.pciconcursos.com.br/concursos/"
    REGEX_DATAS = [r'\d{2}/\d{2}/\d{4}', r'\d{2}/\d{2}']
    REGEX_UF = re.compile(r'\b([A-Z]{2})\b')

# User-Agents Rotativos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0"
]

def get_session():
    """Sessão blindada com retries."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def normalizar_texto(texto):
    """Remove acentos e deixa minúsculo (médico -> medico)."""
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn').lower()

def identificar_niveis(texto_normalizado):
    """Detecta escolaridade no texto."""
    niveis = set()
    if any(k in texto_normalizado for k in ['fundamental', 'alfabetizado', 'elementar', 'operacional']):
        niveis.add('fundamental')
    if any(k in texto_normalizado for k in ['medio', 'tecnico', 'assistente', 'ensino medio']):
        niveis.add('medio')
    if any(k in texto_normalizado for k in ['superior', 'graduacao', 'bacharel', 'licenciatura', 'analista', 'especialista', 'medico', 'enfermeiro', 'engenheiro', 'advogado', 'procurador', 'juiz', 'promotor']):
        niveis.add('superior')
    return niveis

def formatar_real(valor):
    if not valor or valor <= 0: return "A consultar / Variável"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_salario(texto):
    valores = re.findall(r'R\$\s*(\d+(?:\.\d{3})*(?:,\d{1,2})?)', texto)
    lista_vals = []
    for v in valores:
        try:
            limpo = v.replace('.', '').replace(',', '.')
            val_float = float(limpo)
            if val_float > 400: lista_vals.append(val_float)
        except: pass
    return max(lista_vals) if lista_vals else 0.0

def extrair_data(texto):
    hoje = datetime.now().date()
    ano_atual = hoje.year
    datas = []
    for padrao in REGEX_DATAS:
        matches = re.findall(padrao, texto)
        for m in matches:
            try:
                partes = m.split('/')
                if len(partes) == 2:
                    ano = ano_atual + 1 if int(partes[1]) < hoje.month else ano_atual
                    dt = datetime(ano, int(partes[1]), int(partes[0])).date()
                else:
                    dt = datetime.strptime(m, '%d/%m/%Y').date()
                datas.append(dt)
            except: pass
    if datas:
        datas.sort()
        return datas[-1]
    return None

def extrair_uf(texto):
    m = REGEX_UF.search(texto)
    if m: return m.group(1).upper()
    estados = {'acre': 'AC', 'alagoas': 'AL', 'amapá': 'AP', 'amazonas': 'AM', 'bahia': 'BA', 'ceará': 'CE', 'distrito federal': 'DF', 'espírito santo': 'ES', 'goiás': 'GO', 'maranhão': 'MA', 'mato grosso': 'MT', 'minas gerais': 'MG', 'pará': 'PA', 'paraíba': 'PB', 'paraná': 'PR', 'pernambuco': 'PE', 'piauí': 'PI', 'rio de janeiro': 'RJ', 'rio grande do norte': 'RN', 'rio grande do sul': 'RS', 'rondônia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC', 'são paulo': 'SP', 'sergipe': 'SE', 'tocantins': 'TO'}
    texto_lower = texto.lower()
    for nome, sigla in estados.items():
        if nome in texto_lower: return sigla
    return "Nacional/Outro"

def raspar_dados_online():
    session = get_session()
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    print("--> [SCRAPER] Iniciando varredura COMPLETA (Broad Search)...")
    
    try:
        resp = session.get(URL_BASE, timeout=25, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # PEGA TUDO: Procura qualquer div que tenha classe (ca, cd, ce, na, etc)
        itens_brutos = soup.find_all('div', attrs={'class': True}) 
        
        lista = []
        hoje = datetime.now().date()
        links_processados = set()

        for item in itens_brutos:
            # Filtro básico de classes conhecidas do PCI
            classes = item.get('class', [])
            if not any(c in classes for c in ['ca', 'cd', 'ce', 'na', 'nc', 'nd']): continue

            try:
                link_tag = item.find('a')
                if not link_tag: continue
                
                texto = item.get_text(" ", strip=True)
                link = link_tag['href']
                
                if link in links_processados or len(texto) < 15: continue
                links_processados.add(link)

                data_fim = extrair_data(texto)
                data_display = "Inscrições Abertas"
                if data_fim:
                    if data_fim < hoje: continue
                    data_display = data_fim.strftime('%d/%m/%Y')
                
                salario = extrair_salario(texto)
                uf = extrair_uf(texto)
                
                # Normalização e Escolaridade
                texto_normalizado = normalizar_texto(texto)
                tokens = set(re.sub(r'[^\w\s]', '', texto_normalizado).split())
                niveis = identificar_niveis(texto_normalizado)

                lista.append({
                    'texto': texto,
                    'texto_normalized': texto_normalizado,
                    'tokens': tokens,
                    'niveis': niveis,
                    'link': link,
                    'data_fim': data_display,
                    'salario_num': salario,
                    'salario_formatado': formatar_real(salario),
                    'uf': uf
                })
            except: continue

        lista.sort(key=lambda x: x['salario_num'], reverse=True)
        print(f"--> [SCRAPER] Sucesso! {len(lista)} concursos encontrados.")
        return lista
    except Exception as e:
        print(f"--> [ERRO] Scraper: {e}")
        return []

def extrair_link_final(url, tipo='edital'): return url 

def filtrar_concursos(todos, sal_min, chaves, ufs, excluir, niveis_filtro=None):
    res = []
    excluir_set = set(normalizar_texto(p) for p in excluir) if excluir else set()
    chaves_norm = [normalizar_texto(k) for k in chaves] if chaves else []
    set_niveis_alvo = set(niveis_filtro) if niveis_filtro else set()

    for item in todos:
        if excluir_set and not excluir_set.isdisjoint(item['tokens']): continue
        if sal_min > 0 and item['salario_num'] < sal_min: continue
        
        if ufs:
            if item['uf'] not in ufs and item['uf'] != 'Nacional/Outro':
                if not any(u in item['texto'] for u in ufs): continue
        
        if chaves_norm:
            if not any(k in item['texto_normalized'] for k in chaves_norm): continue
            
        # Filtro de Escolaridade
        if set_niveis_alvo:
            if set_niveis_alvo.isdisjoint(item['niveis']): continue 

        res.append({
            'Salário': item['salario_formatado'],
            'UF': item['uf'],
            'Data Fim Inscrição': item['data_fim'],
            'Informações do Concurso': item['texto'],
            'Link': item['link']
        })
    return res
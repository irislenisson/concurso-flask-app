import re
import requests
import random
import logging
import unicodedata # <--- Nova importação para lidar com acentos
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Constantes de Fallback
URL_BASE = "https://www.pciconcursos.com.br/concursos/"
REGEX_DATAS = [r'\d{2}/\d{2}/\d{4}', r'\d{2}/\d{2}']
REGEX_UF = re.compile(r'\b([A-Z]{2})\b')

# User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0"
]

def get_session():
    """Cria uma sessão HTTP persistente com reconexão automática."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# --- NOVA FUNÇÃO DE NORMALIZAÇÃO ---
def normalizar_texto(texto):
    """
    Remove acentos e caracteres especiais, deixando tudo em minúsculo.
    Ex: 'Médico Veterinário' -> 'medico veterinario'
    """
    if not texto: return ""
    # 1. Normaliza para NFD (decompõe caracteres)
    # 2. Filtra caracteres que não são espaçamento (tira os acentos)
    # 3. Codifica para ASCII e decodifica de volta para string
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn').lower()

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
            if val_float > 400:
                lista_vals.append(val_float)
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
                if len(partes) == 2: # dd/mm
                    ano = ano_atual + 1 if int(partes[1]) < hoje.month else ano_atual
                    dt = datetime(ano, int(partes[1]), int(partes[0])).date()
                else: # dd/mm/yyyy
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
    
    estados = {
        'acre': 'AC', 'alagoas': 'AL', 'amapá': 'AP', 'amazonas': 'AM', 'bahia': 'BA', 'ceará': 'CE',
        'distrito federal': 'DF', 'espírito santo': 'ES', 'goiás': 'GO', 'maranhão': 'MA',
        'mato grosso': 'MT', 'minas gerais': 'MG', 'pará': 'PA', 'paraíba': 'PB', 'paraná': 'PR',
        'pernambuco': 'PE', 'piauí': 'PI', 'rio de janeiro': 'RJ', 'rio grande do norte': 'RN',
        'rio grande do sul': 'RS', 'rondônia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC',
        'são paulo': 'SP', 'sergipe': 'SE', 'tocantins': 'TO'
    }
    texto_lower = texto.lower()
    for nome, sigla in estados.items():
        if nome in texto_lower: return sigla
    return "Nacional/Outro"

def raspar_dados_online():
    session = get_session()
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    print("--> [SCRAPER] Iniciando varredura TOTAL (Normalizada)...")
    
    try:
        resp = session.get(URL_BASE, timeout=25, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        itens_brutos = soup.find_all('div', attrs={'class': True}) 
        
        lista = []
        hoje = datetime.now().date()
        links_processados = set()

        for item in itens_brutos:
            classes = item.get('class', [])
            if not any(c in classes for c in ['ca', 'cd', 'ce', 'na', 'nc', 'nd']):
                continue

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
                
                # AQUI ESTÁ A MÁGICA:
                # Criamos um campo 'tokens' totalmente sem acentos para facilitar a busca
                texto_normalizado = normalizar_texto(texto)
                tokens = set(re.sub(r'[^\w\s]', '', texto_normalizado).split())

                lista.append({
                    'texto': texto, # Mantemos o texto original bonito para exibir
                    'texto_normalized': texto_normalizado, # Campo oculto para busca
                    'tokens': tokens, # Tokens sem acento
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
        print(f"--> [ERRO CRÍTICO] Scraper falhou: {e}")
        return []

def extrair_link_final(url, tipo='edital'):
    return url 

def filtrar_concursos(todos, sal_min, chaves, ufs, excluir):
    res = []
    
    # Normalizamos as palavras de exclusão do usuário (ex: 'Estágio' -> 'estagio')
    excluir_set = set(normalizar_texto(p) for p in excluir) if excluir else set()
    
    # Normalizamos as palavras-chave de busca (ex: 'Médico' -> 'medico')
    chaves_norm = [normalizar_texto(k) for k in chaves] if chaves else []
    
    for item in todos:
        # 1. Filtro Exclusão (Compara tokens sem acento com exclusão sem acento)
        if excluir_set and not excluir_set.isdisjoint(item['tokens']): continue
        
        # 2. Filtro Salário
        if sal_min > 0 and item['salario_num'] < sal_min: continue
        
        # 3. Filtro UF
        if ufs:
            if item['uf'] not in ufs and item['uf'] != 'Nacional/Outro':
                if not any(u in item['texto'] for u in ufs): continue
        
        # 4. Filtro Palavra-Chave (Agora insensível a acentos)
        if chaves_norm:
            # Verifica se 'medico' está dentro de 'prefeitura de medico...'
            if not any(k in item['texto_normalized'] for k in chaves_norm): continue
            
        res.append({
            'Salário': item['salario_formatado'],
            'UF': item['uf'],
            'Data Fim Inscrição': item['data_fim'],
            'Informações do Concurso': item['texto'],
            'Link': item['link']
        })
    return res
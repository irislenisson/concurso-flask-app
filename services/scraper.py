import re
import requests
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- IMPORTAÇÃO DE CONSTANTES (COM FALLBACK) ---
try:
    from constants import URL_BASE, REGEX_SALARIOS, REGEX_DATAS, REGEX_UF, REGEX_BANCAS
except ImportError:
    URL_BASE = "https://www.pciconcursos.com.br/concursos/"
    REGEX_SALARIOS = [r'R\$\s*(\d+(?:\.\d{3})*(?:,\d{1,2})?)']
    REGEX_DATAS = [r'\d{2}/\d{2}/\d{4}', r'\d{2}/\d{2}']
    REGEX_UF = re.compile(r'\b([A-Z]{2})\b')
    REGEX_BANCAS = re.compile(r'banca|instituto|fundacao', re.IGNORECASE)

# --- CONFIGURAÇÃO ANTI-BLOQUEIO (ÚNICA ADIÇÃO AO SEU CÓDIGO) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0"
]

def get_session():
    """Cria sessão blindada com retries. Essencial para o Render não dar timeout."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# --- SUAS FUNÇÕES ORIGINAIS (MANTIDAS) ---

def formatar_real(valor):
    if valor <= 0: return "Ver Edital/Variável"
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_salario(texto):
    # Lógica original sua, que funcionava bem
    for padrao in REGEX_SALARIOS:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            try:
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
    if m: return m.group(0).upper()
    m2 = re.search(r'prefeitura de ([A-Za-zà-ú]+)', texto, re.IGNORECASE)
    if m2: return "Nacional/Outro" # Mantido seu fallback
    return "Nacional/Outro"

# --- FUNÇÃO PRINCIPAL (COM A CORREÇÃO DE REDE APENAS) ---

def raspar_dados_online():
    # Aqui usamos a sessão blindada e user-agent rotativo
    session = get_session()
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    print("--> [SCRAPER] Iniciando raspagem baseada no modelo original...")
    
    try:
        # Timeout aumentado para 30s como no seu original
        resp = session.get(URL_BASE, timeout=30, headers=headers)
        resp.raise_for_status()
        
        # Encoding forçado para evitar caracteres estranhos
        resp.encoding = resp.apparent_encoding 
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # MANTIDO ESTRITAMENTE O SEU SELETOR ORIGINAL
        itens_brutos = soup.find_all('div', class_='ca')
        
        if not itens_brutos:
            # Fallback de segurança: se 'ca' falhar, tenta pegar tudo, mas prioriza seu metodo
            print("--> Aviso: Classe 'ca' não retornou itens. Tentando fallback amplo.")
            itens_brutos = soup.find_all('div', attrs={'class': True})

        lista_processada = []
        hoje = datetime.now().date()

        for c in itens_brutos:
            # Sua lógica de extração
            texto = c.get_text(separator=' ', strip=True)
            
            # Filtro básico para evitar lixo HTML
            if len(texto) < 20: continue 

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
                if data_fim_obj < hoje: continue # Ignora vencidos
                data_str = data_fim_obj.strftime('%d/%m/%Y')

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
        
        # Ordenação original
        lista_processada.sort(key=lambda x: x['salario_num'], reverse=True)
        print(f"--> [SCRAPER] Sucesso! {len(lista_processada)} itens recuperados.")
        return lista_processada

    except Exception as e:
        print(f"--> ERRO CRÍTICO NA RASPAGEM: {e}")
        return []

def extrair_link_final(url, tipo='edital'):
    # Mantendo simples para evitar erros de execução no Render
    return url

def filtrar_concursos(todos_dados, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    # Sua lógica de filtro exata
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0
    set_exclusao = set(p.lower() for p in excluir_palavras) if excluir_palavras else None

    for item in todos_dados:
        if set_exclusao and 'tokens' in item:
            if not set_exclusao.isdisjoint(item['tokens']): continue
        elif excluir_palavras and any(ex.lower() in item['texto_lower'] for ex in excluir_palavras):
            continue

        if lista_palavras_chave:
            encontrou = any(chave.lower() in item['texto_lower'] for chave in lista_palavras_chave)
            if not encontrou: continue

        if salario_min > 0 and item['salario_num'] < salario_min: continue

        if modo_restritivo:
            if item['uf'] not in lista_ufs_alvo: continue

        resultados.append({
            'Salário': item['salario_formatado'],
            'UF': item['uf'],
            'Data Fim Inscrição': item['data_fim'],
            'Informações do Concurso': item['texto'],
            'Link': item['link']
        })

    return resultados
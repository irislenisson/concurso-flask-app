import re
import requests
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Tenta importar constantes, se falhar usa padrões
try:
    from constants import URL_BASE, REGEX_DATAS, REGEX_UF
except ImportError:
    URL_BASE = "https://www.pciconcursos.com.br/concursos/"
    REGEX_DATAS = [r'\d{2}/\d{2}/\d{4}', r'\d{2}/\d{2}']
    REGEX_UF = re.compile(r'\b([A-Z]{2})\b')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0"
]

def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def formatar_real(valor):
    if not valor or valor <= 0: return "A consultar / Variável"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_salario(texto):
    # Procura valores numéricos monetários
    valores = re.findall(r'R\$\s*(\d+(?:\.\d{3})*(?:,\d{1,2})?)', texto)
    lista_vals = []
    for v in valores:
        try:
            # Limpa formatação brasileira para float python
            limpo = v.replace('.', '').replace(',', '.')
            val_float = float(limpo)
            if val_float > 400: # Ignora taxas de inscrição baixas
                lista_vals.append(val_float)
        except: pass
    return max(lista_vals) if lista_vals else 0.0

def extrair_data(texto):
    hoje = datetime.now().date()
    ano_atual = hoje.year
    datas = []
    
    # Procura qualquer padrão de data
    for padrao in REGEX_DATAS:
        matches = re.findall(padrao, texto)
        for m in matches:
            try:
                partes = m.split('/')
                if len(partes) == 2: # dd/mm
                    # Se o mês for menor que o mês atual, assume ano que vem
                    ano = ano_atual + 1 if int(partes[1]) < hoje.month else ano_atual
                    dt = datetime(ano, int(partes[1]), int(partes[0])).date()
                else: # dd/mm/yyyy
                    dt = datetime.strptime(m, '%d/%m/%Y').date()
                datas.append(dt)
            except: pass
    
    # Retorna a maior data encontrada (presumivelmente o fim da inscrição)
    if datas:
        datas.sort()
        return datas[-1]
    return None

def extrair_uf(texto):
    # Tenta achar sigla (SP, RJ)
    m = REGEX_UF.search(texto)
    if m: return m.group(1).upper()
    
    # Busca textual simples
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
    
    print("--> [SCRAPER] Iniciando varredura ampla...")
    
    try:
        resp = session.get(URL_BASE, timeout=20, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # MUDANÇA CRÍTICA: Pegamos TODAS as divs que podem conter concursos
        # O site usa classes como 'ca', 'cd', 'ce', 'na', etc.
        # Vamos pegar todas as divs que tenham um link direto dentro
        itens_brutos = soup.find_all('div', class_=re.compile(r'\b(ca|cd|ce|na)\b'))
        
        lista = []
        hoje = datetime.now().date()

        for item in itens_brutos:
            try:
                # O texto geralmente está direto na div ou num link dentro dela
                link_tag = item.find('a')
                if not link_tag: continue
                
                texto = item.get_text(" ", strip=True)
                link = link_tag['href']
                
                # Validação mínima: Texto muito curto não é concurso
                if len(texto) < 15: continue

                data_fim = extrair_data(texto)
                
                # Lógica de Data Permissiva:
                # Se achou data e ela já passou, ignora.
                # Se NÃO achou data, INCLUI (melhor pecar pelo excesso do que pela falta).
                data_display = "Em breve / A definir"
                if data_fim:
                    if data_fim < hoje: continue # Vencido
                    data_display = data_fim.strftime('%d/%m/%Y')
                
                salario = extrair_salario(texto)
                uf = extrair_uf(texto)
                
                # Tokenização para busca rápida
                tokens = set(re.sub(r'[^\w\s]', '', texto.lower()).split())

                lista.append({
                    'texto': texto,
                    'texto_lower': texto.lower(),
                    'tokens': tokens,
                    'link': link,
                    'data_fim': data_display,
                    'salario_num': salario,
                    'salario_formatado': formatar_real(salario),
                    'uf': uf
                })
            except: continue

        # Ordena: Maior salário primeiro
        lista.sort(key=lambda x: x['salario_num'], reverse=True)
        print(f"--> [SCRAPER] Sucesso! {len(lista)} itens recuperados.")
        return lista

    except Exception as e:
        print(f"--> [ERRO] Falha no scraper: {e}")
        return []

# Mantendo a função de extrair link final simples para evitar timeouts
def extrair_link_final(url, tipo='edital'):
    return url 

# Mantendo compatibilidade com seu filtro
def filtrar_concursos(todos, sal_min, chaves, ufs, excluir):
    res = []
    excluir_set = set(p.lower() for p in excluir) if excluir else set()
    
    for item in todos:
        # Filtro Exclusão
        if excluir_set and not excluir_set.isdisjoint(item['tokens']): continue
        
        # Filtro Salário
        if sal_min > 0 and item['salario_num'] < sal_min: continue
        
        # Filtro UF
        if ufs:
            if item['uf'] not in ufs and item['uf'] != 'Nacional/Outro':
                # Tenta match no texto
                if not any(u in item['texto'] for u in ufs): continue
        
        # Filtro Palavra-Chave
        if chaves:
            if not any(k.lower() in item['texto_lower'] for k in chaves): continue
            
        res.append({
            'Salário': item['salario_formatado'],
            'UF': item['uf'],
            'Data Fim Inscrição': item['data_fim'],
            'Informações do Concurso': item['texto'],
            'Link': item['link']
        })
    return res
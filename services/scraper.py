import re
import requests
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- IMPORTANDO CONSTANTES (Mantendo compatibilidade com seu projeto) ---
try:
    from constants import (
        URL_BASE, REGEX_SALARIOS, REGEX_DATAS, REGEX_UF, REGEX_BANCAS
    )
except ImportError:
    # Fallback para evitar crash se rodar isolado
    URL_BASE = "https://www.pciconcursos.com.br/concursos/"
    REGEX_SALARIOS = [r'R\$\s*(\d+(?:\.\d{3})*(?:,\d{1,2})?)']
    REGEX_DATAS = [r'\d{2}/\d{2}/\d{4}', r'\d{2}/\d{2}']
    REGEX_UF = re.compile(r'\b([A-Z]{2})\b')
    REGEX_BANCAS = re.compile(r'banca|instituto|fundacao', re.IGNORECASE)

# Configuração de Logging (Melhor que print para debug em produção)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- CONFIGURAÇÃO ANTI-BLOQUEIO ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
]

def get_session():
    """Cria uma sessão HTTP robusta que tenta reconectar 3 vezes se falhar."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---

def formatar_real(valor):
    if not valor or valor <= 0: return "A consultar / Variável"
    # Formatação brasileira manual para garantir precisão
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_salario(texto):
    """
    Melhoria Padrão Ouro: Busca TODOS os valores monetários no texto
    e retorna o MAIOR deles (Teto salarial), ignorando valores baixos irreais.
    """
    valores_encontrados = []
    
    # Remove pontos de milhar temporariamente para facilitar regex
    texto_limpo = texto.replace('.', '')
    
    # Busca genérica por padrões monetários (ex: 5000,00 ou 5000)
    matches = re.findall(r'R\$\s*(\d+(?:,\d{1,2})?)', texto)
    
    for m in matches:
        try:
            val = float(m.replace('.', '').replace(',', '.'))
            if val > 400: # Filtra taxas de inscrição confundidas com salário
                valores_encontrados.append(val)
        except: pass
    
    # Se achou valores, retorna o maior (mais atrativo). Se não, 0.0
    return max(valores_encontrados) if valores_encontrados else 0.0

def extrair_data(texto):
    hoje = datetime.now().date()
    ano_atual = hoje.year
    
    datas_encontradas = []
    
    # Procura todas as datas possíveis
    for padrao in REGEX_DATAS:
        matches = re.findall(padrao, texto)
        for data_str in matches:
            try:
                partes = data_str.split('/')
                if len(partes) == 2: # dd/mm -> Adiciona ano
                    # Se mês for menor que atual, provavelmente é ano que vem
                    ano_data = ano_atual + 1 if int(partes[1]) < hoje.month else ano_atual
                    data_str = f"{partes[0]}/{partes[1]}/{ano_data}"
                elif len(partes) == 3 and len(partes[2]) == 2:
                    partes[2] = "20" + partes[2]
                    data_str = "/".join(partes)
                
                dt_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                datas_encontradas.append(dt_obj)
            except: pass
            
    # Retorna a última data válida encontrada (geralmente é o fim da inscrição)
    if datas_encontradas:
        # Filtra datas passadas muito antigas (ex: erro de extração)
        datas_futuras = [d for d in datas_encontradas if d >= hoje]
        return datas_futuras[-1] if datas_futuras else datas_encontradas[-1]
    
    return None

def extrair_uf(texto):
    # 1. Tenta Regex Padrão (XX)
    m = REGEX_UF.search(texto)
    if m: return m.group(1).upper()
    
    # 2. Busca textual inteligente por Estados
    estados = {
        'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA', 'ceara': 'CE',
        'distrito federal': 'DF', 'espirito santo': 'ES', 'goias': 'GO', 'maranhao': 'MA',
        'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG', 'para': 'PA',
        'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI', 'rio de janeiro': 'RJ',
        'rio grande do norte': 'RN', 'rio grande do sul': 'RS', 'rondonia': 'RO', 'roraima': 'RR',
        'santa catarina': 'SC', 'sao paulo': 'SP', 'sergipe': 'SE', 'tocantins': 'TO'
    }
    texto_lower = texto.lower()
    for nome, sigla in estados.items():
        if f" {nome} " in f" {texto_lower} ": # Espaços evitam falsos positivos (ex: 'para' preposição)
            return sigla
            
    return "Nacional/Outro"

def extrair_link_final(url_base, tipo):
    """Refatorado com Timeout e Session para não travar o servidor."""
    session = get_session()
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        # Timeout curto (5s) pois o usuário está esperando
        resp = session.get(url_base, timeout=5, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        todos_links = soup.find_all('a', href=True)
        
        candidato_melhor = None

        if tipo == 'edital':
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                # Prioridade máxima para PDFs
                if href.endswith('.pdf'): return a['href']
                
                if 'edital' in text or 'abertura' in text:
                    if 'facebook' not in href: candidato_melhor = a['href']
                            
        elif tipo == 'inscricao':
            termos_fortes = ['inscriç', 'inscreva', 'ficha', 'formulário', 'site da banca']
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                
                # Prioridade 1: Link da Banca
                if REGEX_BANCAS and (REGEX_BANCAS.search(href) or REGEX_BANCAS.search(text)):
                    if 'pciconcursos' not in href and '.pdf' not in href: return a['href']
                
                # Prioridade 2: Termos de inscrição
                if any(t in text for t in termos_fortes):
                     if 'pciconcursos' not in href: candidato_melhor = a['href']

        return candidato_melhor if candidato_melhor else url_base
    except Exception as e:
        logging.warning(f"Erro ao extrair link profundo: {e}")
        return url_base

# --- FUNÇÕES PRINCIPAIS ---

def raspar_dados_online():
    """
    Núcleo do Scraper: Baixa, processa e estrutura os dados.
    Agora com rotação de IP (via User-Agent) e tratamento de erros por item.
    """
    session = get_session()
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    logging.info("--> [SERVICE] Iniciando raspagem blindada...")
    
    try:
        resp = session.get(URL_BASE, timeout=20, headers=headers)
        resp.raise_for_status()
        
        # Garante encoding correto (PT-BR)
        resp.encoding = resp.apparent_encoding
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Aceita 'ca' (padrão) ou 'na' (destaque) ou 'cd' (novo layout)
        itens_brutos = soup.find_all('div', class_=['ca', 'na', 'cd'])
        
        lista_processada = []
        hoje = datetime.now().date()

        for c in itens_brutos:
            try:
                texto = c.get_text(separator=' ', strip=True)
                
                # Extração de Link (Defensiva)
                tag_link = c.find('a')
                if not tag_link or 'href' not in tag_link.attrs: continue
                link_original = tag_link['href']

                # Extração de Metadados
                data_fim_obj = extrair_data(texto)
                
                # Validação de Data: Se expirou ontem, não mostre.
                if data_fim_obj and data_fim_obj < hoje: continue
                data_str = data_fim_obj.strftime('%d/%m/%Y') if data_fim_obj else "Em breve"

                salario_num = extrair_salario(texto)
                uf_detectada = extrair_uf(texto)

                # OTIMIZAÇÃO DE BUSCA: Tokens limpos (Set)
                texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
                tokens_set = set(texto_limpo.split()) # Set é mais rápido que list para buscas

                lista_processada.append({
                    'texto': texto,
                    'texto_lower': texto.lower(), # Cache para filtros
                    'tokens': tokens_set,         # Cache para performance
                    'link': link_original,
                    'data_fim': data_str,
                    'salario_num': salario_num,
                    'salario_formatado': formatar_real(salario_num),
                    'uf': uf_detectada
                })
            except Exception as e:
                # Se um item falhar, loga e continua para o próximo (não quebra o scrape)
                continue
        
        # Ordena por maior salário primeiro (Melhor UX)
        lista_processada.sort(key=lambda x: x['salario_num'], reverse=True)
        
        logging.info(f"--> [SERVICE] Raspagem concluída. {len(lista_processada)} itens encontrados.")
        return lista_processada

    except Exception as e:
        logging.error(f"--> [CRITICAL] Falha total na raspagem: {e}")
        return []

def filtrar_concursos(todos_dados, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    """
    Filtra os dados raspados com alta performance.
    """
    resultados = []
    modo_restritivo_uf = len(lista_ufs_alvo) > 0
    
    # Prepara sets para velocidade O(1)
    set_exclusao = set(p.lower().strip() for p in excluir_palavras) if excluir_palavras else None
    
    # Prepara palavras-chave (normalizadas)
    chaves_norm = [k.lower().strip() for k in lista_palavras_chave] if lista_palavras_chave else []

    for item in todos_dados:
        # 1. Filtro de Exclusão (Rápido)
        if set_exclusao:
            # Verifica interseção de conjuntos (Muito rápido)
            if not set_exclusao.isdisjoint(item['tokens']): continue

        # 2. Filtro de UF
        if modo_restritivo_uf:
            # Se não for a UF exata E não for Nacional
            if item['uf'] not in lista_ufs_alvo and item['uf'] != 'Nacional/Outro':
                # Última chance: Procura a sigla no texto
                if not any(uf_alvo in item['texto'] for uf_alvo in lista_ufs_alvo):
                    continue

        # 3. Filtro de Salário
        if salario_min > 0 and item['salario_num'] < salario_min:
            continue
            
        # 4. Filtro Palavra-Chave (Lógica OR - se tiver QUALQUER uma, passa)
        if chaves_norm:
            # Verifica se alguma palavra chave é substring do texto ou dos tokens
            match = False
            for chave in chaves_norm:
                if chave in item['texto_lower']:
                    match = True
                    break
            if not match: continue

        # Formata para o Frontend (Mantendo chaves originais do seu projeto)
        resultados.append({
            'Salário': item['salario_formatado'],
            'UF': item['uf'],
            'Data Fim Inscrição': item['data_fim'],
            'Informações do Concurso': item['texto'],
            'Link': item['link']
        })

    return resultados
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Importando constantes da raiz
# O Python consegue achar isso porque quem executa o projeto é o app.py na raiz
from constants import (
    URL_BASE, REGEX_SALARIOS, REGEX_DATAS, REGEX_UF, REGEX_BANCAS
)

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---

def formatar_real(valor):
    if valor <= 0: return "Ver Edital/Variável"
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_salario(texto):
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
                # Caso: dd/mm (sem ano) -> Adiciona ano atual
                if len(partes) == 2:  
                    data_str = f"{partes[0]}/{partes[1]}/{ano_atual}"
                # Caso: dd/mm/aa (ano 2 dígitos) -> Transforma em 20aa
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
    # Fallback para prefeituras sem UF explícita
    m2 = re.search(r'prefeitura de ([A-Za-zà-ú]+)', texto, re.IGNORECASE)
    if m2:
        return "Nacional/Outro"
    return "Nacional/Outro"

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

# --- FUNÇÕES PRINCIPAIS ---

def raspar_dados_online():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    print("--> Iniciando raspagem online (Service)...")
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
                if data_fim_obj < hoje: continue # Ignora vencidos
                data_str = data_fim_obj.strftime('%d/%m/%Y')

            # OTIMIZAÇÃO: Pré-computar tokens para busca rápida
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
        return lista_processada

    except Exception as e:
        print(f"--> ERRO CRÍTICO NA RASPAGEM: {e}")
        return []

def filtrar_concursos(todos_dados, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0
    
    # Pré-computa set de exclusão para performance O(1)
    set_exclusao = set(p.lower() for p in excluir_palavras) if excluir_palavras else None

    for item in todos_dados:
        # 1. Filtro de Exclusão Otimizado (Set)
        if set_exclusao and 'tokens' in item:
            # Se houver qualquer intersecção entre palavras proibidas e do concurso, pula
            if not set_exclusao.isdisjoint(item['tokens']): continue
        elif excluir_palavras and any(ex.lower() in item['texto_lower'] for ex in excluir_palavras):
            continue

        # 2. Filtro Palavra-Chave
        if lista_palavras_chave:
            encontrou = any(chave.lower() in item['texto_lower'] for chave in lista_palavras_chave)
            if not encontrou: continue

        # 3. Filtro Salário
        if salario_min > 0 and item['salario_num'] < salario_min:
            continue

        # 4. Filtro UF (Estrito)
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
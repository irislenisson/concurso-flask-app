import re
import os
import locale
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

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

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

def buscar_concursos():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        print("--> Baixando dados...")
        resp = requests.get(URL_BASE, timeout=30, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.find_all('div', class_='ca')
    except Exception as e:
        print(f"--> ERRO: {e}")
        return []

def formatar_real(valor):
    """Converte float para string no formato R$ 1.234,56"""
    # Formata como 1,234.56
    formatado = f"{valor:,.2f}"
    # Troca vírgula por X, ponto por vírgula, e X por ponto
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def filtrar_concursos(concursos, salario_min, palavra_chave, lista_ufs_alvo, excluir_palavras):
    hoje = datetime.now().date()
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0

    for c in concursos:
        texto = c.get_text(separator=' ', strip=True)
        
        datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
        data_formatada = "Indefinida"
        if datas:
            try:
                data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                if data_fim < hoje: continue 
                data_formatada = data_fim.strftime('%d/%m/%Y')
            except: pass 

        if excluir_palavras and any(ex.lower() in texto.lower() for ex in excluir_palavras): continue
        if palavra_chave and palavra_chave.lower() not in texto.lower(): continue

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
            # AQUI ESTÁ A CORREÇÃO DE FORMATAÇÃO
            'Salário': formatar_real(salario) if salario > 0 else "Ver Edital/Variável",
            'UF': uf_detectada,
            'Data Fim Inscrição': data_formatada,
            'Informações do Concurso': texto,
            'raw_salario': salario
        })

    resultados.sort(key=lambda x: x['raw_salario'], reverse=True)
    for r in resultados: del r['raw_salario']

    return resultados

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    data = request.json or {}
    
    try:
        s_raw = str(data.get('salario_minimo', ''))
        s_clean = re.sub(r'[^\d,]', '', s_raw)
        s_clean = s_clean.replace(',', '.')
        salario_minimo = float(s_clean) if s_clean else 0.0
    except Exception as e:
        print(f"Erro ao converter salario: {e}")
        salario_minimo = 0.0

    palavra_chave = data.get('palavra_chave', '').strip()
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
    resultados = filtrar_concursos(todos, salario_minimo, palavra_chave, lista_final_ufs, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
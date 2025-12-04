import re
import os
import locale
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# Configuração de Caminho Absoluto
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=basedir, static_folder=basedir)
CORS(app)

UFS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

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

def filtrar_concursos(concursos, salario_min, palavra_chave, uf_filtro, excluir_palavras):
    hoje = datetime.now().date()
    resultados = []

    for c in concursos:
        texto = c.get_text(separator=' ', strip=True)
        
        # Filtro Data
        datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
        data_formatada = "Indefinida"
        if datas:
            try:
                data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                if data_fim < hoje: continue 
                data_formatada = data_fim.strftime('%d/%m/%Y')
            except: pass 

        # Filtro Palavras
        if excluir_palavras and any(ex.lower() in texto.lower() for ex in excluir_palavras): continue
        if palavra_chave and palavra_chave.lower() not in texto.lower(): continue

        # Tratamento Salário
        salario = 0.0
        m = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
        if m:
            try:
                salario = float(m.group(1).replace('.', '').replace(',', '.'))
            except: salario = 0.0
        
        if salario_min > 0 and salario < salario_min: continue

        # Identificação UF
        uf_detectada = 'Nacional/Outro'
        for sigla in UFS:
            if re.search(r'\b' + re.escape(sigla) + r'\b', texto):
                uf_detectada = sigla
                break
        
        if uf_filtro and uf_filtro != '' and uf_detectada != uf_filtro: continue

        resultados.append({
            'Salário': f"R$ {salario:,.2f}".replace('.', ',') if salario > 0 else "Ver Edital/Variável",
            'UF': uf_detectada,
            'Data Fim Inscrição': data_formatada,
            'Informações do Concurso': texto,
            'raw_salario': salario # Campo oculto usado apenas para ordenar
        })

    # ORDENAÇÃO: Ordena a lista usando o valor numérico (raw_salario) do maior para o menor
    resultados.sort(key=lambda x: x['raw_salario'], reverse=True)

    # Limpeza: Remove o campo auxiliar antes de enviar para o front
    for r in resultados:
        del r['raw_salario']

    return resultados

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    data = request.json or {}
    try:
        s_raw = data.get('salario_minimo')
        salario_minimo = float(s_raw) if s_raw else 0.0
    except: salario_minimo = 0.0

    palavra_chave = data.get('palavra_chave', '').strip()
    uf = data.get('uf', '').strip()
    excluir_str = data.get('excluir_palavra', '')
    excluir_palavras = [p.strip() for p in excluir_str.split(',') if p.strip()]
    
    todos = buscar_concursos()
    resultados = filtrar_concursos(todos, salario_minimo, palavra_chave, uf, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
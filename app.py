import re
import os
import locale
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__, template_folder='.')
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
        print("--> Baixando dados do PCI Concursos...")
        resp = requests.get(URL_BASE, timeout=30, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        itens = soup.find_all('div', class_='ca')
        print(f"--> Download concluído. {len(itens)} itens encontrados para processar.")
        return itens
    except Exception as e:
        print(f"--> ERRO DE CONEXÃO: {e}")
        return []

def filtrar_concursos(concursos, salario_min, palavra_chave, uf_filtro, excluir_palavras):
    hoje = datetime.now().date()
    resultados = []
    print(f"--> Iniciando filtro: Min R${salario_min} | Chave: '{palavra_chave}'")

    for c in concursos:
        texto = c.get_text(separator=' ', strip=True)
        
        # 1. Filtro de Data (Mantém apenas inscrições abertas)
        datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
        data_fim = None
        data_formatada = "Indefinida"
        
        if datas:
            try:
                # Pega a última data encontrada no texto
                data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                if data_fim < hoje:
                    continue # Ignora concursos vencidos
                data_formatada = data_fim.strftime('%d/%m/%Y')
            except:
                pass # Se der erro na data, não joga fora, apenas segue

        # 2. Filtro de Exclusão
        if excluir_palavras and any(ex.lower() in texto.lower() for ex in excluir_palavras):
            continue

        # 3. Filtro de Palavra Chave
        if palavra_chave and palavra_chave.lower() not in texto.lower():
            continue

        # 4. Tratamento de Salário (CORREÇÃO PRINCIPAL)
        salario = 0.0
        # Regex flexível para achar R$ 1.000,00 ou R$1000,00
        m = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
        
        if m:
            try:
                salario = float(m.group(1).replace('.', '').replace(',', '.'))
            except:
                salario = 0.0
        
        # Se o usuário pediu um salário mínimo e este concurso paga menos (ou não informa), ignora
        if salario_min > 0 and salario < salario_min:
            continue

        # 5. Filtro de UF
        uf_detectada = 'Nacional/Outro'
        for sigla in UFS:
            # Procura a sigla isolada (ex: " SP ", mas não dentro de "VESPA")
            if re.search(r'\b' + re.escape(sigla) + r'\b', texto):
                uf_detectada = sigla
                break
        
        if uf_filtro and uf_filtro != '' and uf_detectada != uf_filtro:
            continue

        resultados.append({
            'Salário': f"R$ {salario:,.2f}".replace('.', ',') if salario > 0 else "Ver Edital/Variável",
            'UF': uf_detectada,
            'Data Fim Inscrição': data_formatada,
            'Informações do Concurso': texto
        })

    print(f"--> Resultados finais filtrados: {len(resultados)}")
    return resultados

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    data = request.json or {}
    
    try:
        # Garante que o salário seja número
        s_raw = data.get('salario_minimo')
        salario_minimo = float(s_raw) if s_raw else 0.0
    except:
        salario_minimo = 0.0

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
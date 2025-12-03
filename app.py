# app.py
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
UFS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']

@app.route('/', methods=['GET', 'POST'])
def index():
    concursos = []

    if request.method == 'POST':
        salario_min = request.form.get('salario_min')
        palavra = request.form.get('palavra')
        uf = request.form.get('uf')
        excluir = request.form.get('excluir')

        try:
            salario_min = float(salario_min or 0)
        except ValueError:
            salario_min = 0

        concursos = buscar_concursos(salario_min, palavra, excluir, uf)

    return render_template('index.html', concursos=concursos, ufs=UFS)

def buscar_concursos(salario_min, palavra, excluir, uf):
    concursos = []
    try:
        response = requests.get(URL_BASE, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        blocos = soup.find_all('div', class_='ca')

        for bloco in blocos:
            texto = bloco.get_text(" ", strip=True)

            salario_match = re.search(r'R\$\s?([\d\.]+,\d{2})', texto)
            if not salario_match:
                continue

            salario = float(salario_match.group(1).replace('.', '').replace(',', '.'))
            if salario < salario_min:
                continue

            if palavra and palavra.lower() not in texto.lower():
                continue

            if excluir and excluir.lower() in texto.lower():
                continue

            uf_match = re.search(r'\b(' + '|'.join(UFS) + r')\b', texto)
            uf_encontrado = uf_match.group(1) if uf_match else 'N/A'

            if uf and uf != 'Todas' and uf != uf_encontrado:
                continue

            data_match = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
            data_fim = data_match[-1] if data_match else '--'

            concursos.append({
                'salario': f'R$ {salario:,.2f}'.replace(',', 'v').replace('.', ',').replace('v', '.'),
                'uf': uf_encontrado,
                'data_fim': data_fim,
                'info': texto
            })

    except Exception as e:
        print("Erro ao buscar concursos:", e)

    return concursos

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

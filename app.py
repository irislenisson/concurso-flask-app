
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import pandas as pd
import re
import locale

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
UFS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']

@app.route('/', methods=['GET', 'POST'])
def index():
    resultados = []

    if request.method == 'POST':
        salario_min = float(request.form.get('salario', 12000))
        palavra = request.form.get('palavra', '').lower()
        excluir = request.form.get('excluir', '').lower()
        uf = request.form.get('uf', '')

        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL_BASE, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        concursos = soup.find_all('div', class_='ca')

        regex_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
        regex_salario = re.compile(r'R\$[\s]*([\d\.]+,\d{2})')

        hoje = datetime.now().date()

        for concurso in concursos:
            texto = concurso.get_text(separator=' ', strip=True).lower()
            link = concurso.find('a')['href'] if concurso.find('a') else '#'

            datas = regex_data.findall(texto)
            if not datas:
                continue
            data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
            if hoje > data_fim:
                continue

            if excluir and excluir in texto:
                continue

            if palavra and palavra not in texto:
                continue

            sal_match = regex_salario.search(texto)
            if not sal_match:
                continue
            salario = float(sal_match.group(1).replace('.', '').replace(',', '.'))
            if salario < salario_min:
                continue

            uf_match = next((uf_sigla for uf_sigla in UFS if uf_sigla.lower() in texto), 'Outro')
            if uf and uf != uf_match:
                continue

            resultados.append({
                'UF': uf_match.upper(),
                'Salário': f"{salario:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','),
                'Data Fim Inscrição': data_fim.strftime('%d/%m/%Y'),
                'Informações do Concurso': texto,
                'link': link
            })

        resultados.sort(key=lambda x: float(x['Salário'].replace('.', '').replace(',', '.')), reverse=True)

    return render_template("index.html", resultados=resultados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

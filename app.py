from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import pandas as pd

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
SALARIO_MINIMO = 12000
PALAVRAS_EXCLUIR = [
    'prefeitura', 'médico', 'médico superior', 'polícia militar',
    'Engenheiro Mecânico Superior', 'bombeiro militar', 'Corpo de Bombeiros Militar'
]
UFS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def buscar_concursos(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        concursos = soup.find_all('div', class_='ca')
        return concursos
    except requests.exceptions.RequestException:
        return None


def processar_dados(concursos):
    concursos_filtrados = []
    hoje = datetime.now().date()

    regex_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
    regex_excluir = re.compile(r'\b(' + '|'.join(map(re.escape, PALAVRAS_EXCLUIR)) + r')\b', re.IGNORECASE)
    regex_salario = re.compile(r'R\$[\s]*([\d\.]+,\d{2})')
    regex_ufs = re.compile(r'\b(' + '|'.join(UFS) + r')\b')

    for concurso in concursos:
        info_completa = concurso.get_text(separator=' ', strip=True)

        todas_as_datas = regex_data.findall(info_completa)
        if not todas_as_datas:
            continue

        data_fim_str = todas_as_datas[-1]
        try:
            data_fim = datetime.strptime(data_fim_str, '%d/%m/%Y').date()
            if hoje > data_fim:
                continue
        except ValueError:
            continue

        if regex_excluir.search(info_completa):
            continue

        salario_match = regex_salario.search(info_completa)
        if not salario_match:
            continue

        try:
            salario_float = float(salario_match.group(1).replace('.', '').replace(',', '.'))
            if salario_float < SALARIO_MINIMO:
                continue
        except ValueError:
            continue

        uf_match = regex_ufs.search(info_completa)
        uf = uf_match.group(1) if uf_match else 'Nacional/Outro'

        concursos_filtrados.append({
            'Data Fim Inscrição': data_fim.strftime('%d/%m/%Y'),
            'UF': uf,
            'Salário': formatar_moeda(salario_float),
            'Salario_Numerico': salario_float,
            'Informações do Concurso': info_completa
        })

    concursos_filtrados.sort(key=lambda x: (-x['Salario_Numerico'], x['UF']))
    return concursos_filtrados


@app.route('/', methods=['GET', 'POST'])
def index():
    concursos_filtrados = []
    if request.method == 'POST':
        lista_concursos_html = buscar_concursos(URL_BASE)
        if lista_concursos_html:
            concursos_filtrados = processar_dados(lista_concursos_html)

    return render_template('index.html', concursos=concursos_filtrados)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

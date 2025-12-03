from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
from datetime import datetime

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
UFS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def buscar_concursos(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.find_all('div', class_='ca')
    except Exception as e:
        return str(e)

def processar_dados(concursos, salario_minimo, uf_filtro, palavra_excluir):
    concursos_filtrados = []
    hoje = datetime.now().date()

    regex_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
    regex_salario = re.compile(r'R\$[\s]*([\d\.]+,\d{2})')
    regex_ufs = re.compile(r'\b(' + '|'.join(UFS) + r')\b')
    regex_excluir = re.compile(r'\b(' + '|'.join(map(re.escape, palavra_excluir)) + r')\b', re.IGNORECASE) if palavra_excluir else None

    for concurso in concursos:
        info_completa = concurso.get_text(separator=' ', strip=True)

        if regex_excluir and regex_excluir.search(info_completa):
            continue

        salario_match = regex_salario.search(info_completa)
        if not salario_match:
            continue

        try:
            salario_float = float(salario_match.group(1).replace('.', '').replace(',', '.'))
            if salario_float < salario_minimo:
                continue
        except:
            continue

        todas_as_datas = regex_data.findall(info_completa)
        if not todas_as_datas:
            continue
        try:
            data_fim = datetime.strptime(todas_as_datas[-1], '%d/%m/%Y').date()
            if hoje > data_fim:
                continue
        except:
            continue

        uf_match = regex_ufs.search(info_completa)
        uf = uf_match.group(1) if uf_match else 'Nacional/Outro'

        if uf_filtro and uf != uf_filtro:
            continue

        concursos_filtrados.append({
            'Data Fim Inscrição': data_fim.strftime('%d/%m/%Y'),
            'UF': uf,
            'Salário': formatar_moeda(salario_float),
            'Informações do Concurso': info_completa
        })

    return concursos_filtrados

@app.route('/', methods=['GET', 'POST'])
def index():
    concursos = []
    erro = None
    salario_minimo = 0
    uf_filtro = ''
    palavra_excluir = ''

    if request.method == 'POST':
        try:
            salario_minimo = float(request.form.get('salario_minimo', '0').replace('.', '').replace(',', '.'))
        except:
            salario_minimo = 0

        uf_filtro = request.form.get('uf', '').strip().upper()
        palavra_excluir = request.form.get('palavra_excluir', '').strip()
        lista_excluir = [palavra.strip() for palavra in palavra_excluir.split(',')] if palavra_excluir else []

        resultado = buscar_concursos(URL_BASE)
        if isinstance(resultado, str):
            erro = f"Erro ao buscar concursos: {resultado}"
        else:
            concursos = processar_dados(resultado, salario_minimo, uf_filtro, lista_excluir)

    return render_template('index.html', concursos=concursos, erro=erro)

if __name__ == '__main__':
    app.run(debug=True)

import re
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
from datetime import datetime

app = Flask(__name__)

URL_BASE = "https://www.pciconcursos.com.br/concursos/"

UFS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

def buscar_concursos():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(URL_BASE, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        concursos = soup.find_all('div', class_='ca')
        print(f"⚠️ Encontrados {len(concursos)} blocos com class='ca'")
        return concursos
    except Exception as e:
        print(f"Erro ao buscar concursos: {e}")
        return []

def filtrar_concursos(concursos, salario_min, palavra, uf, palavras_excluir):
    filtrados = []
    hoje = datetime.now().date()

    regex_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
    regex_salario = re.compile(r'R\$[\s]*([\d\.]+,\d{2})')
    regex_excluir = re.compile(r'\b(' + '|'.join(map(re.escape, palavras_excluir)) + r')\b', re.IGNORECASE)
    regex_uf = re.compile(r'\b(' + '|'.join(UFS) + r')\b', re.IGNORECASE)

    for concurso in concursos:
        texto = concurso.get_text(separator=' ', strip=True)

        if palavras_excluir and regex_excluir.search(texto):
            continue

        if palavra and palavra.lower() not in texto.lower():
            continue

        data_match = regex_data.findall(texto)
        if not data_match:
            continue
        try:
            data_fim = datetime.strptime(data_match[-1], '%d/%m/%Y').date()
            if data_fim < hoje:
                continue
        except:
            continue

        salario_match = regex_salario.search(texto)
        if not salario_match:
            continue

        try:
            salario_float = float(salario_match.group(1).replace('.', '').replace(',', '.'))
            if salario_min and salario_float < salario_min:
                continue
        except:
            continue

        uf_match = regex_uf.search(texto)
        uf_encontrada = uf_match.group(1).upper() if uf_match else 'Nacional/Outro'
        if uf and uf_encontrada != uf:
            continue

        salario_formatado = f"R$ {salario_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        filtrados.append({
            'salario': salario_formatado,
            'uf': uf_encontrada,
            'data': data_match[-1],
            'info': texto
        })

    return filtrados

@app.route('/', methods=['GET', 'POST'])
def index():
    concursos_filtrados = []
    if request.method == 'POST':
        try:
            salario_min = float(request.form.get('salario_minimo', '0').strip()) or 0
        except:
            salario_min = 0

        palavra = request.form.get('palavra_chave', '').strip()
        uf = request.form.get('uf', '').strip().upper()
        palavras_excluir = request.form.get('palavras_excluir', '').split(',')

        concursos_html = buscar_concursos()
        concursos_filtrados = filtrar_concursos(concursos_html, salario_min, palavra, uf, palavras_excluir)

    return render_template('index.html', concursos=concursos_filtrados)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

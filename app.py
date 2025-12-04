from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
UFS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

def buscar_concursos():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
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
    concursos_filtrados = []
    hoje = datetime.now().date()

    regex_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
    regex_salario = re.compile(r'R\$[\s]*([\d\.]+,\d{2})')
    regex_uf = re.compile(r'\b(' + '|'.join(UFS) + r')\b')
    regex_excluir = re.compile(r'\b(' + '|'.join(map(re.escape, palavras_excluir)) + r')\b', re.IGNORECASE)

    for concurso in concursos:
        info = concurso.get_text(separator=' ', strip=True)

        datas = regex_data.findall(info)
        if not datas:
            continue
        data_fim = datetime.strptime(datas[-1], "%d/%m/%Y").date()
        if data_fim < hoje:
            continue

        if regex_excluir.search(info):
            continue

        if palavra and palavra.lower() not in info.lower():
            continue

        uf_match = regex_uf.search(info)
        uf_concurso = uf_match.group(1) if uf_match else "Nacional/Outro"
        if uf and uf != "Todos" and uf != uf_concurso:
            continue

        sal_match = regex_salario.search(info)
        if not sal_match:
            continue
        salario_float = float(sal_match.group(1).replace(".", "").replace(",", "."))
        if salario_float < salario_min:
            continue

        concursos_filtrados.append({
            "data_fim": data_fim.strftime("%d/%m/%Y"),
            "uf": uf_concurso,
            "salario": f"R$ {salario_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "info": info
        })

    return concursos_filtrados

@app.route('/', methods=['GET', 'POST'])
def index():
    concursos_filtrados = []
    if request.method == 'POST':
        salario_min = int(request.form.get('salario', 0))
        palavra = request.form.get('palavra', '').strip()
        uf = request.form.get('uf', '')
        palavras_excluir = request.form.get('excluir', '').split(',')
        palavras_excluir = [p.strip() for p in palavras_excluir if p.strip()]

        concursos_html = buscar_concursos()
        concursos_filtrados = filtrar_concursos(concursos_html, salario_min, palavra, uf, palavras_excluir)

    return render_template('index.html', concursos=concursos_filtrados)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

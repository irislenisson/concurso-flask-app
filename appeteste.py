from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    concursos_filtrados = []

    if request.method == 'POST':
        url = "https://www.pciconcursos.com.br/concursos/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        blocos = soup.find_all('div', class_='ca')
        print(f"\n⚠️ Encontrados {len(blocos)} blocos com class='ca'\n")

        for bloco in blocos:
            texto = bloco.get_text(strip=True, separator=' ')

            # Captura salário
            salario_match = re.search(r"R\$\s?([\d\.]+,\d{2})", texto)
            salario = float(salario_match.group(1).replace('.', '').replace(',', '.')) if salario_match else 0.0

            # Captura data
            data_match = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
            data_fim = data_match.group(1) if data_match else 'N/A'

            concursos_filtrados.append({
                'info': texto,
                'salario': f"R$ {salario:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','),
                'data_fim': data_fim,
                'uf': 'N/A'  # UF não extraída nesta versão
            })

    return render_template('index.html', concursos=concursos_filtrados)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

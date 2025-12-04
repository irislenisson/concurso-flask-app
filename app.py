from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import locale

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
UFS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
       'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
       'SP', 'SE', 'TO']

# =====================
# 🔎 Função de scraping
# =====================
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

# ============================
# 🎯 Filtragem personalizada
# ============================
def filtrar_concursos(concursos, salario_min, palavra, uf, excluir):
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        locale.setlocale(locale.LC_ALL, '')

    hoje = datetime.now().date()
    resultados = []

    regex_data = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
    regex_salario = re.compile(r'R\$[\s]*([\d\.]+,\d{2})')
    regex_uf = re.compile(r'\b(' + '|'.join(UFS) + r')\b', re.IGNORECASE)
    regex_excluir = re.compile(r'\b(' + '|'.join(map(re.escape, excluir)) + r')\b', re.IGNORECASE) if excluir else None

    for item in concursos:
        texto = item.get_text(separator=' ', strip=True)

        # Palavras-chave a incluir
        if palavra and palavra.lower() not in texto.lower():
            continue

        # Palavras a excluir
        if regex_excluir and regex_excluir.search(texto):
            continue

        # Data de fim de inscrição
        datas = regex_data.findall(texto)
        if not datas:
            continue
        try:
            data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
            if data_fim < hoje:
                continue
        except:
            continue

        # Salário mínimo
        salario_match = regex_salario.search(texto)
        if not salario_match:
            continue
        try:
            salario_float = float(salario_match.group(1).replace('.', '').replace(',', '.'))
            if salario_float < salario_min:
                continue
        except:
            continue

        # UF
        uf_match = regex_uf.search(texto)
        uf_detectada = uf_match.group(1) if uf_match else 'N/A'
        if uf != 'Todas' and uf != uf_detectada:
            continue

        resultados.append({
            'salario': locale.currency(salario_float, grouping=True),
            'uf': uf_detectada,
            'data_fim': data_fim.strftime('%d/%m/%Y'),
            'info': texto
        })

    return sorted(resultados, key=lambda x: x['salario'], reverse=True)

# ========================
# 🌐 Rota principal do app
# ========================
@app.route('/', methods=['GET', 'POST'])
def index():
    concursos_filtrados = []

    if request.method == 'POST':
        salario_min = float(request.form.get('salario_min') or 0)
        palavra = request.form.get('palavra') or ''
        uf = request.form.get('uf') or 'Todas'
        excluir_raw = request.form.get('excluir') or ''
        palavras_excluir = [p.strip() for p in excluir_raw.split(',') if p.strip()]

        concursos_html = buscar_concursos()
        concursos_filtrados = filtrar_concursos(concursos_html, salario_min, palavra, uf, palavras_excluir)

    return render_template('index.html', concursos=concursos_filtrados, ufs=UFS)

# ===================
# 🚀 Execução local
# ===================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

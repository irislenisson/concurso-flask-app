from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = Flask(__name__)

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'
UFS = [
    'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
    'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
]

def buscar_concursos(salario_minimo: float, palavras_incluir: list, palavras_excluir: list, uf_filtro: str):
    resultados = []
    try:
        resp = requests.get(URL_BASE, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        resp.raise_for_status()
    except Exception as e:
        print("❌ Erro ao acessar PCI Concursos:", e)
        return [], f"Erro ao acessar site de concursos: {e}"

    html = resp.text
    # DEBUG: ver os primeiros 2000 caracteres (ajuste se quiser)
    print("===== HTML capturado (início) =====")
    print(html[:2000])
    print("===================================")

    soup = BeautifulSoup(html, 'html.parser')
    blocos = soup.find_all('div', class_='ca')
    print(f"🔎 Total de blocos encontrados: {len(blocos)}")

    hoje = datetime.now().date()

    for bloco in blocos:
        info = bloco.get_text(separator=' ', strip=True)

        # Data final de inscrição
        datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', info)
        if not datas:
            continue
        try:
            data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
            if data_fim < hoje:
                continue
        except:
            continue

        # Salário
        sal_match = re.search(r'R\$[\s]*([\d\.]+,\d{2})', info)
        if not sal_match:
            continue
        try:
            sal = float(sal_match.group(1).replace('.', '').replace(',', '.'))
        except:
            continue
        if sal < salario_minimo:
            continue

        # UF
        uf = None
        for candidate in UFS:
            if f" {candidate} " in f" {info} ":
                uf = candidate
                break
        if uf_filtro and uf_filtro != "" and uf_filtro != uf:
            continue

        # Incluir / Excluir palavras
        lower = info.lower()
        if palavras_excluir:
            if any(p.lower() in lower for p in palavras_excluir):
                continue
        if palavras_incluir:
            if not all(p.lower() in lower for p in palavras_incluir):
                continue

        resultados.append({
            'Salário': f"R$ {sal:,.2f}".replace('.', ','),
            'UF': uf if uf else '',
            'Data Fim Inscrição': data_fim.strftime('%d/%m/%Y'),
            'Informações do Concurso': info
        })

    return resultados, None

@app.route('/', methods=['GET', 'POST'])
def index():
    concursos = []
    erro = None
    # valores padrão do formulário
    salario_minimo = 0.0
    palavras_incluir = []
    palavras_excluir = []
    uf_filtro = ""

    if request.method == 'POST':
        try:
            salario_minimo = float(request.form.get('salario_minimo') or 0)
        except:
            salario_minimo = 0.0
        incluir_raw = request.form.get('palavra_incluir', '').strip()
        if incluir_raw:
            palavras_incluir = [p.strip() for p in incluir_raw.split()]
        excluir_raw = request.form.get('palavra_excluir', '').strip()
        if excluir_raw:
            palavras_excluir = [p.strip() for p in excluir_raw.split()]
        uf_filtro = request.form.get('uf', '').strip().upper()

        resultados, err = buscar_concursos(salario_minimo, palavras_incluir, palavras_excluir, uf_filtro)
        if err:
            erro = err
        else:
            concursos = resultados

    return render_template('index.html', concursos=concursos, erro=erro, ufs=UFS)

if __name__ == '__main__':
    app.run(debug=True)

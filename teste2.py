def buscar_concursos(salario_min, palavra, excluir, uf):
    import re
    from bs4 import BeautifulSoup

    concursos = []
    # Já que você salvou HTML localmente em 'saida.html', leia dele
    with open('saida.html', 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')

    # Vamos imprimir quantos blocos encontramos
    blocos = soup.find_all('div', class_='ca')  # <-- ajuste conforme classe real
    print(f"DEBUG: achei {len(blocos)} blocos com class 'ca'")

    for bloco in blocos:
        texto = bloco.get_text(separator=" ", strip=True)
        # DEBUG: imprimir os primeiros 200 chars pra ver o conteúdo
        print("DEBUG bloco:", texto[:200])

        # Exemplo: extrair salário com regex flexível
        m_sal = re.search(r'R\$[\s]*([\d\.\d\,]+)', texto)
        if not m_sal:
            # se não achar salário, pule (ou continue, dependendo do critério)
            continue
        raw = m_sal.group(1)
        # converter para float: remover pontos de milhar, trocar vírgula por ponto
        try:
            salario = float(raw.replace('.', '').replace(',', '.'))
        except:
            continue

        # Filtragens (mínimo, palavra, excluir, UF) — similares ao seu código
        # ...

        concursos.append({'salario': salario,
                          'texto': texto})
    return concursos

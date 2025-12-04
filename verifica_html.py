from bs4 import BeautifulSoup

with open("saida.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Tenta encontrar qualquer DIV com classe 'ca' (ou o que tiver no HTML do PCI)
blocos = soup.find_all("div", class_="ca")

print(f"\n⚠️ Encontrados {len(blocos)} blocos com class='ca'\n")

# Se encontrou, exibe o início do primeiro
if blocos:
    print("Exemplo de bloco:\n")
    print(blocos[0].get_text(separator=" ", strip=True)[:500])
else:
    print("❌ Nenhum bloco com class='ca' foi encontrado.")

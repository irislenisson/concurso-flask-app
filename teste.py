import requests
from bs4 import BeautifulSoup

url = 'https://www.pciconcursos.com.br/concursos/'  # ou a URL correta
resp = requests.get(url, timeout=15)
html = resp.text

with open('saida.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Tamanho da página:", len(html))

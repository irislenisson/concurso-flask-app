import re
import os
import locale
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=basedir, static_folder=basedir)
CORS(app)

UFS_SIGLAS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

REGIOES = {
    'Norte': ['AM', 'RR', 'AP', 'PA', 'TO', 'RO', 'AC'],
    'Nordeste': ['MA', 'PI', 'CE', 'RN', 'PE', 'PB', 'SE', 'AL', 'BA'],
    'Centro-Oeste': ['MT', 'MS', 'GO', 'DF'],
    'Sudeste': ['SP', 'RJ', 'ES', 'MG'],
    'Sul': ['PR', 'RS', 'SC'],
}

# NOVA LISTA DE PRIORIDADE PARA INSCRIÇÃO
# Termos que identificam as bancas na URL ou no Texto
BANCAS_ALVO = [
    'ibade', 'objetiva', 'cespe', 'cebraspe', 'ibam', 'fgv', 'vunesp', 'ibfc',
    'idecan', 'institutomais', 'consulpam', 'aocp', 'selecon', 'fcc', 'consulplan',
    'ibgp', 'rbo', 'igeduc', 'fundep', 'fafipa', 'ufrj', 'pr4', 'pr-4',
    'avalias', 'quadrix', 'legalle', 'fundatec', 'nossorumo', 'fcc', 'amigapublica', 'access'
    '2dn', 'OMNI OMNI Concursos Públicos', 'FACET Concursos', 
    'FUNDATEC Fundação Universidade-Empresa de Tecnologia e Ciências',
    'Instituto Consulplan', 'Projetos e Assistência Social',
    'CESGRANRIO Fundação Cesgranrio','Quadrix',
    'SEPROD Serviço de Processamento de Dados','SHDIAS Consultoria e Assessoria',
    'IDIB Instituto de Desenvolvimento Institucional Brasileiro',
    'CONSESP Consultoria em Concursos e Pesquisas Sociais Ltda','EPL Empresa Paranaense de Licitações e Concursos',
    'Itame Itame Consultoria e Concursos','FUNATEC FUNATEC | Fundação de Apoio Tecnológico - Piauí (PI)',
    'IGECS Instituto de Gestão de Cidades','CEFET-BA Fundação CEFET - Bahia','PUBLICONSULT Publiconsult Assessoria e Consultoria Pública Ltda',
    'Instituto IBDO Projetos Instituto IBDO Projetos','INDEPAC Instituto de Cultura, Desenvolvimento Educacional, Promoção Humana e Ação Comunitária',
    'Instituto Access Instituto de Acesso à Educação, Capacitação Profissional e Desenvolvimento Humano',
    'OMNI Concursos Públicos','FACET Concursos','Fundação Universidade-Empresa de Tecnologia e Ciências',
    'Instituto Consulplan de Desenvolvimento, Projetos e Assistência Social','Fundação Cesgranrio',
    'Instituto Quadrix de Responsabilidade Social','Serviço de Processamento de Dados',
    'SHDIAS Consultoria e Assessoria',
    'Instituto de Desenvolvimento Institucional Brasileiro',
    'Consultoria em Concursos e Pesquisas Sociais Ltda','Empresa Paranaense de Licitações e Concursos',
    'Itame Consultoria e Concursos',
    'FUNATEC | Fundação de Apoio Tecnológico - Piauí (PI)',
    'Instituto de Gestão de Cidades','Fundação CEFET - Bahia',
    'Publiconsult Assessoria e Consultoria Pública Ltda',    'Instituto IBDO Projetos',
    'Instituto de Cultura, Desenvolvimento Educacional, Promoção Humana e Ação Comunitária',
    'Instituto de Acesso à Educação, Capacitação Profissional e Desenvolvimento Humano',
    'MS Concursos',    'FUVEST Fundação Universitária para o Vestibular',
    'CONCEPÇÃO - Consultoria Técnica Especializada LTDA',
    'Fundação La Salle', 'Centro de Treinamento e Desenvolvimento',
    'Fundação Professor Carlos Antonio Bittencourt',
    'Instituto Avalia de Inovação em Avaliação e Seleção',
    'Fundação de Apoio a Educação e Desenvolvimento Tecnológico',
    'Coordenadoria Geral de Concursos e Processos Seletivos (COGEPS) da Universidade Estadual do Oeste do Paraná',
    'Fundação de Estudos e Pesquisas Sócio Econômicos', 'Instituto Avança São Paulo',
    'Instituto UniFil','Instituto de Educação e Desenvolvimento Social',
    'ADVISE Consultoria', 'Instituto Mineiro de Administração Municipal',
    'Instituto de Apoio à Universidade de Pernambuco - UPE',
    'Fundação de Apoio à Pesquisa, ao Ensino e à Cultura',
    'Instituto de Capacitação, Assessoria e Pesquisa', 'Universidade Patativa de Assaré',
    'Fundação de Apoio à Universidade Estadual de Londrina',
    'Instituto Americano de Desenvolvimento',
    'KLC - Consultoria em Gestão Pública Ltda.',
    'Instituto Legatus',
    'Instituto Brasileiro de Incentivo ao Desenvolvimento Organizacional Eireli',
    'Núcleo de Concursos e Promoção de Eventos - UESPI',
    'Comissão Permanente de Concursos da Universidade Federal do Amazonas (COMPEC)',
    'Fundação de Apoio ao Desenvolvimento UNICENTRO',
    'Fundação Aroeira',
    'Instituto de Estudos Superiores do Extremo Sul',
    'Núcleo de Concursos da Universidade Federal do Paraná',
    'EDUCA PB - Instituto Assessoria',
    'Fundação de Apoio ao Desenvolvimento Científico e Tecnológico',
    'Comissão Permanente de Concursos da Universidade Estadual da Paraíba (UEPB)',
    'Instituto ADM&TEC',
    'Instituto Municipal de Desenvolvimento de Recursos Humanos de Fortaleza - Ceará',
    'Fundação de Apoio à Educação e ao Desenvolvimento Tecnológico do Rio Grande do Norte',
    'Marinha do Brasil',
    'Instituto Verbena - Universidade Federal de Goiás',
    'Universidade Estadual do Ceará - Comissão Executiva do Vestibular',
    'Fundação Sousândrade Concursos Públicos',
    'Fundação Mariana Resende Costa',
    'Creative Group', 'Legalle Concursos', 'SIGMA RH',
    'Coordenadoria de Processos Seletivos da Universidade Estadual de Londrina',
    'CONSCAM', 'FUNECE', 'Instituto Vicente Nelson','Fundação Universidade Regional de Blumenau',
    'CETAP - Centro de Extensão, Treinamento e Aperfeiçoamento Profissional',
    'GS Assessoria e Concursos',
    'Instituto de Desenvolvimento e Capacitação',
    'Master Consultoria Educacional',
    'Assessoria e Gestão Integrada em Recursos Humanos',
    'Força Aérea Brasileira (FAB)',
    'Universidade de Rio Verde - Goiás',
    'PROMUN - Projetos para Municípios',
    'Universidade Federal do Maranhão',
    'Associação dos Municípios do Alto Uruguai Catarinense',
    'Instituto de Desenvolvimento Humano e Tecnológico',
    'WE DO Serviços Inteligentes',
    'Concursos Técnicos', 'Desenvolvimento Educacional e Social',
    'Fênix Concursos - São Paulo',
    'Instituto Assistencial de Desenvolvimento Humano, Educacional e Desportivo',
    'Universidade do Estado da Bahia',
    'Fundação de Amparo e Desenvolvimento da Pesquisa',
    'Universidade Federal do Acre',
    'Universidade Federal de Pernambuco',
    'Banca Não Definida',
    'CETRO Concursos',
    'Universidade do Sul de Santa Catarina',
    'Planexcon - Assessoria e Consultoria Pública',
    'Associação Municipal do Extremo Oeste de Santa Catarina',
    'Escola de Administração Fazendária',
    'Dédalus Concursos & Treinamentos',
    'Instituto Excelência',
    'Centro de Integração Empresa-Escola',
    'Núcleo de Concursos da Universidade Federal do Paraná', 
    'UFMT','CEV - Coordenação de Concursos e Exames Vestibulares da UFMT',
    'ACCESS','ACCESS Seleção',
    'FUNRIO','Fundação de Apoio a Pesquisa, Ensino e Assistência',
    'COMPERVE - UFRN','Núcleo Permanente de Concursos da Universidade Federal do Rio Grande do Norte',
    'Direcao','Direção Concursos',
    'Fenaz do Pará','Fenaz do Pará',
    'Ibest','Instituto Brasileiro de Educação, Seleção e Tecnologia',
    'ABCP','Associação Brasileira de Concursos Públicos',
    'FCM','Fundação CEFETMINAS',
    'AEVSF/FACAPE','Faculdade de Ciências Aplicadas e Sociais de Petrolina',
    'UERR','Universidade Estadual de Roraima',
    'Exército','Exército Brasileiro',
    'COPEVE-UFAL','Núcleo Executivo de Processos Seletivos da UFAL',
    'CEV-URCA','Comissão Executiva do Vestibular - Universidade Regional do Cariri',
    'FUNIVERSA','Fundação Universa',
    'IASP','Instituto IASP',
    'SIPROS','Sistema Integrado de Processo Seletivo Simplificado',
    'Método Soluções Educacionais','Método Soluções Educacionais',
    'USP','Universidade de São Paulo',
    'FAEPESUL','Fundação de Apoio à Educação, Pesquisa e Extensão da Unisul',
    'PGR - Procuradoria Geral da República', 'UFU-MG - Universidade Federal de Uberlândia - MG', 
    'CONESUL - Fundação CONESUL de Desenvolvimento', 
    'CAIP-IMES - USCS', 'Fundação CETREDE', 'EJUD-PI - Escola Judiciária do Piauí', 
    'IAN - Instituto de Avaliação Nacional', 
    'GSA CONCURSOS - Consultoria e Pesquisas em Instituições Públicas S/C Ltda', 
    'CMM - Concursos e Seletivos - Assessoria e Consultoria em Gestão Pública', 
    'UFRGS - Universidade Federal do Rio Grande do Sul', 
    'IPEFAE - Instituto de Pesquisas Econômicas', 
    'IUDS - Instituto Universal de Desenvolvimento Social', 
    'COVEST-COPSET - COVEST-COPSET - Comissão de Processos Seletivos e Treinamentos (UFPE)', 
    'ACEP - Associação Cearense de Estudos e Pesquisas', 
    'FEC - Fundação Euclides da Cunha - UFF', 
    'CONSULTEC - Consultec - Consultoria em Projetos Educacionais e Concursos Ltda', 
    'NCE-UFRJ', 'FADE - UFPE', 'PS Concursos - AIR Soluções em Pesquisa e Tecnologia', 
    'UEPB - Universidade Estadual da Paraíba', 'MS Consultoria - MS Consultoria', 
    'Prefeitura de Bertioga - SP - Prefeitura Municipal de Bertioga - São Paulo', 
    'UNESP - Universidade Estadual Paulista Júlio de Mesquita Filho', 
    'PGE-PA - Procuradoria Geral do Estado do Pará', 
    'SPDM - Associação Paulista para o Desenvolvimento da Medicina', 
    'GUALIMP - GUALIMP Assessoria e Consultoria Ltda', 
    'MPE-BA - Ministério Público do Estado da Bahia', 
    'FAPEMS - Fundação de Apoio à Pesquisa, ao Ensino e à Cultura de Mato Grosso do Sul', 
    'CEFET-MG - Centro Federal de Educação Tecnológica de Minas Gerais', 
    'SEAP - Seap Consultoria e Concursos Públicos', 'PONTUA - Pontua Concursos', 
    'MPE-PR - Ministério Público do Estado do Paraná', 'MPT - Ministério Público do Trabalho', 
    'CFC - Conselho Federal de Contabilidade', 'CEPERJ', 
    'UESPI - Universidade Estadual do Piauí', 'EJEF - Escola Judicial Desembargador Edésio Fernandes', 
    'CEPS-UFPA - Centro de Processos Seletivos da Universidade Federal do Pará', 
    'INSTITUTO PRÓ-MUNICÍPIO', 'INSTITUTO CIDADES', 'MARANATHA', 'TJ-AP', 
    'LJ Assessoria e Planejamento Administrativo Limita', 'Cepros - Comissão Executiva de Processo Seletivo',
    'NEMESIS - NEMESIS', 'Prefeitura de Anchieta - ES', 'FCPC ', 'IDESUL', 'FUCAP', 'AJURI', 'GANZAROLI',
    'Prefeitura de Rondonópolis', 'ACTIO ASSESSORIA', 'MetroCapital Soluções', 'IF Sul Rio-Grandense ', 
    'UFRPE - Universidade Federal Rural de Pernambuco', 
    'UFSC - Universidade Federal de Santa Catarina', 
    'Planejar Consultoria ', 'UFV - Universidade Federal de Viçosa', 
    'SIGMA ASSESSORIA'






]

URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

def buscar_concursos():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        print("--> Baixando dados da lista...")
        resp = requests.get(URL_BASE, timeout=30, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.find_all('div', class_='ca')
    except Exception as e:
        print(f"--> ERRO: {e}")
        return []

def formatar_real(valor):
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def filtrar_concursos(concursos, salario_min, lista_palavras_chave, lista_ufs_alvo, excluir_palavras):
    hoje = datetime.now().date()
    resultados = []
    modo_restritivo = len(lista_ufs_alvo) > 0

    for c in concursos:
        texto = c.get_text(separator=' ', strip=True)
        texto_lower = texto.lower()
        
        link_original = "#"
        try:
            tag_link = c.find('a')
            if tag_link and 'href' in tag_link.attrs:
                link_original = tag_link['href']
        except: pass

        datas = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
        data_formatada = "Indefinida"
        if datas:
            try:
                data_fim = datetime.strptime(datas[-1], '%d/%m/%Y').date()
                if data_fim < hoje: continue 
                data_formatada = data_fim.strftime('%d/%m/%Y')
            except: pass 

        if excluir_palavras and any(ex.lower() in texto_lower for ex in excluir_palavras): 
            continue

        if lista_palavras_chave:
            encontrou_alguma = any(chave.lower() in texto_lower for chave in lista_palavras_chave)
            if not encontrou_alguma:
                continue

        salario = 0.0
        m = re.search(r'R\$\s*([\d\.]+,\d{2})', texto)
        if m:
            try:
                salario = float(m.group(1).replace('.', '').replace(',', '.'))
            except: salario = 0.0
        
        if salario_min > 0 and salario < salario_min: continue

        uf_detectada = 'Nacional/Outro'
        for sigla in UFS_SIGLAS:
            if re.search(r'\b' + re.escape(sigla) + r'\b', texto):
                uf_detectada = sigla
                break
        
        if modo_restritivo:
            if uf_detectada not in lista_ufs_alvo:
                continue

        resultados.append({
            'Salário': formatar_real(salario) if salario > 0 else "Ver Edital/Variável",
            'UF': uf_detectada,
            'Data Fim Inscrição': data_formatada,
            'Informações do Concurso': texto,
            'Link': link_original,
            'raw_salario': salario
        })

    resultados.sort(key=lambda x: x['raw_salario'], reverse=True)
    for r in resultados: del r['raw_salario']

    return resultados

# --- FUNÇÃO APRIMORADA COM BUSCA POR BANCAS ---
def extrair_link_final(url_base, tipo):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url_base, timeout=10, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        todos_links = soup.find_all('a', href=True)
        
        candidato_melhor = None

        if tipo == 'edital':
            # Lógica de Edital (Prioriza PDF)
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                if 'edital' in text or 'abertura' in text or href.endswith('.pdf'):
                    if 'facebook' not in href and 'twitter' not in href:
                        candidato_melhor = a['href']
                        if href.endswith('.pdf'): break # PDF é ouro
                            
        elif tipo == 'inscricao':
            # --- FASE 1: Busca na Lista de Bancas (Prioridade Máxima) ---
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                
                # Verifica se alguma banca da lista está na URL ou no Texto do link
                for banca in BANCAS_ALVO:
                    if banca in href or banca in text:
                        # Filtros de segurança para não pegar notícias sobre a banca
                        if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                            return a['href'] # Achou a banca oficial? Retorna na hora!

            # --- FASE 2: Busca Genérica (Se não achou banca conhecida) ---
            for a in todos_links:
                href = a['href'].lower()
                text = a.get_text().lower()
                
                # Palavras fortes de inscrição
                termos_fortes = ['inscriç', 'inscreva', 'ficha', 'candidato', 'eletrônico', 'formulário']
                
                if any(t in text for t in termos_fortes):
                    if 'pciconcursos' not in href and 'facebook' not in href and '.pdf' not in href:
                        candidato_melhor = a['href']
                        break

        return candidato_melhor if candidato_melhor else url_base

    except Exception as e:
        print(f"Erro deep link: {e}")
        return url_base

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/link-profundo', methods=['POST'])
def api_link_profundo():
    data = request.json or {}
    url_concurso = data.get('url', '')
    tipo = data.get('tipo', 'edital')
    
    if not url_concurso or url_concurso == '#':
        return jsonify({'url': '#'})

    url_final = extrair_link_final(url_concurso, tipo)
    return jsonify({'url': url_final})

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    data = request.json or {}
    
    try:
        s_raw = str(data.get('salario_minimo', ''))
        s_clean = re.sub(r'[^\d,]', '', s_raw)
        s_clean = s_clean.replace(',', '.')
        salario_minimo = float(s_clean) if s_clean else 0.0
    except: salario_minimo = 0.0

    palavra_chave_raw = data.get('palavra_chave', '')
    lista_palavras_chave = [p.strip() for p in palavra_chave_raw.split(',') if p.strip()]

    excluir_str = data.get('excluir_palavra', '')
    excluir_palavras = [p.strip() for p in excluir_str.split(',') if p.strip()]

    ufs_selecionadas = data.get('ufs', []) 
    regioes_selecionadas = data.get('regioes', []) 

    conjunto_ufs_alvo = set(ufs_selecionadas)
    for reg in regioes_selecionadas:
        if reg == 'Nacional':
            conjunto_ufs_alvo.add('Nacional/Outro')
        elif reg in REGIOES:
            conjunto_ufs_alvo.update(REGIOES[reg])
    
    lista_final_ufs = list(conjunto_ufs_alvo)
    
    todos = buscar_concursos()
    resultados = filtrar_concursos(todos, salario_minimo, lista_palavras_chave, lista_final_ufs, excluir_palavras)
    
    return jsonify(resultados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
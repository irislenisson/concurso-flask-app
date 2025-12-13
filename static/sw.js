let todosConcursos = [];
let paginaAtual = 0;
const itensPorPagina = 20;

function getFavoritos() {
    const salvos = localStorage.getItem('concursosFavoritos');
    return salvos ? JSON.parse(salvos) : [];
}
function isFavorito(texto) { return getFavoritos().some(f => f.texto === texto); }
function toggleFavorito(texto, link, salario, uf, dataFim, btnElement) {
    let favs = getFavoritos();
    const index = favs.findIndex(f => f.texto === texto);
    if (index > -1) { favs.splice(index, 1); if(btnElement) btnElement.classList.remove('favorited'); }
    else { favs.push({ texto, link, salario, uf, dataFim }); if(btnElement) btnElement.classList.add('favorited'); }
    localStorage.setItem('concursosFavoritos', JSON.stringify(favs));
    if (document.getElementById('favorites-view').style.display === 'block') renderizarMeusFavoritos();
}

function toggleTelaFavoritos() {
    const mainView = document.getElementById('main-view');
    const favView = document.getElementById('favorites-view');
    if (favView.style.display === 'none' || favView.style.display === '') {
        mainView.style.display = 'none'; favView.style.display = 'block'; renderizarMeusFavoritos();
    } else { favView.style.display = 'none'; mainView.style.display = 'block'; }
}

function renderizarMeusFavoritos() {
    const container = document.getElementById('favorites-list-container');
    const favs = getFavoritos();
    container.innerHTML = '';
    if (favs.length === 0) { container.innerHTML = '<div style="text-align:center; padding:40px; color:#666;">Nenhum favorito salvo.</div>'; return; }
    favs.forEach(c => container.appendChild(criarHTMLCard(c, true)));
}

function criarHTMLCard(c, isFavPage = false) {
    const div = document.createElement('div');
    div.className = 'concurso-card';
    const linkBase = (c.link || c['Link'] || '#').replace(/'/g, "%27");
    const texto = (c.texto || c['Informações do Concurso']).replace(/'/g, "\\'");
    const salario = c.salario || c['Salário'];
    const uf = c.uf || c['UF'];
    const dataFim = c.dataFim || c['Data Fim Inscrição'];
    const classeFav = (isFavPage || isFavorito(c.texto || c['Informações do Concurso'])) ? 'favorited' : '';
    
    div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:start;">
            <h3 style="flex:1; margin-right:10px;">${c.texto || c['Informações do Concurso']}</h3>
            <button class="btn-fav-card ${classeFav}" onclick="toggleFavorito('${texto}', '${linkBase}', '${salario}', '${uf}', '${dataFim}', this)">❤️</button>
        </div>
        <div class="meta-line">
            <span class="badge money">💰 ${salario}</span>
            <span class="badge uf">📍 ${uf}</span>
            <span class="badge date">📅 ${dataFim}</span>
            <a href="/ir?url=${encodeURIComponent(linkBase)}&tipo=edital" target="_blank" class="action-btn btn-edital">📄 Edital</a>
            <a href="/ir?url=${encodeURIComponent(linkBase)}&tipo=inscricao" target="_blank" class="action-btn btn-inscricao">✍️ Inscrição</a>
        </div>
        <div style="text-align: right; margin-top:10px;">
            <button class="btn-report" onclick="reportarErro('${texto}')">🚩 Reportar</button>
        </div>
    `;
    return div;
}

function formatarMoeda(el) {
    let v = el.value.replace(/\D/g, "");
    v = (v/100).toFixed(2) + "";
    el.value = "R$ " + v.replace(".", ",").replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
}

// LISTENERS DOS BOTÕES
document.querySelectorAll('.uf-btn, .region-btn, .level-btn').forEach(btn => {
    btn.addEventListener('click', () => { btn.classList.toggle('active'); });
});

function limparFiltros() {
    document.getElementById('searchForm').reset();
    document.querySelectorAll('.uf-btn, .region-btn, .filter-btn, .level-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('resultados-container').innerHTML = '';
    document.getElementById('btn-load-more').style.display = 'none';
    document.getElementById('status-msg').style.display = 'none';
    window.history.pushState({}, '', window.location.pathname);
}

// RENDERIZAÇÃO
function renderizarLote() {
    const container = document.getElementById('resultados-container');
    const btnLoadMore = document.getElementById('btn-load-more');
    const inicio = paginaAtual * itensPorPagina;
    const fim = inicio + itensPorPagina;
    const lote = todosConcursos.slice(inicio, fim);
    lote.forEach(c => container.appendChild(criarHTMLCard(c)));
    btnLoadMore.style.display = fim < todosConcursos.length ? 'block' : 'none';
    if(fim < todosConcursos.length) btnLoadMore.innerText = `👇 Carregar mais (${todosConcursos.length - fim})`;
}
function carregarMais() { paginaAtual++; renderizarLote(); }

// BUSCA
document.getElementById('searchForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const btnBuscar = document.getElementById('btn-buscar');
    const container = document.getElementById('resultados-container');
    const statusDiv = document.getElementById('status-msg');
    
    todosConcursos = []; paginaAtual = 0;
    container.innerHTML = '<div class="skeleton-card"><div class="skeleton skeleton-title"></div></div>'.repeat(3);
    btnBuscar.disabled = true;

    const ufs = Array.from(document.querySelectorAll('.uf-btn.active')).map(b => b.getAttribute('data-value'));
    const regs = Array.from(document.querySelectorAll('.region-btn.active')).map(b => b.getAttribute('data-value'));
    const nivs = Array.from(document.querySelectorAll('.level-btn.active')).map(b => b.getAttribute('data-value')); // Novos Níveis
    
    const payload = {
        salario_minimo: document.getElementById('salario_minimo').value,
        palavra_chave: document.getElementById('palavra_chave').value,
        excluir_palavra: document.getElementById('excluir_palavra').value,
        regioes: regs,
        ufs: ufs,
        niveis: nivs
    };

    try {
        const resp = await fetch('/api/buscar', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        todosConcursos = await resp.json();
        container.innerHTML = '';
        btnBuscar.disabled = false;
        
        if (todosConcursos.length === 0) {
            statusDiv.style.display = 'block'; statusDiv.className = 'empty'; statusDiv.innerText = 'Nenhum resultado encontrado.';
        } else {
            statusDiv.style.display = 'none';
            btnBuscar.value = `Encontramos ${todosConcursos.length} vagas!`;
            renderizarLote();
        }
    } catch (e) {
        container.innerHTML = ''; statusDiv.style.display = 'block'; statusDiv.className = 'error'; statusDiv.innerText = 'Erro ao buscar.';
        btnBuscar.disabled = false;
    }
});

// INIT
window.addEventListener('load', () => {
    // Carrega tema e cookies (simplificado)
    if(!localStorage.getItem("cookieConsent") && document.getElementById("cookie-banner")) document.getElementById("cookie-banner").style.display = "block";
});
async function compartilharNativo() {
    if (navigator.share) navigator.share({title:'Concurso Ideal', url:window.location.href});
    else { navigator.clipboard.writeText(window.location.href); alert("Link copiado!"); }
}
async function reportarErro(txt) { fetch('/api/reportar', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:txt})}); alert("Obrigado!"); }
async function cadastrarLead() { fetch('/api/newsletter', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('email-lead').value})}); alert("Cadastrado!"); }
function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
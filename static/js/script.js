/* static/js/script.js - Versão Final (Share Nativo + Report API + Tela Viva) */

let todosConcursos = [];
let paginaAtual = 0;
const itensPorPagina = 20;

// --- SISTEMA DE FAVORITOS (LOCALSTORAGE) ---
function getFavoritos() {
    const salvos = localStorage.getItem('concursosFavoritos');
    return salvos ? JSON.parse(salvos) : [];
}

function isFavorito(textoConcurso) {
    const favs = getFavoritos();
    return favs.some(f => f.texto === textoConcurso);
}

function toggleFavorito(texto, link, salario, uf, dataFim, btnElement) {
    let favs = getFavoritos();
    const index = favs.findIndex(f => f.texto === texto);

    if (index > -1) {
        favs.splice(index, 1);
        if(btnElement) btnElement.classList.remove('favorited');
    } else {
        favs.push({ texto, link, salario, uf, dataFim });
        if(btnElement) btnElement.classList.add('favorited');
    }
    localStorage.setItem('concursosFavoritos', JSON.stringify(favs));
    
    if (document.getElementById('favorites-view').style.display === 'block') {
        renderizarMeusFavoritos();
    }
}

function toggleTelaFavoritos() {
    const mainView = document.getElementById('main-view');
    const favView = document.getElementById('favorites-view');
    const btnGlobal = document.getElementById('btn-fav-global'); 
    
    if (favView.style.display === 'none' || favView.style.display === '') {
        mainView.style.display = 'none';
        favView.style.display = 'block';
        if(btnGlobal) btnGlobal.innerHTML = '🏠';
        renderizarMeusFavoritos();
    } else {
        favView.style.display = 'none';
        mainView.style.display = 'block';
        if(btnGlobal) btnGlobal.innerHTML = '❤️';
    }
}

function renderizarMeusFavoritos() {
    const container = document.getElementById('favorites-list-container');
    const favs = getFavoritos();
    container.innerHTML = '';
    if (favs.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:40px; color:#666;"><i class="fas fa-heart-broken" style="font-size:3em; margin-bottom:10px; opacity:0.3;"></i><br>Você ainda não salvou nenhum concurso.<br>Clique no ❤️ nos cards para salvar!</div>';
        return;
    }
    favs.forEach(c => {
        container.appendChild(criarHTMLCard(c, true));
    });
}

// Função Unificada para Criar Cards
function criarHTMLCard(c, isFavPage = false) {
    const div = document.createElement('div');
    div.className = 'concurso-card';
    
    const linkBase = (c.link || c['Link'] || '#').replace(/'/g, "%27");
    const textoConcurso = (c.texto || c['Informações do Concurso']).replace(/'/g, "\\'");
    const salario = c.salario || c['Salário'];
    const uf = c.uf || c['UF'];
    const dataFim = c.dataFim || c['Data Fim Inscrição'];
    const linkEdital = `/ir?url=${encodeURIComponent(linkBase)}&tipo=edital`;
    const linkInscricao = `/ir?url=${encodeURIComponent(linkBase)}&tipo=inscricao`;
    const classeFav = (isFavPage || isFavorito(c.texto || c['Informações do Concurso'])) ? 'favorited' : '';

    div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:start;">
            <h3 style="flex:1; margin-right:10px;">${c.texto || c['Informações do Concurso']}</h3>
            <button class="btn-fav-card ${classeFav}" onclick="toggleFavorito('${textoConcurso}', '${linkBase}', '${salario}', '${uf}', '${dataFim}', this)" title="Salvar/Remover vaga">❤️</button>
        </div>
        <div class="meta-line">
            <span class="badge money"><i class="fas fa-money-bill-wave"></i> ${salario}</span>
            <span class="badge uf"><i class="fas fa-map-marker-alt"></i> ${uf}</span>
            <span class="badge date"><i class="far fa-calendar-alt"></i> ${dataFim}</span>
            <button class="icon-btn btn-copy-small" onclick="copiarLinkUnico('${textoConcurso}')" title="Copiar link"><i class="fas fa-link"></i></button>
            <button class="icon-btn btn-zap-small" onclick="compartilharZapUnico('${textoConcurso}')" title="WhatsApp"><i class="fab fa-whatsapp"></i></button>
            <a href="${linkEdital}" target="_blank" rel="noopener noreferrer" class="action-btn btn-edital"><i class="fas fa-file-pdf"></i> Edital</a>
            <a href="${linkInscricao}" target="_blank" rel="noopener noreferrer" class="action-btn btn-inscricao">✍️ Inscrição</a>
        </div>
        <div style="text-align: right;">
            <button class="btn-report" onclick="reportarErro('${textoConcurso}')"><i class="fas fa-flag"></i> Reportar</button>
        </div>
    `;
    return div;
}

// --- UTILITÁRIOS GERAIS ---
function formatarMoeda(elemento) {
    let valor = elemento.value.replace(/\D/g, "");
    if (valor === "") { elemento.value = ""; return; }
    valor = (valor / 100).toFixed(2) + "";
    valor = valor.replace(".", ",");
    valor = valor.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
    elemento.value = "R$ " + valor;
}

document.querySelectorAll('.uf-btn, .region-btn').forEach(btn => {
    btn.addEventListener('click', () => { btn.classList.toggle('active'); });
});

function limparFiltros() {
    document.getElementById('searchForm').reset();
    document.querySelectorAll('.uf-btn, .region-btn, .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById('resultados-container').innerHTML = '';
    document.getElementById('btn-load-more').style.display = 'none';
    document.getElementById('status-msg').style.display = 'none';
    window.history.pushState({}, '', window.location.pathname);
    document.getElementById('searchForm').dispatchEvent(new Event('submit'));
}

// Theme & Init & Cookies
const themeCheckbox = document.getElementById('checkbox');
const htmlElement = document.documentElement;

document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.setAttribute('data-theme', savedTheme);
        if (savedTheme === 'dark' && themeCheckbox) themeCheckbox.checked = true;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        htmlElement.setAttribute('data-theme', 'dark');
        if (themeCheckbox) themeCheckbox.checked = true;
    }
    if (!localStorage.getItem("cookieConsent")) {
        const banner = document.getElementById("cookie-banner");
        if (banner) banner.style.display = "block";
    }
    const btnGlobal = document.getElementById('btn-fav-global');
    if(btnGlobal) btnGlobal.style.display = 'flex';
});

if (themeCheckbox) {
    themeCheckbox.addEventListener('change', function() {
        if (this.checked) {
            htmlElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            htmlElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
}

function aceitarCookies() {
    localStorage.setItem("cookieConsent", "true");
    document.getElementById("cookie-banner").style.display = "none";
}

window.onscroll = function() {
    const btn = document.getElementById("btn-back-to-top");
    if (btn) {
        if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) btn.style.display = "block";
        else btn.style.display = "none";
    }
};
function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }

// --- COMPARTILHAMENTO INTELIGENTE E REPORTAR API ---

async function compartilharNativo() {
    const dadosShare = {
        title: 'Concurso Ideal 🚀',
        text: 'Encontrei vagas de concursos incríveis! Dá uma olhada:',
        url: window.location.href
    };
    if (navigator.share) {
        try { await navigator.share(dadosShare); } 
        catch (err) { console.log(err); }
    } else {
        navigator.clipboard.writeText(window.location.href).then(() => { mostrarToast("Link copiado!"); });
    }
}

async function reportarErro(texto) {
    if(!confirm("Deseja reportar um erro neste concurso para a equipe?")) return;
    try {
        const response = await fetch('/api/reportar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto: texto })
        });
        if (response.ok) mostrarToast("Erro reportado. Obrigado!");
        else alert("Erro ao enviar reporte.");
    } catch (e) { alert("Erro de conexão."); }
}

function copiarLinkUnico(texto) {
    const urlBase = window.location.origin + window.location.pathname;
    const linkUnico = `${urlBase}?q=${encodeURIComponent(texto)}`;
    navigator.clipboard.writeText(linkUnico).then(() => { mostrarToast("Link copiado!"); });
}

function compartilharZapUnico(texto) {
    const urlBase = window.location.origin + window.location.pathname;
    const linkUnico = `${urlBase}?q=${encodeURIComponent(texto)}`;
    const mensagem = encodeURIComponent(`Olha esse concurso: ${texto}\n${linkUnico}`);
    window.open(`https://api.whatsapp.com/send?text=${mensagem}`, '_blank');
}

function mostrarToast(msg) {
    const toast = document.getElementById("toast");
    toast.innerText = msg;
    toast.className = "show";
    setTimeout(function(){ toast.className = toast.className.replace("show", ""); }, 3000);
}

// --- NEWSLETTER ---
async function cadastrarLead() {
    const emailInput = document.getElementById('email-lead');
    const email = emailInput.value;
    const btn = document.querySelector('.news-form button');
    if (!email || !email.includes('@')) { alert("E-mail inválido."); return; }

    const textoOriginal = btn.innerText;
    btn.innerText = "Enviando...";
    btn.disabled = true;

    try {
        const response = await fetch('/api/newsletter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        if (response.ok) {
            btn.innerText = "Cadastrado! ✅";
            emailInput.value = "";
            setTimeout(() => { btn.innerText = "Cadastrar"; btn.disabled = false; }, 3000);
        } else { throw new Error(); }
    } catch (e) {
        btn.innerText = "Erro ❌";
        setTimeout(() => { btn.innerText = textoOriginal; btn.disabled = false; }, 2000);
    }
}

// --- RENDERIZAÇÃO E BUSCA ---
function renderizarLote() {
    const container = document.getElementById('resultados-container');
    const btnLoadMore = document.getElementById('btn-load-more');
    const inicio = paginaAtual * itensPorPagina;
    const fim = inicio + itensPorPagina;
    const lote = todosConcursos.slice(inicio, fim);

    lote.forEach((c, index) => {
        const indiceAbsoluto = inicio + index;
        if (indiceAbsoluto > 0 && indiceAbsoluto % 5 === 0) {
            const adDiv = document.createElement('div');
            adDiv.className = 'ad-slot';
            adDiv.innerHTML = `<span class="ad-label">Publicidade</span><div style="background:var(--border-color); height:90px; display:flex; align-items:center; justify-content:center; border-radius:4px; opacity:0.7;">Espaço para Anúncio</div>`;
            container.appendChild(adDiv);
        }
        container.appendChild(criarHTMLCard(c));
    });

    if (fim < todosConcursos.length) {
        btnLoadMore.style.display = 'block';
        btnLoadMore.innerText = `👇 Carregar mais (${todosConcursos.length - fim})`;
    } else {
        btnLoadMore.style.display = 'none';
    }
}

function carregarMais() {
    paginaAtual++;
    renderizarLote();
}

// --- AUTO-CARREGAMENTO (TELA VIVA) ---
window.addEventListener('load', () => {
    const params = new URLSearchParams(window.location.search);
    let temFiltrosURL = false;
    if (params.has('q')) { document.getElementById('palavra_chave').value = params.get('q'); temFiltrosURL = true; }
    if (params.has('salario')) { document.getElementById('salario_minimo').value = params.get('salario'); temFiltrosURL = true; }
    if (params.has('excluir')) { document.getElementById('excluir_palavra').value = params.get('excluir'); temFiltrosURL = true; }
    if (params.has('uf')) {
        params.get('uf').split(',').forEach(uf => {
            const btn = document.querySelector(`.uf-btn[data-value="${uf}"]`);
            if (btn) btn.classList.add('active');
        });
        temFiltrosURL = true;
    }
    if (params.has('regiao')) {
        params.get('regiao').split(',').forEach(reg => {
            const btn = document.querySelector(`.region-btn[data-value="${reg}"]`);
            if (btn) btn.classList.add('active');
        });
        temFiltrosURL = true;
    }
    document.getElementById('searchForm').dispatchEvent(new Event('submit'));
});

document.getElementById('searchForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const btnBuscar = document.getElementById('btn-buscar');
    const statusDiv = document.getElementById('status-msg');
    const container = document.getElementById('resultados-container');
    const btnLoadMore = document.getElementById('btn-load-more');
    
    todosConcursos = [];
    paginaAtual = 0;
    btnLoadMore.style.display = 'none';
    container.innerHTML = '';
    statusDiv.style.display = 'none';
    
    let skeletonsHTML = '';
    for(let i=0; i<5; i++) {
        skeletonsHTML += `<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-title" style="width: 60%"></div><div style="margin-top: 20px;"><div class="skeleton skeleton-badge"></div></div></div>`;
    }
    container.innerHTML = skeletonsHTML;
    btnBuscar.disabled = true;

    const activeUfs = Array.from(document.querySelectorAll('.uf-btn.active')).map(btn => btn.getAttribute('data-value'));
    const activeRegions = Array.from(document.querySelectorAll('.region-btn.active')).map(btn => btn.getAttribute('data-value'));
    const salario = document.getElementById('salario_minimo').value;
    const palavraChave = document.getElementById('palavra_chave').value;
    const excluir = document.getElementById('excluir_palavra').value;

    const params = new URLSearchParams();
    if (palavraChave) params.set('q', palavraChave);
    if (salario) params.set('salario', salario);
    if (excluir) params.set('excluir', excluir);
    if (activeUfs.length > 0) params.set('uf', activeUfs.join(','));
    if (activeRegions.length > 0) params.set('regiao', activeRegions.join(','));
    
    if ([...params].length > 0) {
        window.history.pushState({}, '', window.location.pathname + '?' + params.toString());
    }

    const payload = { salario_minimo: salario, palavra_chave: palavraChave, excluir_palavra: excluir, regioes: activeRegions, ufs: activeUfs };

    try {
        const response = await fetch('/api/buscar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`Erro: ${response.status}`);
        todosConcursos = await response.json();
        btnBuscar.value = `Buscar Oportunidades (${todosConcursos.length})`;
        btnBuscar.disabled = false;
        container.innerHTML = '';

        if (todosConcursos.length === 0) {
            statusDiv.style.display = 'block';
            statusDiv.className = 'empty';
            statusDiv.innerHTML = `❌ Não foi possível encontrar concursos com esses filtros.<br>Tente ajustar os filtros ou palavras-chave e buscar novamente.`;
            return;
        }
        renderizarLote();
    } catch (error) {
        console.error(error);
        container.innerHTML = '';
        statusDiv.style.display = 'block';
        statusDiv.className = 'error';
        statusDiv.innerHTML = `❌ Erro de conexão ou instabilidade no servidor. Tente novamente em instantes.`;
        btnBuscar.value = "Buscar Oportunidades";
        btnBuscar.disabled = false;
    }
});
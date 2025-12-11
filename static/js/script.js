/* static/js/script.js */

let todosConcursos = [];
let paginaAtual = 0;
const itensPorPagina = 30;

function formatarMoeda(elemento) {
    let valor = elemento.value.replace(/\D/g, "");
    if (valor === "") { elemento.value = ""; return; }
    valor = (valor / 100).toFixed(2) + "";
    valor = valor.replace(".", ",");
    valor = valor.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
    elemento.value = "R$ " + valor;
}

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => { btn.classList.toggle('active'); });
});

// BOTÃO VOLTAR AO TOPO
window.onscroll = function() {
    const btn = document.getElementById("btn-back-to-top");
    if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) btn.style.display = "block";
    else btn.style.display = "none";
};
function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }

// --- FUNÇÕES DE COMPARTILHAMENTO ---
function copiarLink() {
    navigator.clipboard.writeText(window.location.href).then(() => {
        const toast = document.getElementById("toast");
        toast.innerText = "Link da busca copiado!";
        toast.className = "show";
        setTimeout(function(){ toast.className = toast.className.replace("show", ""); }, 3000);
    });
}

function compartilharWhatsApp() {
    const url = encodeURIComponent(window.location.href);
    const text = encodeURIComponent("Olha esses concursos que encontrei:");
    window.open(`https://api.whatsapp.com/send?text=${text}%20${url}`, '_blank');
}

// COMPARTILHAMENTO DE CONCURSO ÚNICO (DENTRO DO CARD)
function copiarLinkUnico(texto) {
    const urlBase = window.location.origin + window.location.pathname;
    const linkUnico = `${urlBase}?q=${encodeURIComponent(texto)}`;
    navigator.clipboard.writeText(linkUnico).then(() => {
        const toast = document.getElementById("toast");
        toast.innerText = "Link deste concurso copiado!";
        toast.className = "show";
        setTimeout(function(){ toast.className = toast.className.replace("show", ""); }, 3000);
    });
}

function compartilharZapUnico(texto) {
    const urlBase = window.location.origin + window.location.pathname;
    const linkUnico = `${urlBase}?q=${encodeURIComponent(texto)}`;
    const mensagem = encodeURIComponent(`Olha esse concurso: ${texto}\n${linkUnico}`);
    window.open(`https://api.whatsapp.com/send?text=${mensagem}`, '_blank');
}

async function clicarAcao(el, urlBase, tipo) {
    const textoOriginal = el.innerHTML;
    el.classList.add('disabled');
    el.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> ${tipo === 'edital' ? 'Buscando PDF...' : 'Buscando Site...'}`;

    try {
        const response = await fetch('/api/link-profundo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlBase, tipo: tipo })
        });
        const data = await response.json();
        window.open(data.url, '_blank');
    } catch (err) {
        console.error(err);
        window.open(urlBase, '_blank');
    } finally {
        el.innerHTML = textoOriginal;
        el.classList.remove('disabled');
    }
}

function renderizarLote() {
    const container = document.getElementById('resultados-container');
    const btnLoadMore = document.getElementById('btn-load-more');
    const inicio = paginaAtual * itensPorPagina;
    const fim = inicio + itensPorPagina;
    const lote = todosConcursos.slice(inicio, fim);

    lote.forEach(c => {
        const div = document.createElement('div');
        div.className = 'concurso-card';
        const linkBase = c['Link'] && c['Link'] !== '#' ? c['Link'] : 'https://www.pciconcursos.com.br/concursos/';
        
        // Prepara texto para link único
        const textoConcurso = c['Informações do Concurso'].replace(/'/g, "\\'");

        div.innerHTML = `
            <h3>${c['Informações do Concurso']}</h3>
            <div class="meta-line">
                <span class="badge money"><i class="fas fa-money-bill-wave"></i> ${c['Salário']}</span>
                <span class="badge uf"><i class="fas fa-map-marker-alt"></i> ${c['UF']}</span>
                <span class="badge date"><i class="far fa-calendar-alt"></i> ${c['Data Fim Inscrição']}</span>
                
                <button class="icon-btn btn-copy-small" onclick="copiarLinkUnico('${textoConcurso}')" title="Copiar link deste concurso">
                    <i class="fas fa-link"></i>
                </button>
                <button class="icon-btn btn-zap-small" onclick="compartilharZapUnico('${textoConcurso}')" title="Enviar no WhatsApp">
                    <i class="fab fa-whatsapp"></i>
                </button>

                <a href="javascript:void(0)" class="action-btn btn-edital" onclick="clicarAcao(this, '${linkBase}', 'edital')">
                    <i class="fas fa-file-pdf"></i> Ver Edital
                </a>
                <a href="javascript:void(0)" class="action-btn btn-inscricao" onclick="clicarAcao(this, '${linkBase}', 'inscricao')">
                    ✍️ Inscrição
                </a>
            </div>
        `;
        container.appendChild(div);
    });

    if (fim < todosConcursos.length) {
        btnLoadMore.style.display = 'block';
        btnLoadMore.innerText = `👇 Carregar mais (${todosConcursos.length - fim} restantes)`;
    } else {
        btnLoadMore.style.display = 'none';
    }
}

function carregarMais() {
    paginaAtual++;
    renderizarLote();
}

window.addEventListener('load', () => {
    const params = new URLSearchParams(window.location.search);
    let deveBuscar = false;

    if (params.has('q')) { document.getElementById('palavra_chave').value = params.get('q'); deveBuscar = true; }
    if (params.has('salario')) { document.getElementById('salario_minimo').value = params.get('salario'); deveBuscar = true; }
    if (params.has('excluir')) { document.getElementById('excluir_palavra').value = params.get('excluir'); deveBuscar = true; }
    
    if (params.has('uf')) {
        params.get('uf').split(',').forEach(uf => {
            const btn = document.querySelector(`.uf-btn[data-value="${uf}"]`);
            if (btn) btn.classList.add('active');
        });
        deveBuscar = true;
    }
    if (params.has('regiao')) {
        params.get('regiao').split(',').forEach(reg => {
            const btn = document.querySelector(`.region-btn[data-value="${reg}"]`);
            if (btn) btn.classList.add('active');
        });
        deveBuscar = true;
    }

    if (deveBuscar) { document.getElementById('searchForm').dispatchEvent(new Event('submit')); }
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

    // SKELETON LOADING
    container.innerHTML = '';
    statusDiv.style.display = 'none';
    let skeletonsHTML = '';
    for(let i=0; i<5; i++) {
        skeletonsHTML += `
            <div class="skeleton-card">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-title" style="width: 60%"></div>
                <div style="margin-top: 20px;">
                    <div class="skeleton skeleton-badge"></div>
                    <div class="skeleton skeleton-badge"></div>
                    <div class="skeleton skeleton-badge"></div>
                </div>
            </div>
        `;
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
    
    window.history.pushState({}, '', window.location.pathname + '?' + params.toString());

    const payload = {
        salario_minimo: salario,
        palavra_chave: palavraChave,
        excluir_palavra: excluir,
        regioes: activeRegions,
        ufs: activeUfs
    };

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

        container.innerHTML = ''; // Limpa skeleton

        if (todosConcursos.length === 0) {
            statusDiv.style.display = 'block';
            statusDiv.className = 'empty';
            statusDiv.innerHTML = `
                ❌ Não foi possível encontrar concursos com esses filtros.<br>
                Tente ajustar os filtros ou aguarde por novas oportunidades.
            `;
            return;
        }

        statusDiv.style.display = 'none';
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
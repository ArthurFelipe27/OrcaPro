/* ===[ ESTADO E VARIÁVEIS GLOBAIS ]=== */
let itensAtuais = [];
let totalGeral = 0;
let indiceEdicao = -1;
let idOrcamentoAtual = null;

/* ===[ UTILITÁRIOS DE FORMATAÇÃO ]=== */
function formatarMoeda(valor) {
    return value = valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function converterMoeda(str) {
    if (!str) return 0;
    // Remove R$, espaços e substitui vírgula por ponto
    return parseFloat(str.replace('R$', '').replace(/\./g, '').replace(',', '.').trim());
}

/* ===[ NAVEGAÇÃO ]=== */
function navegar(idTela) {
    document.querySelectorAll('.btn-nav').forEach(btn => btn.classList.remove('ativo'));

    const mapa = { 'inicio': 0, 'criar': 1, 'historico': 2, 'configuracoes': 3, 'ajuda': 4 };
    const botoes = document.querySelectorAll('.btn-nav');
    if (mapa[idTela] !== undefined) botoes[mapa[idTela]].classList.add('ativo');

    document.querySelectorAll('.secao').forEach(sec => sec.classList.remove('ativa'));
    document.getElementById(idTela).classList.add('ativa');

    if (idTela === 'inicio') carregarEstatisticas();
    if (idTela === 'historico') carregarHistorico();
    if (idTela === 'configuracoes') carregarConfiguracoes();
}

function iniciarNovoOrcamento() {
    resetarFormulario();
    navegar('criar');
}

/* ===[ GERENCIAMENTO DE ITENS E FORMULÁRIO ]=== */
function resetarFormulario() {
    idOrcamentoAtual = null;
    itensAtuais = [];
    document.getElementById('titulo-formulario').innerText = 'Novo Orçamento';
    document.getElementById('cliente-nome').value = '';
    document.getElementById('cliente-telefone').value = '';
    document.getElementById('cliente-email').value = '';
    document.getElementById('cliente-endereco').value = '';
    document.getElementById('item-desc').value = '';
    document.getElementById('item-obs').value = '';
    document.getElementById('item-qtd').value = '1';
    document.getElementById('item-preco').value = '';

    resetarEstadoEdicao();
    renderizarItens();
}

function mascaraMoedaInput(input) {
    let valor = input.value.replace(/\D/g, "");
    valor = (valor / 100).toFixed(2) + "";
    valor = valor.replace(".", ",");
    valor = valor.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
    input.value = valor;
}

function obterValorMoeda(idInput) {
    const val = document.getElementById(idInput).value;
    if (!val) return 0;
    return parseFloat(val.replace(/\./g, '').replace(',', '.'));
}

function adicionarItem() {
    const desc = document.getElementById('item-desc').value;
    const obs = document.getElementById('item-obs').value;
    const qtd = parseFloat(document.getElementById('item-qtd').value);
    const preco = obterValorMoeda('item-preco');

    if (!desc || isNaN(qtd) || preco <= 0) {
        alert('Preencha a descrição, quantidade e um preço válido.');
        return;
    }

    const total = qtd * preco;
    const novoItem = { desc, obs, qtd, preco, total };

    if (indiceEdicao >= 0) {
        itensAtuais[indiceEdicao] = novoItem;
        resetarEstadoEdicao();
    } else {
        itensAtuais.push(novoItem);
    }

    renderizarItens();

    document.getElementById('item-desc').value = '';
    document.getElementById('item-obs').value = '';
    document.getElementById('item-qtd').value = '1';
    document.getElementById('item-preco').value = '';
    document.getElementById('item-desc').focus();
}

function resetarEstadoEdicao() {
    indiceEdicao = -1;
    const btn = document.getElementById('btn-adicionar-item');
    btn.innerText = 'Adicionar';
    btn.classList.remove('btn-aviso');
    btn.classList.add('btn-secundario');
}

function editarItem(index) {
    const item = itensAtuais[index];
    document.getElementById('item-desc').value = item.desc;
    document.getElementById('item-obs').value = item.obs || '';
    document.getElementById('item-qtd').value = item.qtd;

    // Formatar preço para o input
    let precoStr = item.preco.toFixed(2).replace('.', ',');
    document.getElementById('item-preco').value = precoStr;

    indiceEdicao = index;
    const btn = document.getElementById('btn-adicionar-item');
    btn.innerText = 'Atualizar Item';
    btn.classList.remove('btn-secundario');
    btn.classList.add('btn-aviso');
    document.getElementById('item-desc').focus();
}

function removerItem(index) {
    if (confirm('Remover este item?')) {
        itensAtuais.splice(index, 1);
        if (indiceEdicao === index) resetarEstadoEdicao();
        renderizarItens();
    }
}

function renderizarItens() {
    const corpoTabela = document.getElementById('lista-itens');
    corpoTabela.innerHTML = '';
    totalGeral = 0;

    itensAtuais.forEach((item, index) => {
        totalGeral += item.total;
        let descHtml = `<strong>${item.desc}</strong>`;
        if (item.obs) descHtml += `<span class="item-obs-texto">Obs: ${item.obs}</span>`;

        const linha = `
            <tr class="${indiceEdicao === index ? 'linha-editando' : ''}">
                <td>${descHtml}</td>
                <td>${item.qtd}</td>
                <td>${formatarMoeda(item.preco)}</td>
                <td>${formatarMoeda(item.total)}</td>
                <td>
                    <button class="btn btn-secundario" style="padding: 5px 10px;" onclick="editarItem(${index})">✏️</button>
                    <button class="btn btn-perigo" style="padding: 5px 10px;" onclick="removerItem(${index})">X</button>
                </td>
            </tr>
        `;
        corpoTabela.innerHTML += linha;
    });

    document.getElementById('display-total').innerText = `Total: ${formatarMoeda(totalGeral)}`;
}

/* ===[ SALVAR ORÇAMENTO ]=== */
async function salvarOrcamento() {
    const cliente = document.getElementById('cliente-nome').value;
    const telefone = document.getElementById('cliente-telefone').value;
    const email = document.getElementById('cliente-email').value;
    const endereco = document.getElementById('cliente-endereco').value;

    if (!cliente || itensAtuais.length === 0) {
        alert('Informe o nome do cliente e adicione itens.');
        return;
    }

    const telefoneLimpo = telefone.replace(/\D/g, "");
    if (telefoneLimpo.length < 10) {
        alert('Por favor, informe um telefone válido com DDD (mínimo 10 dígitos).');
        return;
    }

    const dadosOrcamento = {
        id: idOrcamentoAtual,
        cliente: cliente,
        telefone: telefone,
        email: email,
        endereco: endereco,
        itens: itensAtuais,
        total: totalGeral,
        data: new Date().toLocaleDateString('pt-BR')
    };

    try {
        const resposta = await window.pywebview.api.salvar_orcamento(dadosOrcamento);
        if (resposta.status === 'ok') {
            alert('Orçamento salvo com sucesso!');
            resetarFormulario();
            navegar('historico');
        } else {
            alert('Erro ao salvar: ' + resposta.mensagem);
        }
    } catch (e) {
        alert('Erro de conexão com o sistema.');
    }
}

async function editarOrcamento(id) {
    try {
        const orcamento = await window.pywebview.api.obter_detalhes_orcamento(id);
        if (orcamento) {
            idOrcamentoAtual = orcamento.id;
            document.getElementById('titulo-formulario').innerText = `Editando Orçamento #${orcamento.id}`;
            document.getElementById('cliente-nome').value = orcamento.cliente;
            document.getElementById('cliente-email').value = orcamento.email || '';
            document.getElementById('cliente-telefone').value = orcamento.telefone || '';
            document.getElementById('cliente-endereco').value = orcamento.endereco || '';
            itensAtuais = orcamento.itens;
            renderizarItens();
            navegar('criar');
        }
    } catch (e) { alert('Erro ao carregar orçamento.'); }
}

/* ===[ HISTÓRICO E AÇÕES ]=== */
async function definirStatus(id, novoStatus) {
    try {
        const resposta = await window.pywebview.api.atualizar_status(id, novoStatus);
        if (resposta.status === 'ok') { carregarHistorico(); carregarEstatisticas(); }
    } catch (e) { }
}

async function gerarPDF(id) {
    try {
        document.body.style.cursor = 'wait';
        const resposta = await window.pywebview.api.gerar_pdf(id);
        document.body.style.cursor = 'default';

        if (resposta.status === 'ok') {
            console.log("PDF Gerado:", resposta.arquivo);
        } else {
            alert('Erro ao gerar PDF: ' + resposta.mensagem);
        }
    } catch (e) {
        document.body.style.cursor = 'default';
        alert('Erro ao solicitar PDF.');
    }
}

async function excluirOrcamento(id) {
    if (!confirm("Excluir permanentemente?")) return;
    try {
        await window.pywebview.api.excluir_orcamento(id);
        carregarHistorico();
        carregarEstatisticas();
    } catch (e) { }
}

async function carregarHistorico() {
    try {
        const historico = await window.pywebview.api.obter_historico();
        const container = document.getElementById('container-historico');
        if (historico.length === 0) {
            container.innerHTML = '<p style="text-align:center; color: #666; margin-top: 20px;">Nenhum orçamento encontrado.</p>';
            return;
        }

        let html = '';
        historico.reverse().forEach(item => {
            let classeStatus = 'status-pendente';
            let rotuloStatus = 'Pendente';
            // Mapeamento dos status do banco (que estão em inglês ou padrão antigo) para visual
            if (item.status === 'APROVADO' || item.status === 'APPROVED') { classeStatus = 'status-aprovado'; rotuloStatus = 'Aprovado ✅'; }
            else if (item.status === 'REJEITADO' || item.status === 'REJECTED') { classeStatus = 'status-rejeitado'; rotuloStatus = 'Rejeitado ❌'; }

            html += `
                <div class="item-historico ${classeStatus}">
                    <div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${item.cliente}</div>
                        <div style="font-size: 0.9rem; color: var(--texto-suave);">
                             #${item.id} • ${item.data} • ${item.qtd_itens} itens
                        </div>
                        <div style="font-size: 0.8rem; font-weight: bold; margin-top: 4px; color: #555;">${rotuloStatus}</div>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 5px;">
                        <div style="font-weight: 700; color: var(--texto-principal); font-size: 1.1rem;">${formatarMoeda(item.total)}</div>
                        <div style="display: flex; gap: 5px;">
                            ${item.status !== 'APROVADO' && item.status !== 'APPROVED' ? `<button class="btn-icone" onclick="definirStatus(${item.id}, 'APROVADO')" title="Aprovar">✅</button>` : ''}
                            ${item.status !== 'REJEITADO' && item.status !== 'REJECTED' ? `<button class="btn-icone" onclick="definirStatus(${item.id}, 'REJEITADO')" title="Rejeitar">❌</button>` : ''}
                            <div style="width: 1px; background: #ccc; margin: 0 5px;"></div>
                            <button class="btn-icone" onclick="editarOrcamento(${item.id})" title="Editar">✏️</button>
                            <button class="btn-icone" onclick="gerarPDF(${item.id})" title="PDF">📄</button>
                            <button class="btn-icone" onclick="excluirOrcamento(${item.id})" title="Excluir" style="color: #ef4444;">🗑️</button>
                        </div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) { }
}

async function carregarEstatisticas() {
    try {
        const stats = await window.pywebview.api.obter_estatisticas();
        document.getElementById('stat-aprovado-valor').innerText = formatarMoeda(stats.aprovados_valor);
        document.getElementById('stat-aprovado-qtd').innerText = stats.aprovados_qtd;
        document.getElementById('stat-pendente-valor').innerText = formatarMoeda(stats.pendentes_valor);
        document.getElementById('stat-pendente-qtd').innerText = stats.pendentes_qtd;
        document.getElementById('stat-rejeitado-qtd').innerText = stats.rejeitados_qtd;
        document.getElementById('stat-total-geral').innerText = stats.total_geral;
    } catch (e) { }
}

/* ===[ CONFIGURAÇÕES ]=== */
async function selecionarPasta() {
    try {
        const caminho = await window.pywebview.api.selecionar_pasta();
        if (caminho) document.getElementById('caminho-pdf').value = caminho;
    } catch (e) { }
}

async function selecionarLogo() {
    try {
        const resposta = await window.pywebview.api.selecionar_logo();
        if (resposta.status === 'ok') {
            document.getElementById('caminho-logo').value = resposta.caminho;
            const preview = document.getElementById('logo-preview');
            // Cache busting
            preview.src = resposta.caminho + '?t=' + new Date().getTime();
            preview.style.display = 'block';
            document.getElementById('logo-placeholder').style.display = 'none';
        } else if (resposta.status === 'erro') {
            alert(resposta.mensagem);
        }
    } catch (e) { console.error(e); }
}

async function carregarConfiguracoes() {
    try {
        const cfg = await window.pywebview.api.obter_configuracoes();
        if (cfg) {
            document.getElementById('empresa-nome').value = cfg.empresa || '';
            document.getElementById('empresa-razao-social').value = cfg.razao_social || '';
            document.getElementById('empresa-cnpj').value = cfg.cnpj || '';
            document.getElementById('empresa-endereco').value = cfg.endereco || '';
            document.getElementById('empresa-telefone').value = cfg.telefone || '';
            document.getElementById('texto-rodape').value = cfg.rodape || '';
            document.getElementById('caminho-pdf').value = cfg.caminho_pdf || '';
            document.getElementById('pdf-subpasta').checked = cfg.criar_subpasta;
            document.getElementById('pdf-salvar-auto').checked = cfg.salvar_auto;

            if (cfg.caminho_logo) {
                document.getElementById('caminho-logo').value = cfg.caminho_logo;
                const preview = document.getElementById('logo-preview');
                preview.src = cfg.caminho_logo + '?t=' + new Date().getTime();
                preview.style.display = 'block';
                document.getElementById('logo-placeholder').style.display = 'none';
            }

            document.getElementById('pag-pix').checked = cfg.pagamento_pix;
            document.getElementById('pag-credito').checked = cfg.pagamento_credito;
            document.getElementById('pag-debito').checked = cfg.pagamento_debito;
            document.getElementById('pag-dinheiro').checked = cfg.pagamento_dinheiro;
        }
    } catch (e) { }
}

async function salvarConfiguracoes() {
    try {
        await window.pywebview.api.salvar_configuracoes({
            empresa: document.getElementById('empresa-nome').value,
            razao_social: document.getElementById('empresa-razao-social').value,
            cnpj: document.getElementById('empresa-cnpj').value,
            endereco: document.getElementById('empresa-endereco').value,
            telefone: document.getElementById('empresa-telefone').value,
            rodape: document.getElementById('texto-rodape').value,
            caminho_pdf: document.getElementById('caminho-pdf').value,
            criar_subpasta: document.getElementById('pdf-subpasta').checked,
            salvar_auto: document.getElementById('pdf-salvar-auto').checked,
            caminho_logo: document.getElementById('caminho-logo').value,
            pagamento_pix: document.getElementById('pag-pix').checked,
            pagamento_credito: document.getElementById('pag-credito').checked,
            pagamento_debito: document.getElementById('pag-debito').checked,
            pagamento_dinheiro: document.getElementById('pag-dinheiro').checked,
        });
        alert('Configurações salvas!');
    } catch (e) { }
}

/* ===[ MÁSCARAS E INPUTS ]=== */
function mascaraTelefone(evento) {
    let input = evento.target;
    let valor = input.value.replace(/\D/g, "");

    if (valor.length > 11) valor = valor.slice(0, 11);

    if (valor.length > 10) {
        valor = valor.replace(/^(\d{2})(\d{1})(\d{4})(\d{4}).*/, '($1) $2 $3-$4');
    } else if (valor.length > 6) {
        valor = valor.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
    } else if (valor.length > 2) {
        valor = valor.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
    }
    input.value = valor;
}

function mascaraCNPJ(evento) {
    let input = evento.target;
    let v = input.value.replace(/\D/g, "");
    if (v.length > 14) v = v.slice(0, 14);
    v = v.replace(/^(\d{2})(\d)/, '$1.$2');
    v = v.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
    v = v.replace(/\.(\d{3})(\d)/, '.$1/$2');
    v = v.replace(/(\d{4})(\d)/, '$1-$2');
    input.value = v;
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => carregarEstatisticas(), 500);

    const inputTelefone = document.getElementById('cliente-telefone');
    if (inputTelefone) inputTelefone.addEventListener('input', mascaraTelefone);

    const inputEmpresaTel = document.getElementById('empresa-telefone');
    if (inputEmpresaTel) inputEmpresaTel.addEventListener('input', mascaraTelefone);

    const inputCNPJ = document.getElementById('empresa-cnpj');
    if (inputCNPJ) inputCNPJ.addEventListener('input', mascaraCNPJ);
});
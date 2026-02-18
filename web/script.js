/* ===[ ESTADO E VARIÁVEIS GLOBAIS ]=== */
let currentItems = [];
let grandTotal = 0;
let editingItemIndex = -1;
let currentBudgetId = null;

/* ===[ UTILITÁRIOS DE FORMATAÇÃO ]=== */
function formatCurrency(value) {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function parseCurrency(str) {
    if (!str) return 0;
    // Remove R$, espaços e substitui vírgula por ponto
    return parseFloat(str.replace('R$', '').replace(/\./g, '').replace(',', '.').trim());
}

/* ===[ NAVEGAÇÃO ]=== */
function navigate(screenId) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const map = { 'home': 0, 'create': 1, 'history': 2, 'settings': 3, 'help': 4 };
    const buttons = document.querySelectorAll('.nav-btn');
    if (map[screenId] !== undefined) buttons[map[screenId]].classList.add('active');

    document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');

    if (screenId === 'home') loadStats();
    if (screenId === 'history') loadHistory();
    if (screenId === 'settings') loadSettings();
}

function startNewBudget() {
    resetForm();
    navigate('create');
}

/* ===[ RESET E ITENS ]=== */
function resetForm() {
    currentBudgetId = null;
    currentItems = [];
    document.getElementById('form-title').innerText = 'Novo Orçamento';
    document.getElementById('client-name').value = '';
    document.getElementById('client-phone').value = '';
    document.getElementById('client-email').value = '';
    document.getElementById('client-address').value = '';
    document.getElementById('item-desc').value = '';
    document.getElementById('item-obs').value = '';
    document.getElementById('item-qty').value = '1';
    document.getElementById('item-price').value = '';

    resetItemEditState();
    renderItems();
}

function maskMoneyInput(input) {
    let value = input.value.replace(/\D/g, "");
    value = (value / 100).toFixed(2) + "";
    value = value.replace(".", ",");
    value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
    input.value = value;
}

function getMoneyValue(inputId) {
    const val = document.getElementById(inputId).value;
    if (!val) return 0;
    return parseFloat(val.replace(/\./g, '').replace(',', '.'));
}

function addItem() {
    const desc = document.getElementById('item-desc').value;
    const obs = document.getElementById('item-obs').value;
    const qty = parseFloat(document.getElementById('item-qty').value);
    const price = getMoneyValue('item-price');

    if (!desc || isNaN(qty) || price <= 0) {
        alert('Preencha a descrição, quantidade e um preço válido.');
        return;
    }

    const total = qty * price;
    const newItem = { desc, obs, qty, price, total };

    if (editingItemIndex >= 0) {
        currentItems[editingItemIndex] = newItem;
        resetItemEditState();
    } else {
        currentItems.push(newItem);
    }

    renderItems();

    document.getElementById('item-desc').value = '';
    document.getElementById('item-obs').value = '';
    document.getElementById('item-qty').value = '1';
    document.getElementById('item-price').value = '';
    document.getElementById('item-desc').focus();
}

function resetItemEditState() {
    editingItemIndex = -1;
    const btn = document.getElementById('btn-add-item');
    btn.innerText = 'Adicionar';
    btn.classList.remove('btn-warning');
    btn.classList.add('btn-secondary');
}

function editItem(index) {
    const item = currentItems[index];
    document.getElementById('item-desc').value = item.desc;
    document.getElementById('item-obs').value = item.obs || '';
    document.getElementById('item-qty').value = item.qty;

    // Formatar preço para o input
    let priceStr = item.price.toFixed(2).replace('.', ',');
    // Adicionar separadores de milhar manualmente se necessário, ou deixar simples
    document.getElementById('item-price').value = priceStr;

    editingItemIndex = index;
    const btn = document.getElementById('btn-add-item');
    btn.innerText = 'Atualizar Item';
    btn.classList.remove('btn-secondary');
    btn.classList.add('btn-warning');
    document.getElementById('item-desc').focus();
}

function removeItem(index) {
    if (confirm('Remover este item?')) {
        currentItems.splice(index, 1);
        if (editingItemIndex === index) resetItemEditState();
        renderItems();
    }
}

function renderItems() {
    const tbody = document.getElementById('items-list');
    tbody.innerHTML = '';
    grandTotal = 0;

    currentItems.forEach((item, index) => {
        grandTotal += item.total;
        let descHtml = `<strong>${item.desc}</strong>`;
        if (item.obs) descHtml += `<span class="item-obs-text">Obs: ${item.obs}</span>`;

        const row = `
            <tr class="${editingItemIndex === index ? 'editing-row' : ''}">
                <td>${descHtml}</td>
                <td>${item.qty}</td>
                <td>${formatCurrency(item.price)}</td>
                <td>${formatCurrency(item.total)}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 5px 10px;" onclick="editItem(${index})">✏️</button>
                    <button class="btn btn-danger" style="padding: 5px 10px;" onclick="removeItem(${index})">X</button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    document.getElementById('total-display').innerText = `Total: ${formatCurrency(grandTotal)}`;
}

/* ===[ SALVAR ORÇAMENTO ]=== */
async function saveBudget() {
    const client = document.getElementById('client-name').value;
    const phone = document.getElementById('client-phone').value;
    const email = document.getElementById('client-email').value;
    const address = document.getElementById('client-address').value;

    if (!client || currentItems.length === 0) {
        alert('Informe o nome do cliente e adicione itens.');
        return;
    }

    // Validação estrita de telefone
    const cleanPhone = phone.replace(/\D/g, "");
    if (cleanPhone.length < 10) {
        alert('Por favor, informe um telefone válido com DDD (mínimo 10 dígitos).');
        return;
    }

    const budgetData = {
        id: currentBudgetId,
        client: client,
        phone: phone,
        email: email,
        address: address,
        items: currentItems,
        total: grandTotal,
        date: new Date().toLocaleDateString('pt-BR')
    };

    try {
        const response = await window.pywebview.api.save_budget(budgetData);
        if (response.status === 'ok') {
            alert('Orçamento salvo com sucesso!');
            resetForm();
            navigate('history');
        } else {
            alert('Erro ao salvar: ' + response.message);
        }
    } catch (e) {
        alert('Erro de conexão com o sistema.');
    }
}

async function editBudget(id) {
    try {
        const budget = await window.pywebview.api.get_budget_details(id);
        if (budget) {
            currentBudgetId = budget.id;
            document.getElementById('form-title').innerText = `Editando Orçamento #${budget.id}`;
            document.getElementById('client-name').value = budget.client;
            document.getElementById('client-email').value = budget.email || '';
            document.getElementById('client-phone').value = budget.phone || '';
            document.getElementById('client-address').value = budget.address || '';
            currentItems = budget.items;
            renderItems();
            navigate('create');
        }
    } catch (e) { alert('Erro ao carregar orçamento.'); }
}

/* ===[ HISTÓRICO ]=== */
async function setStatus(id, newStatus) {
    try {
        const response = await window.pywebview.api.update_status(id, newStatus);
        if (response.status === 'ok') { loadHistory(); loadStats(); }
    } catch (e) { }
}

async function generatePDF(id) {
    try {
        document.body.style.cursor = 'wait';
        const response = await window.pywebview.api.generate_pdf(id);
        document.body.style.cursor = 'default';

        if (response.status === 'ok') {
            // Se salvo automaticamente, ok. Se for temp, o Python já abre.
            console.log("PDF:", response.file);
        } else {
            alert('Erro ao gerar PDF: ' + response.message);
        }
    } catch (e) {
        document.body.style.cursor = 'default';
        alert('Erro ao solicitar PDF.');
    }
}

async function deleteBudget(id) {
    if (!confirm("Excluir permanentemente?")) return;
    try {
        await window.pywebview.api.delete_budget(id);
        loadHistory();
        loadStats();
    } catch (e) { }
}

async function loadHistory() {
    try {
        const history = await window.pywebview.api.get_history();
        const container = document.getElementById('history-container');
        if (history.length === 0) {
            container.innerHTML = '<p style="text-align:center; color: #666; margin-top: 20px;">Nenhum orçamento encontrado.</p>';
            return;
        }

        let html = '';
        history.reverse().forEach(item => {
            let statusClass = 'status-pending';
            let statusLabel = 'Pendente';
            if (item.status === 'APPROVED') { statusClass = 'status-approved'; statusLabel = 'Aprovado ✅'; }
            else if (item.status === 'REJECTED') { statusClass = 'status-rejected'; statusLabel = 'Rejeitado ❌'; }

            html += `
                <div class="history-item ${statusClass}">
                    <div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${item.client}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">
                             #${item.id} • ${item.date} • ${item.items_count} itens
                        </div>
                        <div style="font-size: 0.8rem; font-weight: bold; margin-top: 4px; color: #555;">${statusLabel}</div>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 5px;">
                        <div style="font-weight: 700; color: var(--text-main); font-size: 1.1rem;">${formatCurrency(item.total)}</div>
                        <div style="display: flex; gap: 5px;">
                            ${item.status !== 'APPROVED' ? `<button class="btn-icon" onclick="setStatus(${item.id}, 'APPROVED')" title="Aprovar">✅</button>` : ''}
                            ${item.status !== 'REJECTED' ? `<button class="btn-icon" onclick="setStatus(${item.id}, 'REJECTED')" title="Rejeitar">❌</button>` : ''}
                            <div style="width: 1px; background: #ccc; margin: 0 5px;"></div>
                            <button class="btn-icon" onclick="editBudget(${item.id})" title="Editar">✏️</button>
                            <button class="btn-icon" onclick="generatePDF(${item.id})" title="PDF">📄</button>
                            <button class="btn-icon" onclick="deleteBudget(${item.id})" title="Excluir" style="color: #ef4444;">🗑️</button>
                        </div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) { }
}

async function loadStats() {
    try {
        const stats = await window.pywebview.api.get_stats();
        document.getElementById('stat-approved-value').innerText = formatCurrency(stats.approved_value);
        document.getElementById('stat-approved-count').innerText = stats.approved_count;
        document.getElementById('stat-pending-value').innerText = formatCurrency(stats.pending_value);
        document.getElementById('stat-pending-count').innerText = stats.pending_count;
        document.getElementById('stat-rejected-count').innerText = stats.rejected_count;
        document.getElementById('stat-total-count').innerText = stats.total_count;
    } catch (e) { }
}

/* ===[ CONFIGURAÇÕES ]=== */
async function selectFolder() {
    try {
        const path = await window.pywebview.api.select_folder();
        if (path) document.getElementById('pdf-path').value = path;
    } catch (e) { }
}

async function selectLogo() {
    try {
        const response = await window.pywebview.api.select_logo();
        if (response.status === 'ok') {
            document.getElementById('logo-path').value = response.path;
            const preview = document.getElementById('logo-preview');
            // Adiciona timestamp para forçar reload da imagem se for o mesmo nome
            preview.src = response.path + '?t=' + new Date().getTime();
            preview.style.display = 'block';
            document.getElementById('logo-placeholder').style.display = 'none';
        } else if (response.status === 'error') {
            alert(response.message);
        }
    } catch (e) { console.error(e); }
}

async function loadSettings() {
    try {
        const s = await window.pywebview.api.get_settings();
        if (s) {
            document.getElementById('company-name').value = s.company || '';
            document.getElementById('company-legal-name').value = s.legal_name || '';
            document.getElementById('company-cnpj').value = s.cnpj || '';
            document.getElementById('company-address').value = s.address || '';
            document.getElementById('company-phone').value = s.phone || '';
            document.getElementById('footer-text').value = s.footer || '';
            document.getElementById('pdf-path').value = s.pdf_path || '';
            document.getElementById('pdf-subfolder').checked = s.create_subfolder;
            document.getElementById('pdf-auto-save').checked = s.auto_save;

            // Logo
            if (s.logo_path) {
                document.getElementById('logo-path').value = s.logo_path;
                const preview = document.getElementById('logo-preview');
                preview.src = s.logo_path + '?t=' + new Date().getTime();
                preview.style.display = 'block';
                document.getElementById('logo-placeholder').style.display = 'none';
            }

            // Pagamentos
            document.getElementById('pay-pix').checked = s.payment_pix;
            document.getElementById('pay-credit').checked = s.payment_credit;
            document.getElementById('pay-debit').checked = s.payment_debit;
            document.getElementById('pay-cash').checked = s.payment_cash;
        }
    } catch (e) { }
}

async function saveSettings() {
    try {
        await window.pywebview.api.save_settings({
            company: document.getElementById('company-name').value,
            legal_name: document.getElementById('company-legal-name').value,
            cnpj: document.getElementById('company-cnpj').value,
            address: document.getElementById('company-address').value,
            phone: document.getElementById('company-phone').value,
            footer: document.getElementById('footer-text').value,
            pdf_path: document.getElementById('pdf-path').value,
            create_subfolder: document.getElementById('pdf-subfolder').checked,
            auto_save: document.getElementById('pdf-auto-save').checked,
            logo_path: document.getElementById('logo-path').value,
            payment_pix: document.getElementById('pay-pix').checked,
            payment_credit: document.getElementById('pay-credit').checked,
            payment_debit: document.getElementById('pay-debit').checked,
            payment_cash: document.getElementById('pay-cash').checked,
        });
        alert('Configurações salvas!');
    } catch (e) { }
}

/* ===[ MÁSCARAS E INPUTS ]=== */
function maskPhone(event) {
    let input = event.target;
    let value = input.value.replace(/\D/g, "");

    // Limita a 11 números
    if (value.length > 11) value = value.slice(0, 11);

    // Formatação
    if (value.length > 10) {
        // (11) 9 1234-5678 (Padrão com 9º dígito separado)
        value = value.replace(/^(\d{2})(\d{1})(\d{4})(\d{4}).*/, '($1) $2 $3-$4');
    } else if (value.length > 6) {
        // (11) 1234-5678 (Fixo)
        value = value.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
    } else if (value.length > 2) {
        value = value.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
    }
    input.value = value;
}

function maskCNPJ(event) {
    let input = event.target;
    let v = input.value.replace(/\D/g, "");
    if (v.length > 14) v = v.slice(0, 14);
    v = v.replace(/^(\d{2})(\d)/, '$1.$2');
    v = v.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
    v = v.replace(/\.(\d{3})(\d)/, '.$1/$2');
    v = v.replace(/(\d{4})(\d)/, '$1-$2');
    input.value = v;
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => loadStats(), 500);

    const phoneInput = document.getElementById('client-phone');
    if (phoneInput) phoneInput.addEventListener('input', maskPhone);

    const companyPhone = document.getElementById('company-phone');
    if (companyPhone) companyPhone.addEventListener('input', maskPhone);

    const cnpjInput = document.getElementById('company-cnpj');
    if (cnpjInput) cnpjInput.addEventListener('input', maskCNPJ);
});
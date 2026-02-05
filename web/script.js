/* ===[ ESTADO E VARIÁVEIS GLOBAIS ]=== */
let currentItems = [];
let grandTotal = 0;
let editingItemIndex = -1; // -1 significa que não estamos editando nenhum item
let currentBudgetId = null; // null significa novo orçamento

/* ===[ NAVEGAÇÃO ENTRE TELAS ]=== */
function navigate(screenId) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const buttons = document.querySelectorAll('.nav-btn');
    if (screenId === 'home') buttons[0].classList.add('active');
    if (screenId === 'create') buttons[1].classList.add('active');
    if (screenId === 'history') buttons[2].classList.add('active');
    if (screenId === 'settings') buttons[3].classList.add('active');
    if (screenId === 'help') buttons[4].classList.add('active');

    document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');

    if (screenId === 'home') loadStats();
    if (screenId === 'create') {
        // Se viemos pelo menu e não temos ID carregado, é um NOVO orçamento.
    }
    if (screenId === 'history') loadHistory();
    if (screenId === 'settings') loadSettings();
}

function startNewBudget() {
    resetForm();
    navigate('create');
}

/* ===[ RESET DE FORMULÁRIOS ]=== */
function resetForm() {
    currentBudgetId = null;
    currentItems = [];
    document.getElementById('form-title').innerText = 'Novo Orçamento';
    document.getElementById('client-name').value = '';
    document.getElementById('client-phone').value = '';
    document.getElementById('client-email').value = '';
    document.getElementById('client-address').value = '';

    // Reset item inputs
    document.getElementById('item-desc').value = '';
    document.getElementById('item-obs').value = '';
    document.getElementById('item-qty').value = '1';
    document.getElementById('item-price').value = '';

    resetItemEditState();
    renderItems();
}

/* ===[ GERENCIAMENTO DE ITENS DO ORÇAMENTO ]=== */
function addItem() {
    const desc = document.getElementById('item-desc').value;
    const obs = document.getElementById('item-obs').value;
    const qty = parseFloat(document.getElementById('item-qty').value);
    const price = parseFloat(document.getElementById('item-price').value);

    if (!desc || isNaN(qty) || isNaN(price)) {
        alert('Preencha a descrição, quantidade e preço.');
        return;
    }

    const total = qty * price;
    const newItem = { desc, obs, qty, price, total };

    if (editingItemIndex >= 0) {
        // Atualizando item existente
        currentItems[editingItemIndex] = newItem;
        resetItemEditState();
    } else {
        // Adicionando novo
        currentItems.push(newItem);
    }

    renderItems();

    // Limpar campos
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
    document.getElementById('item-price').value = item.price;

    editingItemIndex = index;

    // Mudar botão para indicar edição
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
        if (item.obs) {
            descHtml += `<span class="item-obs-text">Obs: ${item.obs}</span>`;
        }

        const row = `
            <tr class="${editingItemIndex === index ? 'editing-row' : ''}">
                <td>${descHtml}</td>
                <td>${item.qty}</td>
                <td>R$ ${item.price.toFixed(2)}</td>
                <td>R$ ${item.total.toFixed(2)}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 0.8rem; margin-right: 5px;" onclick="editItem(${index})" title="Editar Item">✏️</button>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: 0.8rem;" onclick="removeItem(${index})" title="Remover Item">X</button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    document.getElementById('total-display').innerText = `Total: R$ ${grandTotal.toFixed(2)}`;
}

/* ===[ CRUD DE ORÇAMENTOS (SALVAR/EDITAR) ]=== */
async function saveBudget() {
    const client = document.getElementById('client-name').value;
    const phone = document.getElementById('client-phone').value;
    const email = document.getElementById('client-email').value;
    const address = document.getElementById('client-address').value;

    if (!client || currentItems.length === 0) {
        alert('Informe o nome do cliente e adicione itens.');
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
        console.error("Erro:", e);
        alert('Erro de conexão com o sistema.');
    }
}

async function editBudget(id) {
    try {
        const budget = await window.pywebview.api.get_budget_details(id);
        if (budget) {
            currentBudgetId = budget.id;

            // Preencher campos
            document.getElementById('form-title').innerText = `Editando Orçamento #${budget.id}`;
            document.getElementById('client-name').value = budget.client;
            document.getElementById('client-email').value = budget.email || '';
            document.getElementById('client-phone').value = budget.phone || '';
            document.getElementById('client-address').value = budget.address || '';

            // Carregar itens
            currentItems = budget.items;
            renderItems();

            navigate('create');
        }
    } catch (e) {
        console.error(e);
        alert('Erro ao carregar orçamento para edição.');
    }
}

/* ===[ HISTÓRICO, PDF E STATUS ]=== */

// Atualizar Status (Aprovado/Rejeitado)
async function setStatus(id, newStatus) {
    try {
        const response = await window.pywebview.api.update_status(id, newStatus);
        if (response.status === 'ok') {
            loadHistory();
            loadStats();
        } else {
            alert('Erro ao atualizar status: ' + response.message);
        }
    } catch (e) {
        console.error(e);
        alert('Erro de comunicação.');
    }
}

async function generatePDF(id) {
    try {
        document.body.style.cursor = 'wait';
        const response = await window.pywebview.api.generate_pdf(id);
        document.body.style.cursor = 'default';

        if (response.status === 'ok') {
            console.log("PDF Gerado:", response.file);
        } else {
            alert('Erro ao gerar PDF: ' + response.message);
        }
    } catch (e) {
        document.body.style.cursor = 'default';
        alert('Erro ao solicitar PDF.');
    }
}

async function deleteBudget(id) {
    if (!confirm("Tem certeza que deseja excluir este orçamento permanentemente?")) {
        return;
    }

    try {
        const response = await window.pywebview.api.delete_budget(id);
        if (response.status === 'ok') {
            loadHistory();
            loadStats();
        } else {
            alert("Erro ao excluir: " + response.message);
        }
    } catch (e) {
        alert("Erro ao conectar com o sistema.");
    }
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

            if (item.status === 'APPROVED') {
                statusClass = 'status-approved';
                statusLabel = 'Aprovado ✅';
            } else if (item.status === 'REJECTED') {
                statusClass = 'status-rejected';
                statusLabel = 'Rejeitado ❌';
            }

            html += `
                <div class="history-item ${statusClass}">
                    <div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${item.client}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">
                             #${item.id} • ${item.date} • ${item.items_count} itens
                        </div>
                        <div style="font-size: 0.8rem; font-weight: bold; margin-top: 4px; color: #555;">
                            Status: ${statusLabel}
                        </div>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 5px;">
                        <div style="font-weight: 700; color: var(--text-main); font-size: 1.1rem;">R$ ${item.total.toFixed(2)}</div>
                        
                        <div style="display: flex; gap: 5px;">
                            ${item.status !== 'APPROVED' ?
                    `<button class="btn-icon" onclick="setStatus(${item.id}, 'APPROVED')" title="Aprovar Orçamento">✅</button>` : ''}
                            
                            ${item.status !== 'REJECTED' ?
                    `<button class="btn-icon" onclick="setStatus(${item.id}, 'REJECTED')" title="Rejeitar Orçamento">❌</button>` : ''}
                            
                            <div style="width: 1px; background: #ccc; margin: 0 5px;"></div>

                            <button class="btn-icon" onclick="editBudget(${item.id})" title="Editar Orçamento">✏️</button>
                            <button class="btn-icon" onclick="generatePDF(${item.id})" title="Gerar PDF">📄</button>
                            <button class="btn-icon" onclick="deleteBudget(${item.id})" title="Excluir Orçamento" style="color: #ef4444;">🗑️</button>
                        </div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) { console.log(e); }
}

/* ===[ DASHBOARD E CONFIGURAÇÕES ]=== */
async function loadStats() {
    try {
        const stats = await window.pywebview.api.get_stats();

        document.getElementById('stat-approved-value').innerText = `R$ ${stats.approved_value.toFixed(2)}`;
        document.getElementById('stat-approved-count').innerText = stats.approved_count;

        document.getElementById('stat-pending-value').innerText = `R$ ${stats.pending_value.toFixed(2)}`;
        document.getElementById('stat-pending-count').innerText = stats.pending_count;

        document.getElementById('stat-rejected-count').innerText = stats.rejected_count;
        document.getElementById('stat-total-count').innerText = stats.total_count;

    } catch (e) {
        console.error("Erro ao carregar estatísticas:", e);
    }
}

async function loadSettings() {
    try {
        const settings = await window.pywebview.api.get_settings();
        if (settings) {
            document.getElementById('company-name').value = settings.company || '';
            document.getElementById('company-legal-name').value = settings.legal_name || '';
            document.getElementById('company-cnpj').value = settings.cnpj || '';
            document.getElementById('company-address').value = settings.address || '';
            document.getElementById('company-phone').value = settings.phone || '';
            document.getElementById('footer-text').value = settings.footer || '';

            if (settings.pdf_path) {
                document.getElementById('pdf-path').value = settings.pdf_path;
            }
            document.getElementById('pdf-subfolder').checked = settings.create_subfolder;
        }
    } catch (e) { }
}

async function selectFolder() {
    try {
        const path = await window.pywebview.api.select_folder();
        if (path) {
            document.getElementById('pdf-path').value = path;
        }
    } catch (e) {
        console.error(e);
    }
}

async function saveSettings() {
    const company = document.getElementById('company-name').value;
    const legalName = document.getElementById('company-legal-name').value;
    const cnpj = document.getElementById('company-cnpj').value;
    const address = document.getElementById('company-address').value;
    const phone = document.getElementById('company-phone').value;
    const footer = document.getElementById('footer-text').value;
    const pdfPath = document.getElementById('pdf-path').value;
    const createSubfolder = document.getElementById('pdf-subfolder').checked;

    try {
        await window.pywebview.api.save_settings({
            company: company,
            legal_name: legalName,
            cnpj: cnpj,
            address: address,
            phone: phone,
            footer: footer,
            pdf_path: pdfPath,
            create_subfolder: createSubfolder
        });
        alert('Configurações salvas!');
    } catch (e) { }
}

/* ===[ UTILITÁRIOS E INICIALIZAÇÃO ]=== */
function maskPhone(event) {
    let input = event.target;
    let value = input.value.replace(/\D/g, "");

    if (value.length > 11) value = value.slice(0, 11);

    if (value.length > 2) {
        value = `(${value.slice(0, 2)}) ${value.slice(2)}`;
    }
    if (value.length > 9) {
        value = `${value.slice(0, 9)}-${value.slice(9)}`;
    }

    input.value = value;
}

function maskCNPJ(event) {
    let input = event.target;
    let value = input.value.replace(/\D/g, "");

    if (value.length > 14) value = value.slice(0, 14);

    if (value.length > 2) value = value.replace(/^(\d{2})(\d)/, '$1.$2');
    if (value.length > 5) value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
    if (value.length > 8) value = value.replace(/\.(\d{3})(\d)/, '.$1/$2');
    if (value.length > 12) value = value.replace(/(\d{4})(\d)/, '$1-$2');

    input.value = value;
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
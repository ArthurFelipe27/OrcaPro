// --- STATE MANAGEMENT ---
let currentItems = [];
let grandTotal = 0;

// --- NAVIGATION ---
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
    if (screenId === 'history') loadHistory();
    if (screenId === 'settings') loadSettings();
}

// --- LOGIC: CREATE BUDGET ---
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
    currentItems.push({ desc, obs, qty, price, total });
    renderItems();

    document.getElementById('item-desc').value = '';
    document.getElementById('item-obs').value = '';
    document.getElementById('item-qty').value = '1';
    document.getElementById('item-price').value = '';
    document.getElementById('item-desc').focus();
}

function removeItem(index) {
    currentItems.splice(index, 1);
    renderItems();
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
            <tr>
                <td>${descHtml}</td>
                <td>${item.qty}</td>
                <td>R$ ${item.price.toFixed(2)}</td>
                <td>R$ ${item.total.toFixed(2)}</td>
                <td><button class="btn btn-danger" style="padding: 5px 10px; font-size: 0.8rem;" onclick="removeItem(${index})">X</button></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    document.getElementById('total-display').innerText = `Total: R$ ${grandTotal.toFixed(2)}`;
}

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
            document.getElementById('client-name').value = '';
            document.getElementById('client-phone').value = '';
            document.getElementById('client-email').value = '';
            document.getElementById('client-address').value = '';
            currentItems = [];
            renderItems();
            navigate('history');
        } else {
            alert('Erro ao salvar: ' + response.message);
        }
    } catch (e) {
        console.error("Erro:", e);
        alert('Erro de conexão com o sistema.');
    }
}

// --- LOGIC: HISTORY & PDF ---
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
            loadHistory(); // Recarrega a lista
            loadStats();   // Atualiza estatísticas
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
            html += `
                <div class="history-item">
                    <div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${item.client}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">
                             #${item.id} • ${item.date} • ${item.items_count} itens
                        </div>
                    </div>
                    <div style="text-align: right; display: flex; align-items: center; gap: 10px;">
                        <div style="font-weight: 700; color: var(--primary); margin-right: 10px;">R$ ${item.total.toFixed(2)}</div>
                        
                        <button class="btn btn-secondary" onclick="generatePDF(${item.id})" title="Gerar PDF">
                            📄
                        </button>
                        
                        <button class="btn btn-danger" onclick="deleteBudget(${item.id})" title="Excluir Orçamento" style="padding: 0.75rem;">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) { console.log(e); }
}

// --- LOGIC: STATS & SETTINGS ---
async function loadStats() {
    try {
        const stats = await window.pywebview.api.get_stats();
        document.getElementById('stat-count').innerText = stats.count;
        document.getElementById('stat-total').innerText = `R$ ${stats.total.toFixed(2)}`;
    } catch (e) { }
}

async function loadSettings() {
    try {
        const settings = await window.pywebview.api.get_settings();
        if (settings) {
            document.getElementById('company-name').value = settings.company || '';
            document.getElementById('footer-text').value = settings.footer || '';
            document.getElementById('company-legal-name').value = settings.legal_name || '';
            document.getElementById('company-address').value = settings.address || '';
            document.getElementById('company-phone').value = settings.phone || '';

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
    const address = document.getElementById('company-address').value;
    const phone = document.getElementById('company-phone').value;
    const footer = document.getElementById('footer-text').value;
    const pdfPath = document.getElementById('pdf-path').value;
    const createSubfolder = document.getElementById('pdf-subfolder').checked;

    try {
        await window.pywebview.api.save_settings({
            company: company,
            legal_name: legalName,
            address: address,
            phone: phone,
            footer: footer,
            pdf_path: pdfPath,
            create_subfolder: createSubfolder
        });
        alert('Configurações salvas!');
    } catch (e) { }
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => loadStats(), 500);
});
# ⚡ OrcaPro - Gerador de Orçamentos

![GitHub repo size](https://img.shields.io/github/repo-size/ArthurFelipe27/OrcaPro?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/count/ArthurFelipe27/OrcaPro?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/ArthurFelipe27/OrcaPro?style=for-the-badge)
![License](https://img.shields.io/github/license/ArthurFelipe27/OrcaPro?style=for-the-badge)

> OrcaPro é uma aplicação Desktop moderna para **criação, gerenciamento e exportação de orçamentos profissionais**, desenvolvida em Python com interface Web integrada. O projeto une backend robusto com frontend elegante para oferecer produtividade e controle financeiro em um único lugar.

---

## ✨ Funcionalidades Principais

* 📊 **Dashboard Interativo**
  Visão geral do negócio com totais de faturamento **Aprovados**, **Pendentes** e **Rejeitados**.

* 📝 **Cadastro de Orçamentos**
  Interface intuitiva para adicionar clientes e itens de serviço com **cálculo automático** de valores.

* 📄 **Gerador de PDF Profissional**
  Exportação automática de orçamentos em PDF com layout moderno utilizando **fpdf2**.

* 🗂️ **Histórico Completo**
  Listagem de orçamentos com filtros visuais por status:
  ✅ Aprovado • ⏳ Pendente • ❌ Rejeitado

* ⚙️ **Configurações da Empresa**
  Personalização de logo, CNPJ e rodapé exibidos automaticamente no PDF.

* 📂 **Gestão de Arquivos**
  PDFs organizados automaticamente em **subpastas por cliente**.

---

## 💻 Pré-requisitos

Antes de começar, verifique se você atende aos seguintes requisitos:

* Python **3.10 ou superior**
* Pip (gerenciador de pacotes do Python)
* Sistema operacional: **Windows, Linux ou macOS**

---

## 🚀 Tecnologias Utilizadas

### 🧩 Backend (Python)

* 🐍 **Python 3.12**
* 🪟 **PyWebView** — Janela desktop nativa e ponte Python ↔ JavaScript
* 📄 **FPDF2** — Geração avançada de arquivos PDF
* 🗄️ **SQLite3** — Banco de dados local (nativo do Python)

### 🎨 Frontend (Web)

* 🧱 **HTML5** — Estrutura semântica (SPA)
* 💅 **CSS3** — Design moderno, responsivo e com variáveis CSS
* ⚡ **JavaScript** — Lógica de interface, DOM e comunicação com a API Python

---

## ⚙️ Instalando o OrcaPro

### 1️⃣ Clone o repositório

```bash
git clone https://github.com/ArthurFelipe27/GeradorDeOrcamentoPython.git
cd GeradorDeOrcamentoPython
```

### 2️⃣ Instale as dependências

```bash
pip install pywebview fpdf2
```

> ⚠️ **Importante:** certifique-se de não ter a biblioteca **PyFPDF** antiga instalada para evitar conflitos.

### 3️⃣ Execute a aplicação

```bash
python main.py
```

A aplicação será aberta em uma janela desktop nativa. O banco de dados `orcamentos.db` será criado automaticamente na primeira execução.

---

## 📂 Estrutura de Pastas

```text
GeradorDeOrcamentoPython/
├── main.py                  # 🧠 Backend: Banco, API e Geração de PDF
├── orcamentos.db            # 🗄️ Banco de Dados (gerado automaticamente)
├── web/                     # 🎨 Frontend
│   ├── index.html           # Estrutura HTML (SPA)
│   ├── style.css            # Estilos e temas
│   └── script.js            # Lógica de interface e API
├── .gitignore               # Arquivos ignorados pelo Git
└── README.md                # Documentação do projeto
```

---

## 📸 Demonstração

### Dashboard

<img width="1074" height="741" alt="Captura de tela 2026-02-05 183427" src="https://github.com/user-attachments/assets/20a7c836-5c38-49a2-9ac8-d6b978632290" />

### PDF Gerado

[> *(Exemplo de PDF exportado pelo sistema)*](https://drive.google.com/file/d/1iAjPwueFYdelkJ9jcBkMwDySTNgM4-Ew/view?usp=sharing)

---

## 🛣️ Funcionalidades da API Interna

A comunicação entre Frontend e Backend ocorre via `window.pywebview.api`.

| Método Python   | Função JS         | Descrição                                |
| --------------- | ----------------- | ---------------------------------------- |
| `save_budget`   | `saveBudget()`    | Salva ou atualiza um orçamento no SQLite |
| `get_history`   | `loadHistory()`   | Retorna a lista de orçamentos            |
| `generate_pdf`  | `generatePDF(id)` | Gera e abre o PDF do orçamento           |
| `update_status` | `setStatus(id)`   | Atualiza o status do orçamento           |
| `get_stats`     | `loadStats()`     | Calcula os dados do dashboard            |

---

## 🧑‍💻 Autor

**Arthur Felipe**  
📧 Email: [arthurfelipedasilvamatosdev@gmail.com](mailto:arthurfelipedasilvamatosdev@gmail.com)  
🌐 GitHub: [ArthurFelipe27](https://github.com/ArthurFelipe27)  

---

## 📝 Licença

Este projeto está licenciado sob a **Licença MIT**.

---

💡 *Projeto desenvolvido para demonstrar o poder da criação de aplicações Desktop modernas utilizando Python em conjunto com Tecnologias Web.*

import webview
import json
import sqlite3
import os
import sys
import platform
import subprocess
import re
from datetime import datetime
from fpdf import FPDF

# Configuração do Banco de Dados
DB_FILE = 'orcamentos.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabela orçamentos
    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            client_email TEXT,
            client_phone TEXT,
            client_address TEXT,
            items TEXT,
            total REAL,
            date_created TEXT
        )
    ''')

    # Tabela configurações
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            company_name TEXT,
            company_legal_name TEXT,
            company_address TEXT,
            company_phone TEXT,
            footer_text TEXT,
            pdf_save_path TEXT,
            pdf_create_subfolder INTEGER
        )
    ''')
    
    # Migrações para garantir compatibilidade com versões anteriores
    migrations = [
        ('settings', 'pdf_save_path', 'TEXT'),
        ('settings', 'pdf_create_subfolder', 'INTEGER'),
        ('settings', 'company_legal_name', 'TEXT'),
        ('settings', 'company_address', 'TEXT'),
        ('settings', 'company_phone', 'TEXT'),
        ('budgets', 'client_email', 'TEXT'),
        ('budgets', 'client_phone', 'TEXT'),
        ('budgets', 'client_address', 'TEXT')
    ]

    for table, col, dtype in migrations:
        try:
            c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {dtype}')
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

def open_file(filepath):
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(filepath)
    else:                                   # linux
        subprocess.call(('xdg-open', filepath))

def sanitize_filename(name):
    """Remove caracteres inválidos para nomes de arquivos/pastas"""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

class ModernPDF(FPDF):
    def __init__(self, company_data, budget_id, date_str):
        super().__init__()
        self.company = company_data
        self.budget_id = budget_id
        self.date_str = date_str
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Aumentar altura do cabeçalho para caber mais informações
        header_height = 50
        
        # Fundo do cabeçalho
        self.set_fill_color(79, 70, 229) # Cor Primária (Indigo)
        self.rect(0, 0, 210, header_height, 'F')
        
        # Texto Empresa (Branco)
        self.set_text_color(255, 255, 255)
        
        # 1. Nome Fantasia (Destaque)
        self.set_font('Helvetica', 'B', 22)
        self.set_xy(10, 8)
        self.cell(0, 10, self.company.get('name', 'Minha Empresa'), 0, 1, 'L')
        
        # 2. Dados da Empresa (Menor)
        self.set_font('Helvetica', '', 9)
        current_y = 18
        line_height = 4.5
        
        if self.company.get('legal_name'):
            self.set_xy(10, current_y)
            self.cell(0, line_height, self.company['legal_name'], 0, 1, 'L')
            current_y += line_height
            
        if self.company.get('address'):
            self.set_xy(10, current_y)
            self.cell(0, line_height, self.company['address'], 0, 1, 'L')
            current_y += line_height
            
        if self.company.get('phone'):
            self.set_xy(10, current_y)
            self.cell(0, line_height, f"Contato: {self.company['phone']}", 0, 1, 'L')

        # 3. Detalhes do Orçamento (Direita)
        self.set_font('Helvetica', '', 10)
        # Reposicionar para o topo direito
        self.set_xy(10, 10)
        self.cell(0, 8, f"Orçamento #{self.budget_id}", 0, 1, 'R')
        self.cell(0, 6, f"Data: {self.date_str}", 0, 1, 'R')
        
        # Espaçamento para o conteúdo não sobrepor
        self.set_y(header_height + 10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

class Api:
    def __init__(self):
        self.window = None

    def select_folder(self):
        if self.window:
            result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                return result[0]
        return None

    def save_budget(self, data):
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            items_json = json.dumps(data['items'])
            
            c.execute('''
                INSERT INTO budgets 
                (client, client_email, client_phone, client_address, items, total, date_created) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (data['client'], data.get('email', ''), data.get('phone', ''), data.get('address', ''), items_json, data['total'], data['date']))
            conn.commit()
            conn.close()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_history(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM budgets')
        rows = c.fetchall()
        results = []
        for row in rows:
            items = json.loads(row['items'])
            results.append({
                'id': row['id'],
                'client': row['client'],
                'total': row['total'],
                'date': row['date_created'],
                'items_count': len(items)
            })
        conn.close()
        return results

    def get_stats(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT COUNT(*), SUM(total) FROM budgets')
        row = c.fetchone()
        conn.close()
        return {'count': row[0] if row[0] else 0, 'total': row[1] if row[1] else 0.0}

    def save_settings(self, data):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT id FROM settings WHERE id=1')
        exists = c.fetchone()
        
        subfolder_int = 1 if data.get('create_subfolder') else 0
        
        params = (
            data['company'], 
            data.get('legal_name', ''),
            data.get('address', ''),
            data.get('phone', ''),
            data['footer'], 
            data.get('pdf_path', ''), 
            subfolder_int
        )

        if exists:
            c.execute('''
                UPDATE settings 
                SET company_name=?, company_legal_name=?, company_address=?, company_phone=?, 
                    footer_text=?, pdf_save_path=?, pdf_create_subfolder=?
                WHERE id=1
            ''', params)
        else:
            c.execute('''
                INSERT INTO settings (company_name, company_legal_name, company_address, company_phone, 
                                      footer_text, pdf_save_path, pdf_create_subfolder, id)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', params)
            
        conn.commit()
        conn.close()
        return {'status': 'ok'}

    def get_settings(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM settings WHERE id=1')
        row = c.fetchone()
        conn.close()
        if row:
            # Helper para evitar KeyErrors em migrações
            def get_val(key, default=''):
                return row[key] if key in row.keys() and row[key] else default
            
            return {
                'company': get_val('company_name'),
                'legal_name': get_val('company_legal_name'),
                'address': get_val('company_address'),
                'phone': get_val('company_phone'),
                'footer': get_val('footer_text'),
                'pdf_path': get_val('pdf_save_path'),
                'create_subfolder': bool(row['pdf_create_subfolder']) if 'pdf_create_subfolder' in row.keys() else False
            }
        return {}

    def generate_pdf(self, budget_id):
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute('SELECT * FROM budgets WHERE id = ?', (budget_id,))
            budget = c.fetchone()
            
            c.execute('SELECT * FROM settings WHERE id = 1')
            settings_row = c.fetchone()
            conn.close()

            if not budget: return {'status': 'error', 'message': 'Orçamento não encontrado'}

            # Processar Configurações
            settings = {}
            if settings_row:
                keys = settings_row.keys()
                settings = {k: settings_row[k] for k in keys}

            company_data = {
                'name': settings.get('company_name', 'Minha Empresa'),
                'legal_name': settings.get('company_legal_name', ''),
                'address': settings.get('company_address', ''),
                'phone': settings.get('company_phone', '')
            }
            
            footer_text = settings.get('footer_text', '')
            save_path = settings.get('pdf_save_path', '')
            if not save_path: save_path = os.path.expanduser("~/Documents")
            
            use_subfolder = bool(settings.get('pdf_create_subfolder', 0))

            if not os.path.exists(save_path): save_path = os.getcwd()

            if use_subfolder:
                safe_client = sanitize_filename(budget['client'])
                save_path = os.path.join(save_path, safe_client)
                if not os.path.exists(save_path): os.makedirs(save_path)

            items = json.loads(budget['items'])

            # --- GERAÇÃO DO PDF ---
            # Passamos o objeto completo da empresa agora
            pdf = ModernPDF(company_data, budget['id'], budget['date_created'])
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # Dados do Cliente
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 8, "Dados do Cliente", 0, 1)
            
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_fill_color(245, 247, 250)
            
            client_info = f"Nome: {budget['client']}\n"
            if budget['client_phone']: client_info += f"Telefone: {budget['client_phone']}\n"
            if budget['client_email']: client_info += f"Email: {budget['client_email']}\n"
            if budget['client_address']: client_info += f"Endereço: {budget['client_address']}"
            
            pdf.multi_cell(0, 6, client_info, border=1, fill=True)
            pdf.ln(5)

            # Tabela Itens
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(230, 230, 230)
            
            w_desc, w_qty, w_unit, w_total = 95, 25, 35, 35
            
            pdf.cell(w_desc, 8, "Descrição / Serviço", 1, 0, 'L', True)
            pdf.cell(w_qty, 8, "Qtd", 1, 0, 'C', True)
            pdf.cell(w_unit, 8, "Unitário", 1, 0, 'R', True)
            pdf.cell(w_total, 8, "Total", 1, 1, 'R', True)
            
            pdf.set_font('Helvetica', '', 10)
            
            fill = False
            for item in items:
                pdf.set_fill_color(250, 250, 250) if fill else pdf.set_fill_color(255, 255, 255)
                
                desc = item['desc']
                if 'obs' in item and item['obs']: desc += f"\n(Obs: {item['obs']})"

                x_before = pdf.get_x()
                y_before = pdf.get_y()
                
                pdf.multi_cell(w_desc, 6, desc, border='LTB', align='L', fill=True)
                
                row_height = pdf.get_y() - y_before
                pdf.set_xy(x_before + w_desc, y_before)
                
                pdf.cell(w_qty, row_height, str(item['qty']), border='RTB', align='C', fill=True)
                pdf.cell(w_unit, row_height, f"R$ {item['price']:.2f}", border='RTB', align='R', fill=True)
                pdf.cell(w_total, row_height, f"R$ {item['total']:.2f}", border='RTB', align='R', fill=True)
                pdf.ln()
                fill = not fill

            # Total
            pdf.ln(5)
            pdf.set_fill_color(79, 70, 229)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 12)
            total_text = f"TOTAL: R$ {budget['total']:.2f}"
            width_total = pdf.get_string_width(total_text) + 20
            pdf.set_x(210 - 10 - width_total)
            pdf.cell(width_total, 10, total_text, 0, 1, 'C', True)

            # Rodapé
            if footer_text:
                pdf.ln(10)
                pdf.set_text_color(100, 100, 100)
                pdf.set_font('Helvetica', '', 9)
                pdf.multi_cell(0, 5, footer_text, 0, 'C')

            # Salvar
            filename = f"Orcamento_{budget['id']}_{sanitize_filename(budget['client'])}.pdf"
            full_path = os.path.join(save_path, filename)
            pdf.output(full_path)
            open_file(full_path)

            return {'status': 'ok', 'file': full_path}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

if __name__ == '__main__':
    init_db()
    api = Api()
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'index.html')
    api.window = webview.create_window('Gerador de Orçamentos PRO', file_path, js_api=api, width=1100, height=800, min_size=(900, 650))
    webview.start(debug=True)
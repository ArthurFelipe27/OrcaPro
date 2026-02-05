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
            company_cnpj TEXT,
            company_address TEXT,
            company_phone TEXT,
            footer_text TEXT,
            pdf_save_path TEXT,
            pdf_create_subfolder INTEGER
        )
    ''')
    
    # Migrações (Adiciona colunas novas automaticamente se não existirem)
    migrations = [
        ('settings', 'pdf_save_path', 'TEXT'),
        ('settings', 'pdf_create_subfolder', 'INTEGER'),
        ('settings', 'company_legal_name', 'TEXT'),
        ('settings', 'company_cnpj', 'TEXT'), # Nova coluna CNPJ
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
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

class ModernPDF(FPDF):
    def __init__(self, company_data, budget, date_str):
        super().__init__()
        self.company = company_data
        self.budget = budget
        self.date_str = date_str
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)

    def header(self):
        # 1. Barra de Acento Superior
        self.set_fill_color(55, 65, 81) # Cinza Chumbo Profissional
        self.rect(0, 0, 210, 5, 'F')
        
        self.ln(10)
        
        # 2. Título do Documento e Numero (Direita)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(220, 220, 220) # Cinza bem claro
        self.cell(0, 10, "ORÇAMENTO", 0, 1, 'R')
        
        self.set_y(25) # Voltar para cima para escrever o resto
        
        # 3. Dados da Empresa (Esquerda) - "DE:"
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', 'B', 14)
        self.cell(100, 7, self.company.get('name', 'Minha Empresa'), 0, 1, 'L')
        
        self.set_font('Helvetica', '', 9)
        self.set_text_color(80, 80, 80)
        
        if self.company.get('legal_name'):
            self.cell(100, 5, self.company['legal_name'], 0, 1, 'L')
            
        # Adicionando CNPJ logo abaixo da razão social
        if self.company.get('cnpj'):
            self.cell(100, 5, f"CNPJ: {self.company['cnpj']}", 0, 1, 'L')
            
        if self.company.get('address'):
            self.cell(100, 5, self.company['address'], 0, 1, 'L')
        if self.company.get('phone'):
            self.cell(100, 5, f"Tel: {self.company['phone']}", 0, 1, 'L')
            
        # 4. Dados do Orçamento (Direita - Abaixo do Titulo)
        y_pos = 38
        self.set_xy(110, y_pos)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(0, 0, 0)
        self.cell(30, 6, "Número:", 0, 0, 'R')
        self.set_font('Helvetica', '', 10)
        self.cell(50, 6, f"#{self.budget['id']:04d}", 0, 1, 'R')
        
        self.set_xy(110, y_pos + 6)
        self.set_font('Helvetica', 'B', 10)
        self.cell(30, 6, "Data:", 0, 0, 'R')
        self.set_font('Helvetica', '', 10)
        self.cell(50, 6, self.date_str, 0, 1, 'R')

        self.ln(15)
        
        # 5. Separador e Dados do Cliente "PARA:"
        self.set_draw_color(200, 200, 200)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)
        
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "PREPARADO PARA:", 0, 1, 'L')
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, self.budget['client'], 0, 1, 'L')
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(80, 80, 80)
        
        client_details = []
        if self.budget['client_email']: client_details.append(self.budget['client_email'])
        if self.budget['client_phone']: client_details.append(self.budget['client_phone'])
        
        if client_details:
            self.cell(0, 5, " | ".join(client_details), 0, 1, 'L')
            
        if self.budget['client_address']:
            self.cell(0, 5, self.budget['client_address'], 0, 1, 'L')
            
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
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

    def delete_budget(self, budget_id):
        """Exclui um orçamento do banco de dados."""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM budgets WHERE id = ?', (budget_id,))
            conn.commit()
            conn.close()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def save_budget(self, data):
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            items_json = json.dumps(data['items'])
            
            # Se vier um ID, atualiza (UPDATE), senão cria novo (INSERT)
            if 'id' in data and data['id']:
                c.execute('''
                    UPDATE budgets 
                    SET client=?, client_email=?, client_phone=?, client_address=?, items=?, total=?, date_created=?
                    WHERE id=?
                ''', (data['client'], data.get('email', ''), data.get('phone', ''), data.get('address', ''), items_json, data['total'], data['date'], data['id']))
            else:
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

    def get_budget_details(self, budget_id):
        """Busca todos os detalhes de um orçamento para edição."""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM budgets WHERE id = ?', (budget_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'client': row['client'],
                'email': row['client_email'],
                'phone': row['client_phone'],
                'address': row['client_address'],
                'items': json.loads(row['items']),
                'total': row['total']
            }
        return None

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
        
        # Parâmetros atualizados com CNPJ
        params = (data['company'], data.get('legal_name', ''), data.get('cnpj', ''), data.get('address', ''), data.get('phone', ''), data['footer'], data.get('pdf_path', ''), subfolder_int)

        if exists:
            c.execute('UPDATE settings SET company_name=?, company_legal_name=?, company_cnpj=?, company_address=?, company_phone=?, footer_text=?, pdf_save_path=?, pdf_create_subfolder=? WHERE id=1', params)
        else:
            c.execute('INSERT INTO settings (company_name, company_legal_name, company_cnpj, company_address, company_phone, footer_text, pdf_save_path, pdf_create_subfolder, id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)', params)
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
            def get_val(key, default=''): return row[key] if key in row.keys() and row[key] else default
            return {
                'company': get_val('company_name'),
                'legal_name': get_val('company_legal_name'),
                'cnpj': get_val('company_cnpj'),
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
            
            # Buscar Orçamento e Settings
            c.execute('SELECT * FROM budgets WHERE id = ?', (budget_id,))
            budget = c.fetchone()
            c.execute('SELECT * FROM settings WHERE id = 1')
            settings_row = c.fetchone()
            conn.close()

            if not budget: return {'status': 'error', 'message': 'Orçamento não encontrado'}

            # Mapear settings
            settings = {k: settings_row[k] for k in settings_row.keys()} if settings_row else {}
            company_data = {
                'name': settings.get('company_name', 'Minha Empresa'),
                'legal_name': settings.get('company_legal_name', ''),
                'cnpj': settings.get('company_cnpj', ''),
                'address': settings.get('company_address', ''),
                'phone': settings.get('company_phone', '')
            }
            
            # Diretório de salvamento
            save_path = settings.get('pdf_save_path', '')
            if not save_path or not os.path.exists(save_path): save_path = os.getcwd() # Fallback

            if bool(settings.get('pdf_create_subfolder', 0)):
                safe_client = sanitize_filename(budget['client'])
                save_path = os.path.join(save_path, safe_client)
                if not os.path.exists(save_path): os.makedirs(save_path)

            items = json.loads(budget['items'])

            # --- CONSTRUÇÃO DO PDF ---
            pdf = ModernPDF(company_data, budget, budget['date_created'])
            pdf.alias_nb_pages()
            pdf.add_page()

            # Espaço extra antes da tabela
            pdf.ln(5)

            # Cabeçalho da Tabela - VISIBILIDADE MELHORADA
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(50, 50, 50)  # Fundo Escuro
            pdf.set_draw_color(50, 50, 50)  # Borda Escura
            pdf.set_text_color(255, 255, 255) # Texto Branco
            
            # Ajustando larguras para A4 (180mm area util)
            w_desc, w_qty, w_unit, w_total = 90, 25, 30, 35
            h_header = 9 # Altura do cabeçalho levemente maior
            
            pdf.cell(w_desc, h_header, "  DESCRIÇÃO / SERVIÇO", 1, 0, 'L', True)
            pdf.cell(w_qty, h_header, "QTD", 1, 0, 'C', True)
            pdf.cell(w_unit, h_header, "UNITÁRIO", 1, 0, 'R', True)
            pdf.cell(w_total, h_header, "TOTAL  ", 1, 1, 'R', True)
            
            # Itens da Tabela
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(220, 220, 220) # Borda cinza clara para as linhas
            
            for i, item in enumerate(items):
                desc = item['desc']
                if 'obs' in item and item['obs']: desc += f"\n(Obs: {item['obs']})"

                # Efeito Zebrado (Linhas alternadas com fundo cinza bem claro)
                fill = (i % 2 == 1)
                if fill:
                    pdf.set_fill_color(248, 248, 248)
                else:
                    pdf.set_fill_color(255, 255, 255)

                # Salvar posições
                x_start = pdf.get_x()
                y_start = pdf.get_y()
                
                # Simular altura da descrição para desenhar o fundo corretamente
                # O '  ' adiciona um pequeno padding visual à esquerda
                pdf.multi_cell(w_desc, 7, "  " + desc, 'L', 'L', fill)
                h_desc = pdf.get_y() - y_start
                
                # Voltar para o topo da linha e desenhar as outras colunas
                pdf.set_xy(x_start + w_desc, y_start)
                
                # Desenhando as células com a mesma altura da descrição e preenchimento
                pdf.cell(w_qty, h_desc, str(item['qty']), 0, 0, 'C', fill)
                pdf.cell(w_unit, h_desc, f"R$ {item['price']:.2f}", 0, 0, 'R', fill)
                pdf.cell(w_total, h_desc, f"R$ {item['total']:.2f}  ", 0, 0, 'R', fill)
                
                # Desenhar linha inferior da linha inteira
                pdf.line(15, y_start + h_desc, 195, y_start + h_desc)
                
                pdf.ln(h_desc) # Avançar linha final

            # --- TOTAL GERAL EM DESTAQUE ---
            pdf.ln(8)
            
            # Verificar se precisa de nova página para o total
            if pdf.get_y() > 250: pdf.add_page()
            
            # Caixa do Total
            x_total = 120
            w_total_box = 195 - x_total
            h_total_box = 12
            
            pdf.set_fill_color(235, 235, 235) # Fundo cinza para destaque
            pdf.set_draw_color(0, 0, 0)       # Borda preta
            pdf.set_line_width(0.3)
            
            pdf.set_x(x_total)
            pdf.rect(x_total, pdf.get_y(), w_total_box, h_total_box, 'DF')
            
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(40, h_total_box, "  TOTAL GERAL", 0, 0, 'L') # Label alinhado à esquerda do box
            
            pdf.set_text_color(0, 0, 0)
            # Valor alinhado à direita do box com padding
            pdf.cell(w_total_box - 40, h_total_box, f"R$ {budget['total']:.2f}  ", 0, 1, 'R')
            
            # Reset de estilos
            pdf.set_line_width(0.2)
            pdf.set_text_color(0, 0, 0)

            # --- RODAPÉ PERSONALIZADO (SEM TÍTULO) ---
            footer_text = settings.get('footer_text', '')
            if footer_text:
                pdf.set_y(-35) # Posição fixa perto do fim
                
                # Linha separadora sutil acima da mensagem
                pdf.set_draw_color(200, 200, 200)
                pdf.line(15, pdf.get_y()-2, 195, pdf.get_y()-2)
                
                # Mensagem centralizada e limpa
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(60, 60, 60)
                pdf.multi_cell(0, 5, footer_text, 0, 'C')

            # Salvar e Abrir
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
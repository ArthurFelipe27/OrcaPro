import webview
import json
import sqlite3
import os
import sys
import platform
import subprocess
import re
import shutil
import tempfile
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

try:
    from PIL import Image
except ImportError:
    print("ERRO CRÍTICO: A biblioteca 'Pillow' é necessária. Instale com: pip install Pillow")
    sys.exit(1)

# ===[ CONFIGURAÇÕES E CONSTANTES ]===

def obter_caminho_app():
    """Retorna o caminho absoluto da aplicação (compatível com PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

ARQUIVO_DB = os.path.join(obter_caminho_app(), 'orcamentos.db')
ARQUIVO_LOGO = os.path.join(obter_caminho_app(), 'logo_empresa.png')

# ===[ GERENCIAMENTO DE BANCO DE DADOS ]===

def inicializar_banco():
    """Cria tabelas e executa migrações se necessário."""
    conexao = sqlite3.connect(ARQUIVO_DB)
    cursor = conexao.cursor()
    
    # Tabela de Orçamentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            cliente_email TEXT,
            cliente_telefone TEXT,
            cliente_endereco TEXT,
            itens TEXT,
            total REAL,
            data_criacao TEXT,
            status TEXT DEFAULT 'PENDENTE'
        )
    ''')

    # Tabela de Configurações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            id INTEGER PRIMARY KEY,
            nome_empresa TEXT,
            razao_social TEXT,
            cnpj TEXT,
            endereco TEXT,
            telefone TEXT,
            texto_rodape TEXT,
            caminho_salvar_pdf TEXT,
            criar_subpasta INTEGER,
            salvar_auto INTEGER DEFAULT 1,
            caminho_logo TEXT,
            pagamento_pix INTEGER DEFAULT 0,
            pagamento_credito INTEGER DEFAULT 0,
            pagamento_debito INTEGER DEFAULT 0,
            pagamento_dinheiro INTEGER DEFAULT 0
        )
    ''')
    
    # Migrações
    migracoes = [
        ('configuracoes', 'caminho_salvar_pdf', 'TEXT'),
        ('configuracoes', 'criar_subpasta', 'INTEGER'),
        ('configuracoes', 'razao_social', 'TEXT'),
        ('configuracoes', 'cnpj', 'TEXT'),
        ('configuracoes', 'endereco', 'TEXT'),
        ('configuracoes', 'telefone', 'TEXT'),
        ('configuracoes', 'salvar_auto', 'INTEGER DEFAULT 1'),
        ('configuracoes', 'caminho_logo', 'TEXT'),
        ('configuracoes', 'pagamento_pix', 'INTEGER DEFAULT 0'),
        ('configuracoes', 'pagamento_credito', 'INTEGER DEFAULT 0'),
        ('configuracoes', 'pagamento_debito', 'INTEGER DEFAULT 0'),
        ('configuracoes', 'pagamento_dinheiro', 'INTEGER DEFAULT 0'),
        ('orcamentos', 'cliente_email', 'TEXT'),
        ('orcamentos', 'cliente_telefone', 'TEXT'),
        ('orcamentos', 'cliente_endereco', 'TEXT'),
        ('orcamentos', 'status', 'TEXT')
    ]

    for tabela, coluna, tipo in migracoes:
        try:
            col_nome = coluna.split(' ')[0]
            cursor.execute(f'ALTER TABLE {tabela} ADD COLUMN {col_nome} {tipo.replace("DEFAULT", "")}')
            if 'DEFAULT' in tipo:
                valor_padrao = tipo.split('DEFAULT')[1].strip()
                cursor.execute(f"UPDATE {tabela} SET {col_nome} = {valor_padrao} WHERE {col_nome} IS NULL")
        except sqlite3.OperationalError:
            pass 
    
    conexao.commit()
    conexao.close()

# ===[ FUNÇÕES AUXILIARES ]===

def formatar_moeda(valor):
    """Formata float para BRL."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_texto(texto):
    """Converte texto para latin-1 para compatibilidade com fontes padrão do FPDF."""
    if not texto: return ""
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

def abrir_arquivo_externo(caminho):
    """Abre o arquivo com o programa padrão do sistema."""
    if platform.system() == 'Darwin':
        subprocess.call(('open', caminho))
    elif platform.system() == 'Windows':
        os.startfile(caminho)
    else:
        subprocess.call(('xdg-open', caminho))

def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos para nomes de arquivo."""
    return re.sub(r'[<>:"/\\|?*]', '', nome).strip()

# ===[ GERAÇÃO DE PDF ]===

class RelatorioPDF(FPDF):
    def __init__(self, dados_empresa, orcamento, data_formatada, metodos_pagamento, texto_rodape=""):
        super().__init__()
        self.empresa = dados_empresa
        self.orcamento = orcamento
        self.data_str = data_formatada
        self.pagamentos = metodos_pagamento
        self.texto_rodape = texto_rodape
        # Margem inferior aumentada para comportar o rodapé estendido com segurança
        self.set_auto_page_break(auto=True, margin=35)
        self.set_margins(15, 15, 15)

    def header(self):
        # Topo decorativo
        self.set_fill_color(55, 65, 81)
        self.rect(0, 0, 210, 5, 'F')
        self.ln(10)
        
        possui_logo = False
        if self.empresa.get('caminho_logo') and os.path.exists(self.empresa.get('caminho_logo')):
            try:
                self.image(self.empresa.get('caminho_logo'), 15, 12, w=30)
                possui_logo = True
            except:
                pass

        pos_texto_x = 50 if possui_logo else 15
        
        # Dados da Empresa
        self.set_xy(pos_texto_x, 15)
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', 'B', 14)
        self.cell(100, 7, limpar_texto(self.empresa.get('nome', 'Minha Empresa')), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_font('Helvetica', '', 9)
        self.set_text_color(80, 80, 80)
        
        if self.empresa.get('razao_social'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, limpar_texto(self.empresa['razao_social']), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        if self.empresa.get('cnpj'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, limpar_texto(f"CNPJ: {self.empresa['cnpj']}"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        if self.empresa.get('endereco'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, limpar_texto(self.empresa['endereco']), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        if self.empresa.get('telefone'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, limpar_texto(f"Tel: {self.empresa['telefone']}"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

        # Título do Documento
        self.set_y(15)
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(200, 200, 200)
        self.cell(0, 10, limpar_texto("ORÇAMENTO"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

        y_pos = 28
        self.set_xy(110, y_pos)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(0, 0, 0)
        self.cell(40, 6, limpar_texto("Número:"), border=0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
        self.set_font('Helvetica', '', 10)
        self.cell(45, 6, limpar_texto(f"#{self.orcamento['id']:04d}"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
        
        self.set_xy(110, y_pos + 6)
        self.set_font('Helvetica', 'B', 10)
        self.cell(40, 6, limpar_texto("Data:"), border=0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
        self.set_font('Helvetica', '', 10)
        self.cell(45, 6, limpar_texto(self.data_str), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

        self.set_y(max(self.get_y(), 50)) 
        self.ln(5)
        
        # Dados do Cliente
        self.set_draw_color(200, 200, 200)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)
        
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, limpar_texto("PREPARADO PARA:"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, limpar_texto(self.orcamento['cliente']), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(80, 80, 80)
        
        detalhes_cliente = []
        if self.orcamento.get('email'): detalhes_cliente.append(self.orcamento['email'])
        if self.orcamento.get('telefone'): detalhes_cliente.append(self.orcamento['telefone'])
        
        if detalhes_cliente:
            self.cell(0, 5, limpar_texto(" | ".join(detalhes_cliente)), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
        if self.orcamento.get('endereco'):
            self.cell(0, 5, limpar_texto(self.orcamento['endereco']), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
        self.ln(8) # Espaço antes do começo da tabela

    def cabecalho_tabela(self):
        """Desenha os cabeçalhos das colunas (Repetido automaticamente em novas páginas)."""
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(50, 50, 50)
        self.set_draw_color(50, 50, 50)
        self.set_text_color(255, 255, 255)
        larguras = [90, 25, 30, 35]
        
        self.cell(larguras[0], 9, limpar_texto("  DESCRIÇÃO / SERVIÇO"), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
        self.cell(larguras[1], 9, limpar_texto("QTD"), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(larguras[2], 9, limpar_texto("UNITÁRIO"), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R', fill=True)
        self.cell(larguras[3], 9, limpar_texto("TOTAL  "), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(0, 0, 0)
        self.set_draw_color(220, 220, 220)

    def footer(self):
        """Rodapé fixo em todas as páginas."""
        # Define a altura base do rodapé baseada na presença do texto extra das configurações
        y_pos = -35 if self.texto_rodape else -25
        self.set_y(y_pos)
        
        # Texto customizado de observação / rodapé
        if self.texto_rodape:
            self.set_draw_color(200, 200, 200)
            self.line(15, self.get_y()-2, 195, self.get_y()-2)
            self.set_font('Helvetica', '', 9)
            self.set_text_color(60, 60, 60)
            self.multi_cell(0, 5, limpar_texto(self.texto_rodape), align='C')
            self.ln(3)

        # Formas de Pagamento
        if self.pagamentos:
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(50, 50, 50)
            self.cell(0, 4, limpar_texto("Formas de Pagamento Aceitas:"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.set_font('Helvetica', '', 8)
            
            texto_metodos = []
            if self.pagamentos.get('pix'): texto_metodos.append("PIX")
            if self.pagamentos.get('credito'): texto_metodos.append("Cartão de Crédito")
            if self.pagamentos.get('debito'): texto_metodos.append("Cartão de Débito")
            if self.pagamentos.get('dinheiro'): texto_metodos.append("Dinheiro")
            
            if texto_metodos:
                texto_final = ", ".join(texto_metodos) + "."
                self.cell(0, 4, limpar_texto(texto_final), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        # Contagem de páginas
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, limpar_texto(f'Página {self.page_no()}/{{nb}}'), border=0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

# ===[ API DO SISTEMA ]===

class InterfaceSistema:
    def __init__(self):
        self.janela = None

    def selecionar_pasta(self):
        if self.janela:
            resultado = self.janela.create_file_dialog(webview.FOLDER_DIALOG)
            if resultado and len(resultado) > 0:
                return resultado[0]
        return None

    def selecionar_logo(self):
        if self.janela:
            tipos_arquivo = ('Imagens (*.png;*.jpg;*.jpeg)', 'Todos os arquivos (*.*)')
            resultado = self.janela.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=tipos_arquivo)
            
            if resultado and len(resultado) > 0:
                caminho_origem = resultado[0]
                try:
                    img = Image.open(caminho_origem).convert("RGBA")
                    dimensao_max = 3300
                    if img.width > dimensao_max or img.height > dimensao_max:
                        img.thumbnail((dimensao_max, dimensao_max), Image.Resampling.LANCZOS)
                    
                    tamanho = max(img.width, img.height)
                    nova_img = Image.new("RGBA", (tamanho, tamanho), (255, 255, 255, 0))
                    nova_img.paste(img, ((tamanho - img.width) // 2, (tamanho - img.height) // 2), img)
                    nova_img.save(ARQUIVO_LOGO, "PNG")
                    return {'status': 'ok', 'caminho': ARQUIVO_LOGO}
                except Exception as e:
                    return {'status': 'erro', 'mensagem': f"Erro ao processar imagem: {str(e)}"}
        return {'status': 'cancelado'}

    def atualizar_status(self, id_orcamento, novo_status):
        try:
            conexao = sqlite3.connect(ARQUIVO_DB)
            cursor = conexao.cursor()
            cursor.execute('UPDATE orcamentos SET status = ? WHERE id = ?', (novo_status, id_orcamento))
            conexao.commit()
            conexao.close()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'erro', 'mensagem': str(e)}

    def excluir_orcamento(self, id_orcamento):
        try:
            conexao = sqlite3.connect(ARQUIVO_DB)
            cursor = conexao.cursor()
            cursor.execute('DELETE FROM orcamentos WHERE id = ?', (id_orcamento,))
            conexao.commit()
            conexao.close()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'erro', 'mensagem': str(e)}

    def salvar_orcamento(self, dados):
        try:
            conexao = sqlite3.connect(ARQUIVO_DB)
            cursor = conexao.cursor()
            itens_json = json.dumps(dados['itens'])
            
            if 'id' in dados and dados['id']:
                cursor.execute('''
                    UPDATE orcamentos 
                    SET cliente=?, cliente_email=?, cliente_telefone=?, cliente_endereco=?, itens=?, total=?, data_criacao=?
                    WHERE id=?
                ''', (dados['cliente'], dados.get('email', ''), dados.get('telefone', ''), dados.get('endereco', ''), itens_json, dados['total'], dados['data'], dados['id']))
            else:
                cursor.execute('''
                    INSERT INTO orcamentos 
                    (cliente, cliente_email, cliente_telefone, cliente_endereco, itens, total, data_criacao, status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDENTE')
                ''', (dados['cliente'], dados.get('email', ''), dados.get('telefone', ''), dados.get('endereco', ''), itens_json, dados['total'], dados['data']))
                
            conexao.commit()
            conexao.close()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'erro', 'mensagem': str(e)}

    def obter_detalhes_orcamento(self, id_orcamento):
        conexao = sqlite3.connect(ARQUIVO_DB)
        conexao.row_factory = sqlite3.Row
        cursor = conexao.cursor()
        cursor.execute('SELECT * FROM orcamentos WHERE id = ?', (id_orcamento,))
        linha = cursor.fetchone()
        conexao.close()
        
        if linha:
            return {
                'id': linha['id'],
                'cliente': linha['cliente'],
                'email': linha['cliente_email'],
                'telefone': linha['cliente_telefone'],
                'endereco': linha['cliente_endereco'],
                'itens': json.loads(linha['itens']),
                'total': linha['total']
            }
        return None

    def obter_historico(self):
        conexao = sqlite3.connect(ARQUIVO_DB)
        conexao.row_factory = sqlite3.Row
        cursor = conexao.cursor()
        cursor.execute('SELECT * FROM orcamentos')
        linhas = cursor.fetchall()
        resultados = []
        for linha in linhas:
            itens = json.loads(linha['itens'])
            resultados.append({
                'id': linha['id'],
                'cliente': linha['cliente'],
                'total': linha['total'],
                'data': linha['data_criacao'],
                'qtd_itens': len(itens),
                'status': linha['status'] or 'PENDENTE'
            })
        conexao.close()
        return resultados

    def obter_estatisticas(self):
        conexao = sqlite3.connect(ARQUIVO_DB)
        cursor = conexao.cursor()
        cursor.execute('SELECT COUNT(*) FROM orcamentos')
        total_geral = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*), SUM(total) FROM orcamentos WHERE status = 'APROVADO'")
        l_aprov = cursor.fetchone()
        cursor.execute("SELECT COUNT(*), SUM(total) FROM orcamentos WHERE status = 'PENDENTE' OR status IS NULL")
        l_pend = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM orcamentos WHERE status = 'REJEITADO'")
        rej_qtd = cursor.fetchone()[0] or 0
        conexao.close()
        return {
            'total_geral': total_geral,
            'aprovados_qtd': l_aprov[0] or 0, 'aprovados_valor': l_aprov[1] or 0.0,
            'pendentes_qtd': l_pend[0] or 0, 'pendentes_valor': l_pend[1] or 0.0,
            'rejeitados_qtd': rej_qtd
        }

    def salvar_configuracoes(self, dados):
        conexao = sqlite3.connect(ARQUIVO_DB)
        cursor = conexao.cursor()
        cursor.execute('SELECT id FROM configuracoes WHERE id=1')
        existe = cursor.fetchone()
        
        parametros = (
            dados['empresa'], dados.get('razao_social', ''), dados.get('cnpj', ''), dados.get('endereco', ''), 
            dados.get('telefone', ''), dados['rodape'], dados.get('caminho_pdf', ''), 
            1 if dados.get('criar_subpasta') else 0, 1 if dados.get('salvar_auto') else 0, 
            dados.get('caminho_logo', ''), 1 if dados.get('pagamento_pix') else 0,
            1 if dados.get('pagamento_credito') else 0, 1 if dados.get('pagamento_debito') else 0,
            1 if dados.get('pagamento_dinheiro') else 0
        )

        if existe:
            cursor.execute('''UPDATE configuracoes SET 
                nome_empresa=?, razao_social=?, cnpj=?, endereco=?, telefone=?, texto_rodape=?, 
                caminho_salvar_pdf=?, criar_subpasta=?, salvar_auto=?, caminho_logo=?, 
                pagamento_pix=?, pagamento_credito=?, pagamento_debito=?, pagamento_dinheiro=? WHERE id=1''', parametros)
        else:
            cursor.execute('''INSERT INTO configuracoes (
                nome_empresa, razao_social, cnpj, endereco, telefone, texto_rodape, 
                caminho_salvar_pdf, criar_subpasta, salvar_auto, caminho_logo, 
                pagamento_pix, pagamento_credito, pagamento_debito, pagamento_dinheiro, id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''', parametros)
        conexao.commit()
        conexao.close()
        return {'status': 'ok'}

    def obter_configuracoes(self):
        conexao = sqlite3.connect(ARQUIVO_DB)
        conexao.row_factory = sqlite3.Row
        cursor = conexao.cursor()
        cursor.execute('SELECT * FROM configuracoes WHERE id=1')
        linha = cursor.fetchone()
        conexao.close()
        if linha:
            return {
                'empresa': linha['nome_empresa'], 'razao_social': linha['razao_social'],
                'cnpj': linha['cnpj'], 'endereco': linha['endereco'], 'telefone': linha['telefone'],
                'rodape': linha['texto_rodape'], 'caminho_pdf': linha['caminho_salvar_pdf'],
                'criar_subpasta': bool(linha['criar_subpasta']), 'salvar_auto': bool(linha['salvar_auto']),
                'caminho_logo': linha['caminho_logo'], 'pagamento_pix': bool(linha['pagamento_pix']),
                'pagamento_credito': bool(linha['pagamento_credito']), 'pagamento_debito': bool(linha['pagamento_debito']),
                'pagamento_dinheiro': bool(linha['pagamento_dinheiro']),
            }
        return {}

    def gerar_pdf(self, id_orcamento):
        try:
            conexao = sqlite3.connect(ARQUIVO_DB)
            conexao.row_factory = sqlite3.Row
            cursor = conexao.cursor()
            cursor.execute('SELECT * FROM orcamentos WHERE id = ?', (id_orcamento,))
            linha_orc = cursor.fetchone()
            cursor.execute('SELECT * FROM configuracoes WHERE id = 1')
            config_linha = cursor.fetchone()
            conexao.close()

            if not linha_orc: return {'status': 'erro', 'mensagem': 'Orçamento não encontrado'}

            orcamento = {
                'id': linha_orc['id'],
                'cliente': linha_orc['cliente'],
                'email': linha_orc['cliente_email'],
                'telefone': linha_orc['cliente_telefone'],
                'endereco': linha_orc['cliente_endereco'],
                'itens': linha_orc['itens'],
                'total': linha_orc['total'],
                'data_criacao': linha_orc['data_criacao']
            }

            config = {k: config_linha[k] for k in config_linha.keys()} if config_linha else {}
            
            dados_empresa = {
                'nome': config.get('nome_empresa', 'Minha Empresa'),
                'razao_social': config.get('razao_social', ''),
                'cnpj': config.get('cnpj', ''),
                'endereco': config.get('endereco', ''),
                'telefone': config.get('telefone', ''),
                'caminho_logo': config.get('caminho_logo', '')
            }

            metodos_pagamento = {
                'pix': bool(config.get('pagamento_pix', 0)),
                'credito': bool(config.get('pagamento_credito', 0)),
                'debito': bool(config.get('pagamento_debito', 0)),
                'dinheiro': bool(config.get('pagamento_dinheiro', 0))
            }
            
            salvar_auto = bool(config.get('salvar_auto', 1))
            caminho_usuario = config.get('caminho_salvar_pdf', '')
            texto_rodape = config.get('texto_rodape', '')
            
            if salvar_auto and caminho_usuario and os.path.exists(caminho_usuario):
                dir_salvamento = caminho_usuario
                if bool(config.get('criar_subpasta', 0)):
                    cliente_seguro = sanitizar_nome_arquivo(orcamento['cliente'])
                    dir_salvamento = os.path.join(dir_salvamento, cliente_seguro)
                    if not os.path.exists(dir_salvamento): os.makedirs(dir_salvamento)
            else:
                dir_salvamento = tempfile.gettempdir()

            itens = json.loads(orcamento['itens'])
            
            # Instancia o PDF com todos os dados preenchidos
            pdf = RelatorioPDF(dados_empresa, orcamento, orcamento['data_criacao'], metodos_pagamento, texto_rodape)
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # Cabeçalho da Tabela pela primeira vez
            pdf.cabecalho_tabela()
            larguras = [90, 25, 30, 35]
            
            for i, item in enumerate(itens):
                desc = item['desc']
                if item.get('obs'): desc += f"\n(Obs: {item['obs']})"
                
                # --- PREVISÃO DE ESPAÇO: Evitar que a tabela quebre no meio do desenho ---
                pdf.set_font('Helvetica', '', 10)
                linhas_texto = desc.split('\n')
                qtd_linhas = 0
                for l in linhas_texto:
                    largura_str = pdf.get_string_width("  " + l)
                    qtd_linhas += max(1, int(largura_str / 85) + 1)
                
                altura_estimada = qtd_linhas * 7
                
                # O PDF FPDF vai até 297mm. Avaliamos até o 240mm por conta do nosso Rodapé Fixo estendido
                if pdf.get_y() + altura_estimada > 240:
                    pdf.add_page() # O FPDF automaticamente puxará o cabeçalho (empresa e cliente)
                    pdf.cabecalho_tabela() # Nós chamamos manualmente as colunas da tabela novamente
                # --------------------------------------------------------------------------

                bg = (i % 2 == 1)
                pdf.set_fill_color(248, 248, 248) if bg else pdf.set_fill_color(255, 255, 255)

                x_ini, y_ini = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(larguras[0], 7, limpar_texto("  " + desc), border='L', align='L', fill=bg)
                h_linha = pdf.get_y() - y_ini
                
                pdf.set_xy(x_ini + larguras[0], y_ini)
                pdf.cell(larguras[1], h_linha, str(item['qtd']), border=0, align='C', fill=bg)
                pdf.cell(larguras[2], h_linha, limpar_texto(formatar_moeda(item['preco'])), border=0, align='R', fill=bg)
                pdf.cell(larguras[3], h_linha, limpar_texto(formatar_moeda(item['total']) + "  "), border=0, align='R', fill=bg)
                
                pdf.line(15, y_ini + h_linha, 195, y_ini + h_linha)
                pdf.set_y(y_ini + h_linha)

            pdf.ln(8)
            
            # Se não houver espaço para mostrar o Total Geral adequadamente, jogue para a próxima pág.
            if pdf.get_y() > 225: 
                pdf.add_page()
            
            # Totais
            pdf.set_fill_color(235, 235, 235)
            pdf.set_draw_color(0, 0, 0)
            pdf.set_x(120)
            pdf.rect(120, pdf.get_y(), 75, 12, 'DF')
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(40, 12, limpar_texto("  TOTAL GERAL"), border=0, align='L')
            pdf.cell(35, 12, limpar_texto(formatar_moeda(orcamento['total']) + "  "), border=0, align='R')
            pdf.ln(15)

            nome_arq = f"Orcamento_{orcamento['id']}_{sanitizar_nome_arquivo(orcamento['cliente'])}.pdf"
            caminho_final = os.path.join(dir_salvamento, nome_arq)
            pdf.output(caminho_final)
            abrir_arquivo_externo(caminho_final)

            return {'status': 'ok', 'arquivo': caminho_final}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'erro', 'mensagem': str(e)}

# ===[ EXECUÇÃO ]===

if __name__ == '__main__':
    inicializar_banco()
    api = InterfaceSistema()
    caminho_html = os.path.join(obter_caminho_app(), 'web', 'index.html')
    api.janela = webview.create_window('OrcaPro', caminho_html, js_api=api, width=1200, height=850)
    webview.start()
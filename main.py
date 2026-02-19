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
    
    # Migrações para garantir compatibilidade com versões anteriores
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
            pass # Coluna já existe
    
    conexao.commit()
    conexao.close()

# ===[ FUNÇÕES AUXILIARES ]===

def formatar_moeda(valor):
    """Formata float para BRL (R$ 1.234,56)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def abrir_arquivo_externo(caminho):
    """Abre o arquivo com o programa padrão do sistema operacional."""
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', caminho))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(caminho)
    else:                                   # Linux
        subprocess.call(('xdg-open', caminho))

def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos para nomes de arquivo."""
    return re.sub(r'[<>:"/\\|?*]', '', nome).strip()

# ===[ GERAÇÃO DE PDF ]===

class RelatorioPDF(FPDF):
    def __init__(self, dados_empresa, orcamento, data_formatada, metodos_pagamento):
        super().__init__()
        self.empresa = dados_empresa
        self.orcamento = orcamento
        self.data_str = data_formatada
        self.pagamentos = metodos_pagamento
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)

    def header(self):
        # Sobrescrita do método header do FPDF
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
        self.cell(100, 7, self.empresa.get('nome', 'Minha Empresa'), 0, 1, 'L')
        
        self.set_font('Helvetica', '', 9)
        self.set_text_color(80, 80, 80)
        
        if self.empresa.get('razao_social'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, self.empresa['razao_social'], 0, 1, 'L')
        if self.empresa.get('cnpj'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, f"CNPJ: {self.empresa['cnpj']}", 0, 1, 'L')
        if self.empresa.get('endereco'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, self.empresa['endereco'], 0, 1, 'L')
        if self.empresa.get('telefone'):
            self.set_x(pos_texto_x)
            self.cell(100, 5, f"Tel: {self.empresa['telefone']}", 0, 1, 'L')

        # Título do Documento
        self.set_y(15)
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(200, 200, 200)
        self.cell(0, 10, "ORÇAMENTO", 0, 1, 'R')

        y_pos = 28
        self.set_xy(110, y_pos)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(0, 0, 0)
        self.cell(40, 6, "Número:", 0, 0, 'R')
        self.set_font('Helvetica', '', 10)
        self.cell(45, 6, f"#{self.orcamento['id']:04d}", 0, 1, 'R')
        
        self.set_xy(110, y_pos + 6)
        self.set_font('Helvetica', 'B', 10)
        self.cell(40, 6, "Data:", 0, 0, 'R')
        self.set_font('Helvetica', '', 10)
        self.cell(45, 6, self.data_str, 0, 1, 'R')

        self.set_y(max(self.get_y(), 50)) 
        self.ln(5)
        
        # Dados do Cliente
        self.set_draw_color(200, 200, 200)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)
        
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "PREPARADO PARA:", 0, 1, 'L')
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, self.orcamento['cliente'], 0, 1, 'L')
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(80, 80, 80)
        
        detalhes_cliente = []
        if self.orcamento['email']: detalhes_cliente.append(self.orcamento['email'])
        if self.orcamento['telefone']: detalhes_cliente.append(self.orcamento['telefone'])
        
        if detalhes_cliente:
            self.cell(0, 5, " | ".join(detalhes_cliente), 0, 1, 'L')
            
        if self.orcamento['endereco']:
            self.cell(0, 5, self.orcamento['endereco'], 0, 1, 'L')
            
        self.ln(10)

    def footer(self):
        # Sobrescrita do método footer do FPDF
        self.set_y(-25)
        
        if self.pagamentos:
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(50, 50, 50)
            self.cell(0, 4, "Formas de Pagamento Aceitas:", 0, 1, 'C')
            self.set_font('Helvetica', '', 8)
            
            texto_metodos = []
            if self.pagamentos.get('pix'): texto_metodos.append("PIX")
            if self.pagamentos.get('credito'): texto_metodos.append("Cartão de Crédito")
            if self.pagamentos.get('debito'): texto_metodos.append("Cartão de Débito")
            if self.pagamentos.get('dinheiro'): texto_metodos.append("Dinheiro")
            
            texto_final = ", ".join(texto_metodos) + "."
            self.cell(0, 4, texto_final, 0, 1, 'C')

        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

# ===[ API DO SISTEMA (PONTE JS <-> PYTHON) ]===

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
        """Abre diálogo, processa e salva a logo em formato quadrado."""
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
                    
                    esquerda = (tamanho - img.width) // 2
                    topo = (tamanho - img.height) // 2
                    nova_img.paste(img, (esquerda, topo), img)
                    
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
            status = linha['status'] if 'status' in linha.keys() and linha['status'] else 'PENDENTE'
            
            resultados.append({
                'id': linha['id'],
                'cliente': linha['cliente'],
                'total': linha['total'],
                'data': linha['data_criacao'],
                'qtd_itens': len(itens),
                'status': status
            })
        conexao.close()
        return resultados

    def obter_estatisticas(self):
        conexao = sqlite3.connect(ARQUIVO_DB)
        cursor = conexao.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM orcamentos')
        total_geral = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*), SUM(total) FROM orcamentos WHERE status = 'APROVADO'")
        linha_aprovados = cursor.fetchone()
        aprovados_qtd = linha_aprovados[0] or 0
        aprovados_valor = linha_aprovados[1] or 0.0
        
        cursor.execute("SELECT COUNT(*), SUM(total) FROM orcamentos WHERE status = 'PENDENTE' OR status IS NULL")
        linha_pendentes = cursor.fetchone()
        pendentes_qtd = linha_pendentes[0] or 0
        pendentes_valor = linha_pendentes[1] or 0.0
        
        cursor.execute("SELECT COUNT(*) FROM orcamentos WHERE status = 'REJEITADO'")
        rejeitados_qtd = cursor.fetchone()[0] or 0
        
        conexao.close()
        return {
            'total_geral': total_geral,
            'aprovados_qtd': aprovados_qtd,
            'aprovados_valor': aprovados_valor,
            'pendentes_qtd': pendentes_qtd,
            'pendentes_valor': pendentes_valor,
            'rejeitados_qtd': rejeitados_qtd
        }

    def salvar_configuracoes(self, dados):
        conexao = sqlite3.connect(ARQUIVO_DB)
        cursor = conexao.cursor()
        cursor.execute('SELECT id FROM configuracoes WHERE id=1')
        existe = cursor.fetchone()
        
        # Converte booleanos para inteiros (0 ou 1)
        subpasta = 1 if dados.get('criar_subpasta') else 0
        salvar_auto = 1 if dados.get('salvar_auto') else 0
        pg_pix = 1 if dados.get('pagamento_pix') else 0
        pg_credito = 1 if dados.get('pagamento_credito') else 0
        pg_debito = 1 if dados.get('pagamento_debito') else 0
        pg_dinheiro = 1 if dados.get('pagamento_dinheiro') else 0
        
        caminho_logo = dados.get('caminho_logo', '')
        
        colunas = """nome_empresa=?, razao_social=?, cnpj=?, endereco=?, 
                  telefone=?, texto_rodape=?, caminho_salvar_pdf=?, criar_subpasta=?,
                  salvar_auto=?, caminho_logo=?, pagamento_pix=?, pagamento_credito=?, 
                  pagamento_debito=?, pagamento_dinheiro=?"""
        
        parametros = (
            dados['empresa'], dados.get('razao_social', ''), dados.get('cnpj', ''), dados.get('endereco', ''), 
            dados.get('telefone', ''), dados['rodape'], dados.get('caminho_pdf', ''), subpasta,
            salvar_auto, caminho_logo, pg_pix, pg_credito, pg_debito, pg_dinheiro
        )

        if existe:
            cursor.execute(f'UPDATE configuracoes SET {colunas} WHERE id=1', parametros)
        else:
            cursor.execute(f'INSERT INTO configuracoes (nome_empresa, razao_social, cnpj, endereco, telefone, texto_rodape, caminho_salvar_pdf, criar_subpasta, salvar_auto, caminho_logo, pagamento_pix, pagamento_credito, pagamento_debito, pagamento_dinheiro, id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)', parametros)
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
            # Função auxiliar para extrair valor com fallback seguro
            def get_val(chave, padrao=''): 
                return linha[chave] if chave in linha.keys() and linha[chave] else padrao
            
            return {
                'empresa': get_val('nome_empresa'),
                'razao_social': get_val('razao_social'),
                'cnpj': get_val('cnpj'),
                'endereco': get_val('endereco'),
                'telefone': get_val('telefone'),
                'rodape': get_val('texto_rodape'),
                'caminho_pdf': get_val('caminho_salvar_pdf'),
                'criar_subpasta': bool(linha['criar_subpasta']) if 'criar_subpasta' in linha.keys() else False,
                'salvar_auto': bool(linha['salvar_auto']) if 'salvar_auto' in linha.keys() else True,
                'caminho_logo': get_val('caminho_logo'),
                'pagamento_pix': bool(linha['pagamento_pix']) if 'pagamento_pix' in linha.keys() else False,
                'pagamento_credito': bool(linha['pagamento_credito']) if 'pagamento_credito' in linha.keys() else False,
                'pagamento_debito': bool(linha['pagamento_debito']) if 'pagamento_debito' in linha.keys() else False,
                'pagamento_dinheiro': bool(linha['pagamento_dinheiro']) if 'pagamento_dinheiro' in linha.keys() else False,
            }
        return {}

    def gerar_pdf(self, id_orcamento):
        try:
            conexao = sqlite3.connect(ARQUIVO_DB)
            conexao.row_factory = sqlite3.Row
            cursor = conexao.cursor()
            
            cursor.execute('SELECT * FROM orcamentos WHERE id = ?', (id_orcamento,))
            orcamento = cursor.fetchone()
            
            cursor.execute('SELECT * FROM configuracoes WHERE id = 1')
            config_linha = cursor.fetchone()
            conexao.close()

            if not orcamento: return {'status': 'erro', 'mensagem': 'Orçamento não encontrado'}

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
            
            # Lógica de Diretório (Automático ou Temporário)
            salvar_auto = bool(config.get('salvar_auto', 1))
            caminho_usuario = config.get('caminho_salvar_pdf', '')
            
            if salvar_auto and caminho_usuario and os.path.exists(caminho_usuario):
                dir_salvamento = caminho_usuario
                if bool(config.get('criar_subpasta', 0)):
                    cliente_seguro = sanitizar_nome_arquivo(orcamento['cliente'])
                    dir_salvamento = os.path.join(dir_salvamento, cliente_seguro)
                    if not os.path.exists(dir_salvamento): 
                        os.makedirs(dir_salvamento)
            else:
                dir_salvamento = tempfile.gettempdir()

            itens = json.loads(orcamento['itens'])

            pdf = RelatorioPDF(dados_empresa, orcamento, orcamento['data_criacao'], metodos_pagamento)
            pdf.alias_nb_pages()
            pdf.add_page()
            pdf.ln(5)

            # Cabeçalho da Tabela
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(50, 50, 50)
            pdf.set_draw_color(50, 50, 50)
            pdf.set_text_color(255, 255, 255)
            
            larguras = [90, 25, 30, 35] # Descrição, Qtd, Unit, Total
            altura_cabecalho = 9
            
            pdf.cell(larguras[0], altura_cabecalho, "  DESCRIÇÃO / SERVIÇO", 1, 0, 'L', True)
            pdf.cell(larguras[1], altura_cabecalho, "QTD", 1, 0, 'C', True)
            pdf.cell(larguras[2], altura_cabecalho, "UNITÁRIO", 1, 0, 'R', True)
            pdf.cell(larguras[3], altura_cabecalho, "TOTAL  ", 1, 1, 'R', True)
            
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(220, 220, 220)
            
            # Renderização dos Itens
            for i, item in enumerate(itens):
                desc = item['desc']
                if 'obs' in item and item['obs']: desc += f"\n(Obs: {item['obs']})"

                preenchimento = (i % 2 == 1)
                if preenchimento: pdf.set_fill_color(248, 248, 248)
                else: pdf.set_fill_color(255, 255, 255)

                x_inicio = pdf.get_x()
                y_inicio = pdf.get_y()
                
                pdf.multi_cell(larguras[0], 7, "  " + desc, 'L', 'L', preenchimento)
                altura_linha = pdf.get_y() - y_inicio
                
                # Posiciona para as próximas colunas
                pdf.set_xy(x_inicio + larguras[0], y_inicio)
                pdf.cell(larguras[1], altura_linha, str(item['qtd']), 0, 0, 'C', preenchimento)
                pdf.cell(larguras[2], altura_linha, formatar_moeda(item['preco']), 0, 0, 'R', preenchimento)
                pdf.cell(larguras[3], altura_linha, formatar_moeda(item['total']) + "  ", 0, 0, 'R', preenchimento)
                
                pdf.line(15, y_inicio + altura_linha, 195, y_inicio + altura_linha)
                pdf.ln(altura_linha)

            pdf.ln(8)
            if pdf.get_y() > 230: pdf.add_page()
            
            # Caixa de Totais
            x_total = 120
            larg_total = 195 - x_total
            altura_total = 12
            
            pdf.set_fill_color(235, 235, 235)
            pdf.set_draw_color(0, 0, 0)
            pdf.set_line_width(0.3)
            
            pdf.set_x(x_total)
            pdf.rect(x_total, pdf.get_y(), larg_total, altura_total, 'DF')
            
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(40, altura_total, "  TOTAL GERAL", 0, 0, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.cell(larg_total - 40, altura_total, formatar_moeda(orcamento['total']) + "  ", 0, 1, 'R')
            
            pdf.set_line_width(0.2)
            pdf.set_text_color(0, 0, 0)

            # Rodapé Personalizado
            texto_rodape = config.get('texto_rodape', '')
            if texto_rodape:
                pdf.set_y(-40)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(15, pdf.get_y()-2, 195, pdf.get_y()-2)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(60, 60, 60)
                pdf.multi_cell(0, 5, texto_rodape, 0, 'C')

            nome_arquivo = f"Orcamento_{orcamento['id']}_{sanitizar_nome_arquivo(orcamento['cliente'])}.pdf"
            caminho_completo = os.path.join(dir_salvamento, nome_arquivo)
            pdf.output(caminho_completo)
            
            abrir_arquivo_externo(caminho_completo)

            return {'status': 'ok', 'arquivo': caminho_completo, 'salvo_automaticamente': salvar_auto}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'erro', 'mensagem': str(e)}

# ===[ EXECUÇÃO PRINCIPAL ]===

if __name__ == '__main__':
    inicializar_banco()
    api = InterfaceSistema()
    caminho_html = os.path.join(obter_caminho_app(), 'web', 'index.html')
    
    api.janela = webview.create_window(
        'OrcaPro - Gerador de Orçamentos', 
        caminho_html, 
        js_api=api, 
        width=1200, 
        height=850, 
        min_size=(900, 650)
    )
    webview.start(debug=False)
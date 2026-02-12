#Interação com Banco de dados
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import sqlite3 

#Banco de dados Usuário/login
def conectar_user_db(): 
    os.makedirs('instance', exist_ok=True)
    return sqlite3.connect('instance/banco.sqlite') #Conexão com banco de dados (Verificar Local do DB)

def criar_tabela_usuarios(): #Usado para criar tabela usuário (Chamada apenas uma vez)
    conn = conectar_user_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def adicionar_usuario(username, password): #Usado para adicionar usuário
    try:
        conn = conectar_user_db()
        cursor = conn.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Erro ao adicionar usuário: {e}")
        return False
    finally:
        conn.close()
    return True

def buscar_usuario(username):
    conn = conectar_user_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario


#Banco de dados estoque
def conectar_estoque_db():
    os.makedirs('database', exist_ok=True)
    return sqlite3.connect('database/estoque.db')

def listar_tabelas(): #Usado para listar as tabelas que aparecerão no Dropdown do dashboard
    conn = conectar_estoque_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tabelas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tabelas

def ler_tabela(tabela): #Mostra a informações da tabela selecionada
    conn = conectar_estoque_db()
    df = pd.read_sql_query(f"SELECT * FROM {tabela} LIMIT 100", conn)
    conn.close()
    return df

def buscar_produto_por_qr(codigo_qr,tabela,coluna):
    conn = conectar_estoque_db()
    conn.row_factory = sqlite3.Row  # Para retornar dicionários
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {tabela} WHERE {coluna} = ?", (codigo_qr,)) #A virgula final transforma em uma tupla de elemento único
    produto = cursor.fetchone()
    conn.close()
    return produto["id"] if produto else None # Retorna o id do produto

def quant_no_bd(id): #Usado para mostrar quantidades de itens com mesmo ID bando de dados 
    conn = conectar_estoque_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM movimentacoes WHERE produto_id = ?;",(id,) 
    )
    quantidade_linhas = cursor.fetchone()[0]
    conn.close()
    return quantidade_linhas or 0

def registrar_movimentacao_por_qr(qr_completo, produto_id, observacao=""):
    with conectar_estoque_db() as conn:
        cursor = conn.cursor()

        # Verifica se já existe entrada
        cursor.execute("""
            SELECT data_movimentacao FROM movimentacoes
            WHERE qr_unico = ? AND tipo = 'entrada'
            ORDER BY data_movimentacao DESC
            LIMIT 1
        """, (qr_completo,))
        ultima_entrada = cursor.fetchone()

        # Verifica se já existe saída
        cursor.execute("""
            SELECT 1 FROM movimentacoes
            WHERE qr_unico = ? AND tipo = 'saida'
        """, (qr_completo,))
        tem_saida = cursor.fetchone() is not None

        agora = datetime.now()

        if not ultima_entrada:
            tipo = "entrada"

        elif ultima_entrada and not tem_saida:
            data_entrada = datetime.strptime(ultima_entrada[0], "%Y-%m-%d %H:%M:%S")

            #Bloqueia saída se não passou 1 minuto da entrada
            if agora - data_entrada < timedelta(minutes=1):
                return {
                    "status": "erro",
                    "mensagem": "Saida bloqueada: leitura muito prixima da entrada (aguarde 1 minuto)."
                }

            tipo = "saida"

        else:
            return {
                "status": "erro",
                "mensagem": "Este item já possui saída registrada."
            }

        try:
            cursor.execute("""
                INSERT INTO movimentacoes (produto_id, tipo, data_movimentacao, observacao, qr_unico)
                VALUES (?, ?, datetime('now','localtime'), ?, ?)
            """, (produto_id, tipo, observacao, qr_completo))
            conn.commit()

        except sqlite3.IntegrityError:
            return {
                "status": "erro",
                "mensagem": "Movimentação duplicada detectada."
            }

        return {
            "status": "ok",
            "tipo_registrado": tipo,
            "qr": qr_completo
        }

        
def buscar_produto_por_codigo_ou_nome(query):
    conn = conectar_estoque_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM produtos 
        WHERE codigo_qr = ? OR nome LIKE ?
        LIMIT 1
    """, (query, f'%{query}%'))
    produto = cursor.fetchone()
    conn.close()
    return produto

#Apesar de não ser Banco de dados botei a função no models
#Serve para mudar o arquivo input da etiqueta. Mudar ela, muda o qrcode impressa na etiqueta 
def mudar_qr(qr_data):
    file = os.getcwd()    
    path = os.path.join(file, "dados_qr/input_qr")
    with open(path, "w") as f:
        f.write(f"{qr_data}")


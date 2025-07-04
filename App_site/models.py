from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import pandas as pd 

#Banco de dados Usuário/login
def conectar_user_db():
    os.makedirs('instance', exist_ok=True)
    return sqlite3.connect('instance/banco.sqlite')

def criar_tabela_usuarios():
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

def adicionar_usuario(username, password):
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

def listar_tabelas():
    conn = conectar_estoque_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tabelas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tabelas

def ler_tabela(tabela):
    conn = conectar_estoque_db()
    df = pd.read_sql_query(f"SELECT * FROM {tabela} LIMIT 100", conn)
    conn.close()
    return df

def buscar_produto_por_qr(codigo_qr):
    conn = conectar_estoque_db()
    conn.row_factory = sqlite3.Row  # Para retornar dicionários
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE codigo_qr = ?", (codigo_qr,))
    produto = cursor.fetchone()
    conn.close()
    return produto

def registrar_movimentacao_no_banco(produto_id, tipo, quantidade, responsavel, observacao, usuario_id):
    conn = conectar_estoque_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO movimentacoes (produto_id, tipo, quantidade, responsavel, observacao, usuario_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (produto_id, tipo, quantidade, responsavel, observacao, usuario_id))
    conn.commit()
    conn.close()
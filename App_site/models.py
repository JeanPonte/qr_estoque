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
    return sqlite3.connect(f'{os.getcwd()}/instance/banco.sqlite') #Conexão com banco de dados (Verificar Local do DB)

def criar_tabela_usuarios(): #Usado para criar tabela usuário (Chamada apenas uma vez)
    conn = conectar_user_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'       
        )
    ''')
    conn.commit()
    conn.close()

def adicionar_usuario(username, password,role='user'): #Usado para adicionar usuário
    try:
        conn = conectar_user_db()
        cursor = conn.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)',
            (username, hashed_password, role)
            )
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
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
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
        agora = datetime.now()

        cursor.execute("""
            SELECT data_movimentacao FROM movimentacoes
            WHERE qr_unico = ? AND tipo = 'entrada'
            ORDER BY data_movimentacao DESC
            LIMIT 1
        """, (qr_completo,))
        ultima_entrada = cursor.fetchone()

        cursor.execute("""
            SELECT 1 FROM movimentacoes
            WHERE qr_unico = ? AND tipo = 'saida'
        """, (qr_completo,))
        tem_saida = cursor.fetchone() is not None

        if not ultima_entrada:
            tipo = "entrada"

        elif not tem_saida:
            data_entrada = datetime.strptime(ultima_entrada[0], "%Y-%m-%d %H:%M:%S")

            if agora - data_entrada < timedelta(minutes=1):
                return {
                    "status": "erro",
                    "mensagem": "Saída bloqueada: aguarde 1 minuto da entrada."
                }

            tipo = "saida"

        else:
            return {
                "status": "erro",
                "mensagem": "Item já possui saída."
            }

        try:
            # garante registro no estoque
            cursor.execute("""
                INSERT OR IGNORE INTO estoque (produto_id, quantidade)
                VALUES (?, 0)
            """, (produto_id,))

            # registra movimentação
            cursor.execute("""
                INSERT INTO movimentacoes (
                    produto_id, tipo, data_movimentacao,
                    observacao, qr_unico, quantidade
                )
                VALUES (?, ?, datetime('now','localtime'), ?, ?, ?)
            """, (produto_id, tipo, observacao, qr_completo, 1))

            if tipo == "entrada":

                cursor.execute("""
                    UPDATE estoque
                    SET quantidade = quantidade + 1
                    WHERE produto_id = ?
                """, (produto_id,))

            else:  # saída

                cursor.execute("""
                    UPDATE estoque
                    SET quantidade = quantidade - 1
                    WHERE produto_id = ? AND quantidade > 0
                """, (produto_id,))

                if cursor.rowcount == 0:
                    conn.rollback()
                    return {
                        "status": "erro",
                        "mensagem": "Estoque insuficiente."
                    }

            conn.commit()

        except sqlite3.IntegrityError:
            conn.rollback()
            return {
                "status": "erro",
                "mensagem": "Movimentação duplicada."
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

TABELAS_PERMITIDAS = {
    "produtos",
    "estoque",
    "movimentacoes",
    "usuarios"
}

def buscar_tabela_db(tabela, termo=""):

    conn = conectar_estoque_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    base_query = f"SELECT * FROM {tabela}"
    valores = []

    if termo:
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = cursor.fetchall()

        colunas_texto = [
            col[1] for col in colunas
            if col[2] and "TEXT" in col[2].upper()
        ]

        if colunas_texto:
            filtros = " OR ".join([f"{col} LIKE ?" for col in colunas_texto])
            base_query += f" WHERE {filtros}"
            valores = [f"%{termo}%"] * len(colunas_texto)

    if tabela == 'pedidos':
        base_query += " ORDER BY data_registro DESC"

    cursor.execute(base_query, valores)

    dados = cursor.fetchall()
    conn.close()
    return dados

def estoque_view():
    conn = conectar_estoque_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * from estoque_legivel;")
    dados = cursor.fetchall()
    
    conn.close()
    return dados

def ordens_view():
    conn = conectar_estoque_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""SELECT * 
                    FROM pedidos 
                    ORDER BY data_registro DESC;""")
    dados = cursor.fetchall()
    
    conn.close()
    return dados


def registrar_pedido(qr, volume, quem, quantidade_editada, status):

    partes = qr.split("|")

    if len(partes) != 7:
        return {"erro": "QR inválido"}

    data_pedido, nPedido , entrega, produto, qtd, comprimento, cliente = partes
    
    try:
        if quantidade_editada:
            quantidade_final = int(quantidade_editada)
        else:
            quantidade_final = int(qtd)
    except ValueError:
        quantidade_final = 0

    volume_final = float(volume) if volume else None

    with conectar_estoque_db() as conn:
        cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM pedidos WHERE numero_pedido LIKE ?",
        (f"{nPedido}%",)
    )

    contador = cursor.fetchone()[0]

    novo_numero = nPedido if contador == 0 else f"{nPedido}/{contador}"

    cursor.execute("""
        INSERT INTO pedidos (
            numero_pedido,
            produto,
            quantidade,
            comprimento,
            volume,
            cliente,
            data_pedido,
            entrega,
            usuario,
            status,
            data_registro
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        novo_numero,
        produto,
        quantidade_final,
        comprimento,
        volume_final,
        cliente,
        data_pedido,
        entrega,
        quem,
        status,
        datetime.now()
    ))

    conn.commit()
    conn.close()

    return {"msg": f"Pedido {novo_numero} registrado com sucesso"}


#Apesar de não ser Banco de dados botei a função no models
#Serve para mudar o arquivo input da etiqueta. Mudar ela, muda o qrcode impressa na etiqueta 
def mudar_qr(qr_data):
    file = os.getcwd()    
    path = os.path.join(file, "dados_qr/input_qr")
    with open(path, "w") as f:
        f.write(f"{qr_data}")


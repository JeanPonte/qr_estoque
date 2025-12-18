import sqlite3
import pandas as pd
from config_privado import fornecedores_abrev, produtos_abreviacoes,categoria_abreviacoes


# Conectar (ou criar) um banco SQLite
conn = sqlite3.connect('database/estoque.db')
cursor = conn.cursor()

# Carregar dados do CSV
tabela = pd.read_csv('database/tabela_ler.csv',sep=';',encoding='latin1')
tabela = tabela.drop_duplicates()
tabela["CATEGORIA"] = tabela["CATEGORIA"].str.upper().str.strip()
tabela["PRODUTO"] = tabela["PRODUTO"].str.upper().str.strip()
tabela["FORNECEDOR"] = tabela["FORNECEDOR"].str.upper().str.strip()

# Inserir os dados
# def adicionar_papel_termico(df):
#     for _, item in df.iterrows(): 
#         descricao = f'{item["PRODUTO"]} de LARGURA {item["LARGURA"]} para bobinas'
#         codigo_qr = f'QR_{item["FORNECEDOR"][0]}{item["LARGURA"]}PTB'.replace(" ", "").upper()
#         categoria = "papel"
#         nome = str(item["PRODUTO"]) + ' ' + str(item["LARGURA"])

#         cursor.execute('''
#             INSERT INTO produtos (nome, categoria, descricao, codigo_qr) VALUES (?, ?, ?, ?)
#         ''', (item["PRODUTO"], categoria, descricao, codigo_qr))

#         # Pegar o ID do produto recém-inserido
#         produto_id = cursor.lastrowid

#         # Inserir detalhes na tabela papel_termico_detalhes
#         cursor.execute('''
#             INSERT INTO papel_termico_detalhes (produto_id, largura, data, fornecedor)
#             VALUES (?, ?, CURRENT_DATE, ?)
#         ''', (produto_id, item['LARGURA'], item['FORNECEDOR']))

def adicionar_baseado_categoria(categoria,tamanho,produto,fornecedor,descricao,codigo_qr):
    cursor.execute('''
        INSERT INTO produtos (nome, categoria, descricao, codigo_qr) VALUES (?, ?, ?, ?)
    ''', (produto, categoria, descricao, codigo_qr))

    produto_id = cursor.lastrowid

    tabelas_validas = {"TUBETE", "RIBBONS", "EMBALAGENS", "PAPEL"}
    if categoria not in tabelas_validas:
        raise ValueError(f"Categoria inválida: {categoria}")

    cursor.execute(f'''
        INSERT INTO {categoria}_detalhes (produto_id, tamanho, data, fornecedor)
        VALUES (?, ?, CURRENT_DATE, ?)
    ''', (produto_id,tamanho,fornecedor))

for i, item in tabela.iterrows():  # <- agora iteramos pelas linhas do DataFrame
    categoria_abrev = categoria_abreviacoes.get(str(item["CATEGORIA"]), "UNK")
    produto_abrev = produtos_abreviacoes.get(str(item["PRODUTO"]), "UNK")
    fornecedor_abrev = fornecedores_abrev.get(str(item["FORNECEDOR"]), "UNK")
    numero_unico = f"{i+1:04}"  # número único com zero padding, ex: 0001
    nome = f"{(item['PRODUTO'])} {item['TAMANHO']}"

    if item["CATEGORIA"] in ["TUBETE", "RIBBONS", "EMBALAGENS"]:
        descricao = f'{item["PRODUTO"]} de tamanho {item["TAMANHO"]}'
        codigo_qr = f'QR{produto_abrev}{numero_unico}{fornecedor_abrev}'.upper().replace(" ", "")
    else:
        descricao = f'{item["CATEGORIA"]} {item["PRODUTO"]} de tamanho {item["TAMANHO"]}'
        codigo_qr = f'QR{categoria_abrev}{produto_abrev}{numero_unico}{fornecedor_abrev}'.upper().replace(" ", "")
        
    adicionar_baseado_categoria(item['CATEGORIA'],item['TAMANHO'],
                                nome,item['FORNECEDOR'],descricao=descricao,codigo_qr=codigo_qr)

# Salvar e fechar
conn.commit()
conn.close()

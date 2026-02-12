import subprocess
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from models import (buscar_usuario, listar_tabelas, ler_tabela,
                     buscar_produto_por_qr, registrar_movimentacao_por_qr,
                     buscar_produto_por_codigo_ou_nome,mudar_qr,quant_no_bd)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['SESSION_PERMANENT'] = False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Você precisa estar logado para acessar esta página.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    session.clear()  # Apaga todos os dados da sessão 
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def homepage():
    user = session.get('user')
    return render_template('homepage.html', user=user)  

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        usuario = buscar_usuario(username)
        if usuario and check_password_hash(usuario[2], password):
            session['user'] = {'id': usuario[0], 'username': usuario[1]}
            session.permanent = False
            return redirect(url_for('homepage'))
        else:
            flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/formulario')
@login_required
def formulario():
    return render_template('form.html')

@app.route('/buscar_produto')
def buscar_produto():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"encontrado": False, "erro": "Parâmetro de busca vazio"})

    produto = buscar_produto_por_codigo_ou_nome(query)
    
    if produto:
        return jsonify({
            "encontrado": True,
            "codigo": produto["codigo_qr"],
            "nome": produto["nome"],
        })
    else:
        return jsonify({"encontrado": False})


@app.route('/carregar_tabela/<tabela>')
@login_required
def carregar_tabela(tabela):
    tabelas_validas = listar_tabelas()
    if tabela not in tabelas_validas:
        return f'<p class="text-danger">Tabela "{tabela}" não encontrada.</p>', 404

    df = ler_tabela(tabela)

    tabela_html = df.to_html(classes='data table table-bordered', index=False)
    return tabela_html

@app.route('/mudar_qrcode/<int:id>/<qr>') #Alterar arquivo input_qr
@login_required
def mudar_input_qr(id,qr):
    quantidade_linhas = int(quant_no_bd(id))
    if quantidade_linhas != 0:
        quantidade_linhas += 1
    qr = str(f'{qr}/{quantidade_linhas}')
    mudar_qr(qr)
    return qr

@app.route('/dashboard')
@login_required
def dashboard():
    tabelas = listar_tabelas()
    return render_template('dashboard.html', tabelas=tabelas)

@app.route('/etiqueta')
@login_required
def etiqueta():
    return render_template('etiquetas.html')

@app.route('/abrir_exe', methods=['POST'])
def abrir_exe():
    bartender = r"C:/Program Files (x86)/Seagull/BarTender Suite/bartend.exe" #Caminho do Bartender 
    arquivo_btw = r"C:/Users/Jnpx_/Desktop/33x22 qrcode.btw" #Caminho da etiqueta
    try:
        subprocess.Popen([bartender, arquivo_btw,'/P','/C=3','/X'],shell=False) #/C é a quantidade de etiquetas impressas 
        return jsonify({"status": "Imprimindo"})
    except Exception as e:
        return jsonify({"status": str(e)}), 500
    
@app.route('/movimentacao')
def movimentacao():
    return render_template('movimentacao.html')

#Retirei o @Login_required de algumas route pois dava erro, não é seguro fazer isso. Vou consertar depois 
@app.route('/movimentacao/<qr>/<id_unico>')
def registrar_movimentacao(qr, id_unico):
    qr_completo = f"{qr}/{id_unico}"

    produto_id = buscar_produto_por_qr(
        qr,
        tabela='produtos',
        coluna='codigo_qr'
    )

    if not produto_id:
        return jsonify({
            "status": "erro",
            "mensagem": "Produto não encontrado"
        }), 404

    resultado = registrar_movimentacao_por_qr(qr_completo, produto_id)

    if resultado["status"] == "erro":
        return jsonify(resultado), 400

    return jsonify(resultado)
    

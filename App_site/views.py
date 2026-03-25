import subprocess
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from models import (buscar_usuario, listar_tabelas, ler_tabela,
                     buscar_produto_por_qr, registrar_movimentacao_por_qr,
                     buscar_produto_por_codigo_ou_nome,mudar_qr,
                     quant_no_bd,buscar_tabela_db,estoque_view,ordens_view,registrar_pedido)
from datetime import datetime
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

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            if 'user' not in session:
                flash('Você precisa estar logado.')
                return redirect(url_for('login'))

            if session['user'].get('role') not in roles:
                return "Acesso negado", 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator

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
            session['user'] = {'id': usuario[0], 'username': usuario[1],'role': usuario[3]}
            session.permanent = False
            role = usuario[3]   
            
            if role == 'producao':
                return redirect(url_for('pedido'))
            elif role == 'escritorio': 
                return redirect(url_for('ordens'))
            else:
                return redirect(url_for('homepage'))
        else:
            flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/formulario')
@role_required('admin','owner')
def formulario():
    return render_template('form.html')

@app.route('/buscar_produto')
@login_required
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

    dados = buscar_tabela_db(tabela)

    return render_template(
        "partials/tabela.html",
        dados=dados,
        tabela=tabela
    )

@app.route('/mudar_qrcode/<int:id>/<qr>') #Alterar arquivo input_qr
@role_required('admin','owner')
@login_required
def mudar_input_qr(id,qr):
    quantidade_linhas = int(quant_no_bd(id))
    if quantidade_linhas != 0:
        quantidade_linhas += 1
    qr = str(f'{qr}/{quantidade_linhas}')
    mudar_qr(qr)
    return qr

@app.route('/dashboard')
@role_required('admin','owner')
def dashboard():
    tabelas = listar_tabelas()
    return render_template('dashboard.html', tabelas=tabelas)

@app.route('/etiqueta')
@role_required('admin','owner')
def etiqueta():
    return render_template('etiquetas.html')

@app.route('/abrir_exe', methods=['POST'])
@role_required('admin','owner')
def abrir_exe():
    bartender = r"C:/Program Files (x86)/Seagull/BarTender Suite/bartend.exe" #Caminho do Bartender 
    arquivo_btw = r"C:/Users/Jnpx_/Desktop/33x22 qrcode.btw" #Caminho da etiqueta
    try:
        subprocess.Popen([bartender, arquivo_btw,'/P','/C=3','/X'],shell=False) #/C é a quantidade de etiquetas impressas 
        return jsonify({"status": "Imprimindo"})
    except Exception as e:
        return jsonify({"status": str(e)}), 500
    
@app.route('/movimentacao')
@role_required('admin','owner')
def movimentacao():
    return render_template('movimentacao.html')

#Retirei o @Login_required de algumas route pois dava erro, não é seguro fazer isso. Vou consertar depois 
@app.route('/movimentacao/<qr>/<id_unico>')
@role_required('admin','owner')
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

@app.route("/buscar_tabela/<tabela>")
def buscar_ajax(tabela):
    termo = request.args.get("termo", "")
    dados = buscar_tabela_db(tabela, termo)

    if tabela == "pedidos":
        return render_template(
            "partials/tabela_pedidos.html",
            pedidos=dados
        )
    else:
        return render_template(
            "partials/tabela.html",
            dados=dados,
            tabela=tabela
        )

@app.route("/estoque")
@role_required('admin','owner')
def estoque():
    dados = estoque_view()
    return render_template("estoque.html", estoque=dados)

@app.route("/pedido")
@login_required
@role_required('producao','owner')
def pedido():
    return render_template("entrada_pedido.html")

@app.route("/ordens")
@login_required
@role_required('escritorio','admin','owner')
def ordens():
    dados = ordens_view()
    return render_template("ordens.html", pedidos=dados)

@app.template_filter('data_br')
def data_br(valor):
    if not valor:
        return '-'

    if isinstance(valor, str):
        for formato in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                valor = datetime.strptime(valor, formato)
                break
            except:
                continue

    if isinstance(valor, datetime):
        return valor.strftime('%d/%m/%Y')

    return valor

@app.template_filter('default_br')
def default_br(valor):
    return valor if valor not in (None, '', 'None') else '-'

# Simulação de banco
usuarios = ["Nicolas", "Domingos", "Josemir"]

@app.route("/obter-nomes", methods=["GET"])
@role_required('admin','owner')
def obter_nomes():
    return jsonify(usuarios)

@app.route("/registrar-pedido", methods=["POST"])
@login_required
def registrar():

    data = request.json

    qr = data.get("qr")
    volume = data.get("volume")
    quem = data.get("quem")
    quantidade = data.get("quantidade")
    status = data.get("status")

    if not qr:
        return jsonify({"msg": "QR não informado"}), 400

    resultado = registrar_pedido(qr, volume, quem, quantidade, status)

    return jsonify(resultado)
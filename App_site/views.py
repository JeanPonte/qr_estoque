from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models import buscar_usuario, listar_tabelas, ler_tabela, buscar_produto_por_qr,registrar_movimentacao_no_banco
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
    session.clear()  # Apaga todos os dados da sessão (inclui cookie de login)
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

@app.route('/registrar_movimentacao', methods=['POST'])
@login_required
def registrar_movimentacao():
    codigo_qr = request.form.get('codigo_qr')
    quantidade = request.form.get('quantidade')
    tipo = request.form.get('tipo')
    responsavel = request.form.get('responsavel')
    observacao = request.form.get('observacao')

    produto = buscar_produto_por_qr(codigo_qr)
    if not produto:
        flash("Produto não encontrado para o QR informado.")
        return redirect(url_for('formulario'))

    produto_id = produto['id']
    usuario_id = session['user']['id']

    registrar_movimentacao_no_banco(produto_id, tipo, quantidade, responsavel, observacao, usuario_id)

    return redirect(url_for('formulario'))

@app.route('/carregar_tabela/<tabela>')
@login_required
def carregar_tabela(tabela):
    tabelas_validas = listar_tabelas()
    if tabela not in tabelas_validas:
        return f'<p class="text-danger">Tabela "{tabela}" não encontrada.</p>', 404

    df = ler_tabela(tabela)

    tabela_html = df.to_html(classes='data table table-bordered', index=False)
    return tabela_html

@app.route('/dashboard')
@login_required
def dashboard():
    tabelas = listar_tabelas()
    return render_template('dashboard.html', tabelas=tabelas)

if __name__ == '__main__':
    app.run(debug=False)

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Redireciona '/' para '/home'
@app.route('/')
def index():
    return redirect(url_for('homepage'))

@app.route('/home')
def homepage():
    return render_template('homepage.html')

@app.route('/formulario')
def formulario():
    return render_template('form.html')

@app.route('/registrar_movimentacao', methods=['POST'])
def registrar_movimentacao():
    codigo_qr = request.form.get('codigo_qr')
    quantidade = request.form.get('quantidade')
    tipo = request.form.get('tipo')
    responsavel = request.form.get('responsavel')
    observacao = request.form.get('observacao')

    # Aqui você pode processar e salvar os dados

    return redirect(url_for('homepage'))

if __name__ == '__main__':
    app.run(debug=True)

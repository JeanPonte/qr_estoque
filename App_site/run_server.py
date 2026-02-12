#Aqui é para rodar servidor
from waitress import serve
from views import app  # onde seu Flask app está criado

serve(app, host="0.0.0.0", port=5000)

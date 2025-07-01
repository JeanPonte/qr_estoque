from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)

#rotas
from views import *
    
if __name__ == '__main__':
    app.run()
    
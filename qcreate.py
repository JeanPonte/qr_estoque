import os

# Caminho da pasta atual
file = os.getcwd()

# Caminho completo do arquivo
path = os.path.join(file, "dados_qr/input_qr.csv")

qr_data = ""

with open(path, "w") as f:
    f.write(f"{qr_data}\n")

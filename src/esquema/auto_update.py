import requests
import time
import random

# URL da API
API_URL = "http://192.168.100.32:5000/update_sst"

# Lista de _id's para atualizar (substitua pelos IDs reais do MongoDB)
ids_to_update = [
    "67803f2b5ff643e5855e739c",
    "67805be7143485b0c67adaa1"
]

# Função para atualizar o campo `sst`
def update_sst(_id, sst):
    try:
        # Corpo da requisição
        payload = {
            "_id": _id,
            "sst": sst
        }

        # Envia a requisição para a API
        response = requests.put(API_URL, json=payload)
        
        # Mostra a resposta da API
        if response.status_code == 200:
            print(f"[SUCESSO] Atualização do ID {_id}: {response.json()}")
        else:
            print(f"[ERRO] Falha ao atualizar o ID {_id}: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"[EXCEÇÃO] Erro ao atualizar o ID {_id}: {str(e)}")

# Loop contínuo para atualização
def automated_updates():
    while True:
        for _id in ids_to_update:
            # Gera um valor aleatório para o campo `sst`
            new_sst = random.randint(100, 200)
            
            # Chama a função de atualização
            update_sst(_id, new_sst)

        # Aguarda 10 segundos antes da próxima execução
        time.sleep(5)

if __name__ == "__main__":
    print("Iniciando atualizações automáticas...")
    automated_updates()

import threading
import time
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Permitir CORS para acesso na web

# Conexão com o MongoDB
mongo_uri = "mongodb://192.168.100.32:32017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.3.3"
client = MongoClient(mongo_uri)
db = client['open5gs']

@app.route('/')
def index():
    return jsonify({"message": "Server Flask com MongoDB conectado com sucesso!"})

def log_to_web(message):
    """Função para enviar logs para a página web via WebSocket."""
    socketio.emit('log_message', {'log': message})

def convert_document(document):
    """
    Função para converter todo ObjectId em um documento para string, incluindo subdocumentos.
    """
    if isinstance(document, dict):  # Se for um dicionário
        return {key: convert_document(value) for key, value in document.items()}
    elif isinstance(document, list):  # Se for uma lista
        return [convert_document(item) for item in document]
    elif isinstance(document, ObjectId):  # Se for ObjectId
        return str(document)
    else:  # Se for qualquer outro tipo
        return document

# BUSCAR VALORES
@app.route('/get', methods=['GET'])
def get_data():
    try:
        imsi = request.args.get('imsi')  # Exemplo: ?imsi=001010000000001
        collection = db['subscribers']
        if imsi:
            documents = collection.find({"imsi": imsi})
        else:
            documents = collection.find()
        data = [convert_document(doc) for doc in documents]
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ATUALIZAR VALORES
@app.route('/update', methods=['PUT'])
def update_data():
    try:
        data = request.get_json()
        if not data or '_id' not in data:
            return jsonify({"error": "Campos obrigatórios faltando"}), 400
        _id = data['_id']
        del data['_id']
        collection = db['subscribers']
        result = collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Nenhum documento encontrado com o _id fornecido"}), 404
        return jsonify({"message": "Dados atualizados com sucesso"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ATUALIZAR SST
@app.route('/update_sst', methods=['PUT'])
def update_sst():
    try:
        data = request.get_json()
        if not data or '_id' not in data or 'sst' not in data:
            return jsonify({"error": "Campos obrigatórios faltando"}), 400
        _id = data['_id']
        new_sst = data['sst']
        collection = db['subscribers']
        document = collection.find_one({"_id": ObjectId(_id)})
        if not document:
            return jsonify({"error": "Nenhum documento encontrado com o _id fornecido"}), 404
        current_sst = document.get("slice", [{}])[0].get("sst", None)
        if current_sst == new_sst:
            log_to_web(f"[SUCESSO] ID {_id}: SST já é {new_sst}. Nenhuma alteração necessária.")
            return jsonify({"message": "Nenhuma alteração necessária"})
        result = collection.update_one({"_id": ObjectId(_id)}, {"$set": {"slice.0.sst": new_sst}})
        if result.modified_count > 0:
            log_to_web(f"[SUCESSO] ID {_id}: SST alterado para {new_sst}.")
            return jsonify({"message": f"SST atualizado para {new_sst}"})
        else:
            log_to_web(f"[ERRO] ID {_id}: Falha ao alterar SST.")
            return jsonify({"error": "Não foi possível atualizar o SST"}), 500
    except Exception as e:
        log_to_web(f"[EXCEÇÃO] Erro no servidor ao processar ID {_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# CRIAÇÃO E DELEÇÃO AUTOMÁTICA DE UE
def create_ue():
    """Cria uma UE no MongoDB a cada 30 segundos."""
    while True:
        ue_data = {
            "imsi": f"IMSI{int(time.time())}",
            "slice": [{"sst": 1}],
            "subscriber_status": 0
        }
        collection = db['subscribers']
        result = collection.insert_one(ue_data)
        ue_id = str(result.inserted_id)
        log_to_web(f"[CRIAÇÃO] UE criada com ID {ue_id} e IMSI {ue_data['imsi']}")
        threading.Thread(target=delete_ue, args=(ue_id,)).start()
        time.sleep(30)

def delete_ue(ue_id):
    """Deleta a UE 40 segundos após sua criação."""
    time.sleep(40)
    collection = db['subscribers']
    result = collection.delete_one({"_id": ObjectId(ue_id)})
    if result.deleted_count > 0:
        log_to_web(f"[DELEÇÃO] UE com ID {ue_id} foi deletada.")
    else:
        log_to_web(f"[ERRO] Falha ao deletar a UE com ID {ue_id}.")

# Inicia a thread de criação de UEs
threading.Thread(target=create_ue, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)

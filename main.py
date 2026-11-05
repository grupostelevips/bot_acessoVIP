import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "COLOQUE_SEU_TOKEN_AQUI")
SUITPAY_CLIENT_ID = os.environ.get("SUITPAY_CLIENT_ID", "COLOQUE_CLIENT_ID_AQUI")
SUITPAY_CLIENT_SECRET = os.environ.get("SUITPAY_CLIENT_SECRET", "COLOQUE_CLIENT_SECRET_AQUI")

@app.route("/", methods=["GET"])
def home():
    return "Bot VIP da SuitPay a funcionar 100% online!", 200

@app.route("/webhook/suitpay", methods=["POST"])
def suitpay_webhook():
    dados = request.json
    print("Notificação recebida da SuitPay:", dados)
    
    status_transacao = dados.get("status")
    if status_transacao in ["PAID", "approved"]:
        pass
        
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

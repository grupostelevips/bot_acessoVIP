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

# --- CHAVES E CONFIGURAÇÕES ---
TELEGRAM_BOT_TOKEN = "9144271229:AAFvv9taDmGTnlI4nHoQ4mAOTJqsJFCOxb4"
PUSHINPAY_API_TOKEN = "73774|DCDTM4JGmuvz4MS4g5vPHy2ucM54PkCeQEu7QA4y49fe526b"
ADMIN_ID = "7008304182"
VIP_GROUP_ID = "-1001921257744"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PUSHINPAY_API_URL = "https://api.pushinpay.com.br/api"
RENDER_URL_FIXA = "bot-acessovip-1.onrender.com"

# Memória de estado dos leads
usuarios = {}

# ==================== MÍDIAS DO FUNIL ====================
# ATENÇÃO: Mantenha aqui os seus IDs MP4 (BAAC...) e as fotos já corrigidas do seu GitHub!
VIDEO_1_NARRADO = "AAMCAQADGQEAAwtq9mYTKIw9CTCi1dG0NNxustTfVwAC6xgAAg_-sEdSJ8QNpaFZRAEAB20AAz0E"
VIDEO_2_LONGO = "AAMCAQADGQEAAwxq9mYTrkycKxZLXqvEFuJMWkzRFAAC7BgAAg_-sEflfXjDBTgZHQEAB20AAz0E"
VIDEO_3_PROMESSA = "AAMCAQADGQEAAw1q9mYTxBErxeiP9uboKRY8gwmCPgAC7RgAAg_-sEct-_T4gH_2WgEAB20AAz0E"
FOTO_OFERTA_NINFA = "AgACAgEAAxkBAAMQavZszfbH4j9T9kElws2YrZIo6S0AAgoNaxsP_rBHs0O4L5Gs34wBAAMCAANzAAM9BA"
IMAGEM_TAXA_SEGURANCA = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAANzAAM9BA"
IMAGEM_TUTORIAL_PIX = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAANzAAM9BA"
# =========================================================

# 1. COPY DA OFERTA PRINCIPAL (Vai como legenda do 2º vídeo no /start)
TEXTO_OFERTA_PRINCIPAL = (
    "🔥 **O MAIOR E MAIS PROIBIDO ACERVO VIP DO BRASIL**\n\n"
    "🔞 **ACESSO COMPLETO: CASADAS, VAZADOS REAIS E CÂMERAS ESCONDIDAS**\n\n"
    "Conteúdos exclusivos que são derrubados da internet em minutos. Sem censura, sem cortes e atualizado todos os dias no sigilo absoluto.\n\n"
    "👇 **TOQUE NO BOTÃO ABAIXO PARA LIBERAR SEU ACESSO:**"
)

# 2. COPY DA SEGUNDA OFERTA (Só aparece DEPOIS que o lead clica no botão da 1ª oferta)
TEXTO_OFERTA_NINFA = (
    "💣 **ESPERA! VOCÊ LIBEROU UMA OFERTA ÚNICA ANTES DE PAGAR...**\n\n"
    "🔞 **O DRIVE SECRETO DA NINFOMANÍACA DE 19 ANOS**\n\n"
    "Conseguimos acesso ao celular de uma modelo novinha que gravou mais de **400 vídeos amadores** dando para desconhecidos no sigilo. Sem censura, sem cortes, chorando e implorando.\n\n"
    "Você pode levar o **VIP Principal + Esse Drive Vitalício** juntos agora mesmo por um valor ridículo.\n\n"
    "👇 **ESCOLHA COMO DESEJA CONTINUAR:**"
)

# 3. COPY DA TAXA DE SEGURANÇA (Só aparece DEPOIS que o Pix de entrada é pago)
TEXTO_TAXA_SEGURANCA = (
    "⚠️ **ÚLTIMA ETAPA OBRIGATÓRIA - DISPOSITIVO NÃO RECONHECIDO!**\n\n"
    "Pagamento de entrada confirmado! Porém, nosso sistema antifraude barrou sua entrada imediata. Para manter o grupo 100% livre de denúncias, exigimos uma ativação de segurança.\n\n"
    "🔄 **O valor de R$ 12,90 é 100% REEMBOLSADO** na sua conta PIX no mesmo instante em que você entrar no grupo.\n\n"
    "👇 **Ative abaixo para receber o link IMEDIATAMENTE:**"
)

# 4. INSTRUÇÕES DO PIX (Enviado sempre antes de qualquer código Pix)
TEXTO_INSTRUCOES_PIX = (
    "✅ **Como pagar e liberar na hora:**\n\n"
    "1️⃣ - Toque no código abaixo para copiar\n"
    "2️⃣ - Abra o app do seu banco\n"
    "3️⃣ - Escolha **PIX Copia e Cola** e finalize.\n\n"
    "⬇️ **COPIE SEU CÓDIGO ABAIXO** ⬇️"
)

# --- FUNÇÕES DE ENVIO ---
def enviar_mensagem(chat_id, texto, markup=None):
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    if markup:
        payload["reply_markup"] = markup
    try:
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        print(f"Erro sendMessage: {e}")

def enviar_video(chat_id, video_id, legenda=None, markup=None):
    payload = {"chat_id": chat_id, "video": video_id, "parse_mode": "Markdown"}
    if legenda:
        payload["caption"] = legenda
    if markup:
        payload["reply_markup"] = markup
    try:
        req = requests.post(f"{TELEGRAM_API_URL}/sendVideo", json=payload, timeout=30)
        if req.status_code != 200:
            print(f"Erro Telegram sendVideo: {req.text}")
    except Exception as e:
        print(f"Exceção sendVideo: {e}")

def enviar_foto(chat_id, foto_id, legenda=None, markup=None):
    payload = {"chat_id": chat_id, "photo": foto_id, "parse_mode": "Markdown"}
    if legenda:
        payload["caption"] = legenda
    if markup:
        payload["reply_markup"] = markup
    try:
        req = requests.post(f"{TELEGRAM_API_URL}/sendPhoto", json=payload, timeout=20)
        if req.status_code != 200:
            print(f"Erro Telegram sendPhoto: {req.text}")
    except Exception as e:
        print(f"Exceção sendPhoto: {e}")

def responder_clique_botao(callback_query_id):
    try:
        requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_query_id}, timeout=5)
    except:
        pass

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
        req = requests.post(f"{PUSHINPAY_API_URL}/pix/cashIn", json=payload, headers=headers, timeout=15)
        if req.status_code in [200, 201]:
            resposta_json = req.json()
            return resposta_json.get("qr_code") or resposta_json.get("pix_copia_e_cola")
        else:
            return f"ERRO_BANCO: Código {req.status_code} - {req.text}"
    except Exception as e:
        return f"ERRO_SISTEMA: {str(e)}"

def entregar_pix_completo(chat_id, valor_reais):
    enviar_mensagem(chat_id, "⏳ *Gerando sua chave PIX criptografada, aguarde...*")
    codigo_pix = gerar_pix_pushinpay(valor_reais, chat_id)
    
    if codigo_pix and not codigo_pix.startswith("ERRO_"):
        enviar_foto(chat_id, IMAGEM_TUTORIAL_PIX)
        time.sleep(0.5)
        enviar_mensagem(chat_id, TEXTO_INSTRUCOES_PIX)
        time.sleep(0.5)
        enviar_mensagem(chat_id, f"`{codigo_pix}`")
    else:
        enviar_mensagem(chat_id, f"❌ *Erro de comunicação com o banco. Tente novamente!*\n`{codigo_pix}`")

# --- MOTOR DE REMARKETING CONTÍNUO ---
def disparar_remarketing(chat_id, tipo_funil, contagem):
    status_atual = usuarios.get(chat_id, {}).get("status")
    
    # Cancela se o lead já avançou de etapa
    if tipo_funil == "ENTRADA" and status_atual != "AGUARDANDO_PAGAMENTO_ENTRADA":
        return
    if tipo_funil == "TAXA" and status_atual != "PENDENTE_TAXA_SEGURANCA":
        return

    if tipo_funil == "ENTRADA":
        markup = {"inline_keyboard": [[{"text": "🔥 Garantir Meu Acesso VIP (R$ 9,90)", "callback_data": "comprar_990"}]]}
        if contagem > 3:
            markup = {"inline_keyboard": [[{"text": "💣 Última Chance com Desconto (R$ 4,90)", "callback_data": "pagar_taxa_490"}]]}
    else:
        markup = {"inline_keyboard": [[{"text": "🔒 Pagar Taxa Reembolsável (R$ 12,90)", "callback_data": "pagar_taxa_1290"}]]}
        if contagem > 3:
            markup = {"inline_keyboard": [[{"text": "🔒 Taxa com Desconto Especial (R$ 4,90)", "callback_data": "pagar_taxa_490"}]]}

    def envio_background():
        if contagem == 0 or (contagem > 0 and contagem % 6 == 0):
            legenda = "🚨 **SEU ACESSO ESTÁ SENDO CANCELADO...**\n\nVocê vai mesmo perder isso? Câmeras escondidas, casadas no sigilo e conteúdos deletados da internet que você não acha em lugar nenhum. Finalize agora!"
            enviar_video(chat_id, VIDEO_3_PROMESSA, legenda, markup)
        elif contagem % 2 != 0:
            legenda = "🔥 **MAIS DE 10.000 VAZADOS REAIS...**\n\nO grupo inteiro já está assistindo e só falta você. Conteúdos brutais que ninguém tem coragem de postar. Você tem poucos minutos!"
            enviar_video(chat_id, VIDEO_1_NARRADO, legenda, markup)
        else:
            legenda = "👀 **VEJA COMO ESSE VÍDEO TERMINOU LÁ NO VIP...**\n\nO final é assustador. Libere o seu acesso agora mesmo, sem enrolação. Aperte o botão e entre!"
            enviar_video(chat_id, VIDEO_2_LONGO, legenda, markup)

    threading.Thread(target=envio_background).start()

    # Intervalos contínuos
    if contagem == 0:
        tempo = timedelta(minutes=5)
    elif contagem == 1:
        tempo = timedelta(minutes=5)
    elif contagem == 2:
        tempo = timedelta(minutes=10)
    elif contagem == 3:
        tempo = timedelta(minutes=25)
    else:
        tempo = timedelta(hours=3)

    scheduler.add_job(
        disparar_remarketing,
        'date',
        run_date=datetime.now() + tempo,
        args=[chat_id, tipo_funil, contagem + 1],
        id=f"rmk_{chat_id}",
        replace_existing=True
    )

# --- ROTAS DA API ---
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
    chat_id = request.args.get("chat_id") or dados.get("external_reference")

    if status in ["paid", "APPROVED", "PAID"] and chat_id:
        chat_id = int(chat_id)
        usuario_status = usuarios.get(chat_id, {}).get("status")

        # ETAPA 4: Pagou a entrada (VIP ou Combo) -> Envia Taxa de Segurança
        if usuario_status == "AGUARDANDO_PAGAMENTO_ENTRADA":
            usuarios[chat_id] = {"status": "PENDENTE_TAXA_SEGURANCA"}
            
            def enviar_taxa():
                enviar_foto(chat_id, IMAGEM_TAXA_SEGURANCA, TEXTO_TAXA_SEGURANCA, {
                    "inline_keyboard": [[{"text": "🔒 Ativar e Reembolsar (R$ 12,90)", "callback_data": "pagar_taxa_1290"}]]
                })
            
            threading.Thread(target=enviar_taxa).start()
            
            scheduler.add_job(
                disparar_remarketing,
                'date',
                run_date=datetime.now() + timedelta(minutes=5),
                args=[chat_id, "TAXA", 0],
                id=f"rmk_{chat_id}",
                replace_existing=True
            )

        # ETAPA 5: Pagou a Taxa de Segurança -> Libera link do Grupo VIP
        elif usuario_status == "PENDENTE_TAXA_SEGURANCA":
            usuarios[chat_id] = {"status": "VIP_LIBERADO"}
            try:
                res_convite = requests.post(
                    f"{TELEGRAM_API_URL}/createChatInviteLink",
                    json={"chat_id": VIP_GROUP_ID, "member_limit": 1}
                ).json()
                link = res_convite.get("result", {}).get("invite_link", "LINK_MANUAL_AQUI")
            except:
                link = "LINK_MANUAL_AQUI"
            
            enviar_mensagem(chat_id, f"🎉 **ACESSO VALIDADO!**\n\nBem-vindo ao submundo. Entre agora:\n👑 [ACESSAR VIP AQUI]({link})")

    return {"status": "ok"}, 200

@app.route(f"/webhook/telegram/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)
    if not update:
        return {"status": "ok"}, 200
    
    # ETAPA 1: /start -> Vídeo 1 (sem legenda) -> Vídeo 2 (com oferta principal + botão)
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        texto = update["message"].get("text", "")

        if texto.startswith("/start"):
            usuarios[chat_id] = {"status": "AGUARDANDO_PAGAMENTO_ENTRADA"}
            
            def fluxo_inicial():
                # 1º Vídeo: Narrado e SEM legenda
                enviar_video(chat_id, VIDEO_1_NARRADO)
                time.sleep(2)
                
                # 2º Vídeo: Longo COM legenda da oferta principal e o botão
                markup_principal = {
                    "inline_keyboard": [
                        [{"text": "🔥 QUERO ENTRAR NO VIP AGORA", "callback_data": "abrir_oferta_ninfa"}]
                    ]
                }
                enviar_video(chat_id, VIDEO_2_LONGO, TEXTO_OFERTA_PRINCIPAL, markup_principal)
            
            threading.Thread(target=fluxo_inicial).start()
            
            scheduler.add_job(
                disparar_remarketing,
                'date',
                run_date=datetime.now() + timedelta(minutes=5),
                args=[chat_id, "ENTRADA", 0],
                id=f"rmk_{chat_id}",
                replace_existing=True
            )

    # CLIQUES NOS BOTÕES
    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        botao = query["data"]
        responder_clique_botao(query["id"])

        # ETAPA 2: Apertou o botão da 1ª oferta -> Mostra a 2ª oferta (Ninfa) com 2 botões separados
        if botao == "abrir_oferta_ninfa":
            def enviar_segunda_oferta():
                markup_ninfa = {
                    "inline_keyboard": [
                        [{"text": "✅ VIP + Drive da Ninfa (R$ 14,89)", "callback_data": "comprar_1489"}],
                        [{"text": "❌ Apenas o VIP Principal (R$ 9,90)", "callback_data": "comprar_990"}]
                    ]
                }
                enviar_foto(chat_id, FOTO_OFERTA_NINFA, TEXTO_OFERTA_NINFA, markup_ninfa)
            
            threading.Thread(target=enviar_segunda_oferta).start()

        # ETAPA 3: Escolheu uma das opções (ou clicou em botão de taxa/remarketing) -> Envia Tutorial + Pix
        else:
            valores = {
                "comprar_1489": "14.89",
                "comprar_990": "9.90",
                "pagar_taxa_1290": "12.90",
                "pagar_taxa_490": "4.90"
            }
            if botao in valores:
                threading.Thread(target=entregar_pix_completo, args=(chat_id, valores[botao])).start()

    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

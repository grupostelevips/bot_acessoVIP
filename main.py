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

# Coloque seu @username do Telegram SEM o @ 
USUARIO_SUPORTE = "suporte_playbox"
LINK_SUPORTE = f"https://t.me/{USUARIO_SUPORTE.replace('@', '').strip()}"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PUSHINPAY_API_URL = "https://api.pushinpay.com.br/api"
RENDER_URL_FIXA = "bot-acessovip-3.onrender.com"

# Memória de estado dos leads e controle de transações já liberadas
usuarios = {}
transacoes_processadas = set()

# ==================== MÍDIAS DO FUNIL ====================
# Mantenha aqui os seus IDs MP4 (BAAC...) já corrigidos no seu GitHub!
VIDEO_1_NARRADO = "BAACAgEAAxkBAANsave8MCzTRAAB-Jh1L1XMHd-yzFObAALSCAACoWXAR5NYoZrWsqowPQQ"
VIDEO_2_LONGO = "BAACAgEAAxkBAANtave8XRVU7iwp87WgDcnbNobQqPsAAtQIAAKhZcBHvE_GplCivNM9BA"
VIDEO_3_PROMESSA = "BAACAgEAAxkBAANuave8pAc0LOXei2ck23ittY0H0h8AAtYIAAKhZcBHaTUVWtRpEEo9BA"
FOTO_OFERTA_NINFA = "AgACAgEAAxkBAAMQavZszfbH4j9T9kElws2YrZIo6S0AAgoNaxsP_rBHs0O4L5Gs34wBAAMCAAN5AAM9BA"
IMAGEM_TAXA_SEGURANCA = "AgACAgEAAxkBAAMRavZuBLMuYaDGOSHUpHPh7j9wKPoAAgsNaxsP_rBH1CMV70aesl8BAAMCAAN5AAM9BA"
IMAGEM_TUTORIAL_PIX = "AgACAgEAAxkBAAMKavY_R7x3Ne3C6FP32bk3fDp6QikAAt8MaxsP_rBHRmsJSu060kIBAAMCAAN4AAM9BA"
# =========================================================

# 1. COPY DA OFERTA PRINCIPAL (Legenda do 2º vídeo no /start)
TEXTO_OFERTA_PRINCIPAL = (
    "🔥 **O ACERVO MAIS PROIBIDO E EXCLUSIVO DO BRASIL**\n\n"
    "Você acabou de ver apenas 1% do que rola lá dentro. No **VIP Oficial**, você tem acesso imediato e vitalício a:\n\n"
    "🔞 **Casadas no sigilo absoluto**\n"
    "📸 **Vazados reais e flagras de câmeras escondidas**\n"
    "📂 **Arquivos deletados da internet que não duram 5 minutos no ar**\n"
    "🔄 **Atualizações diárias sem mensalidade**\n\n"
    "⚠️ *As vagas com valor promocional encerram assim que o grupo atingir o limite diário.*\n\n"
    "👇 **TOQUE NO BOTÃO ABAIXO PARA GARANTIR SUA VAGA AGORA:**"
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

# 4. INSTRUÇÕES DO PIX
TEXTO_INSTRUCOES_PIX = (
    "✅ **Como pagar e liberar na hora:**\n\n"
    "1️⃣ - Toque no código abaixo para copiar\n"
    "2️⃣ - Abra o app do seu banco\n"
    "3️⃣ - Escolha **PIX Copia e Cola** e finalize.\n\n"
    "⬇️ **COPIE SEU CÓDIGO ABAIXO** ⬇️"
)


# --- FUNÇÕES DE ENVIO TELEGRAM ---
def enviar_mensagem(chat_id, texto, markup=None):
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    if markup:
        payload["reply_markup"] = markup
    try:
        req = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=15)
        if req.status_code != 200:
            print(f"Erro sendMessage ({req.status_code}): {req.text}")
            # Fallback 1: tenta sem Markdown mantendo os botões
            payload_sem_md = {"chat_id": chat_id, "text": texto}
            if markup:
                payload_sem_md["reply_markup"] = markup
            req2 = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload_sem_md, timeout=15)
            if req2.status_code != 200:
                # Fallback 2: garante entrega do texto/código mesmo se algum botão falhar
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": texto}, timeout=15)
    except Exception as e:
        print(f"Exceção sendMessage: {e}")


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
    except Exception:
        pass


# --- INTEGRAÇÃO PUSHIN PAY (GERAR E CONSULTAR) ---
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
            codigo = resposta_json.get("qr_code") or resposta_json.get("pix_copia_e_cola")
            tx_id = resposta_json.get("id")
            return codigo, tx_id, None
        else:
            return None, None, f"Código {req.status_code} - {req.text}"
    except Exception as e:
        return None, None, str(e)


def consultar_pagamento_pushinpay(tx_id):
    if not tx_id:
        return False
    headers = {
        "Authorization": f"Bearer {PUSHINPAY_API_TOKEN}",
        "Accept": "application/json"
    }
    for rota in [f"{PUSHINPAY_API_URL}/transactions/{tx_id}", f"{PUSHINPAY_API_URL}/transaction/{tx_id}"]:
        try:
            req = requests.get(rota, headers=headers, timeout=15)
            if req.status_code == 200:
                dados = req.json()
                if isinstance(dados.get("data"), dict):
                    dados = dados["data"]
                status = str(dados.get("status", "")).lower()
                if status in ["paid", "approved", "concluded", "settled"]:
                    return True
                return False
        except Exception as e:
            print(f"Erro ao consultar {rota}: {e}")
    return False


# --- AVANÇO DE ETAPA APÓS PAGAMENTO CONFIRMADO ---
def processar_pagamento_aprovado(chat_id, tx_id=None):
    chat_id = int(chat_id)

    if tx_id:
        tx_norm = str(tx_id).lower()
        if tx_norm in transacoes_processadas:
            return True
        transacoes_processadas.add(tx_norm)

    user_info = usuarios.setdefault(chat_id, {"status": "AGUARDANDO_PAGAMENTO_ENTRADA"})
    usuario_status = user_info.get("status")

    if usuario_status in [None, "INICIO_SEM_CLIQUE", "VENDO_OFERTA_NINFA", "AGUARDANDO_PAGAMENTO_ENTRADA"]:
        usuarios[chat_id]["status"] = "PENDENTE_TAXA_SEGURANCA"
        usuarios[chat_id]["tx_id"] = None

        def enviar_taxa():
            enviar_foto(chat_id, IMAGEM_TAXA_SEGURANCA, TEXTO_TAXA_SEGURANCA, {
                "inline_keyboard": [
                    [{"text": "🔒 Ativar e Reembolsar (R$ 12,90)", "callback_data": "pagar_taxa_1290"}],
                    [{"text": "💬 Suporte", "url": LINK_SUPORTE}]
                ]
            })

        threading.Thread(target=enviar_taxa).start()
        agendar_remarketing(chat_id, "TAXA", 0)
        return True

    elif usuario_status == "PENDENTE_TAXA_SEGURANCA":
        usuarios[chat_id]["status"] = "VIP_LIBERADO"
        usuarios[chat_id]["tx_id"] = None

        try:
            res_convite = requests.post(
                f"{TELEGRAM_API_URL}/createChatInviteLink",
                json={"chat_id": VIP_GROUP_ID, "member_limit": 1},
                timeout=15
            ).json()
            link = res_convite.get("result", {}).get("invite_link", "LINK_MANUAL_AQUI")
        except Exception:
            link = "LINK_MANUAL_AQUI"

        enviar_mensagem(
            chat_id,
            f"🎉 **ACESSO VALIDADO COM SUCESSO!**\n\nBem-vindo ao VIP. Seu link exclusivo de entrada única está liberado:\n👑 [CLIQUE AQUI PARA ENTRAR NO VIP]({link})"
        )
        return True

    return False


# --- ENTREGA DO PIX + REINÍCIO DO REMARKETING COM VÍDEO 3 ---
def entregar_pix_completo(chat_id, valor_reais):
    enviar_mensagem(chat_id, "⏳ *Gerando sua chave PIX criptografada, aguarde...*")
    codigo_pix, tx_id, erro = gerar_pix_pushinpay(valor_reais, chat_id)

    if codigo_pix:
        user_info = usuarios.setdefault(chat_id, {})
        user_info["tx_id"] = tx_id

        if user_info.get("status") != "PENDENTE_TAXA_SEGURANCA":
            user_info["status"] = "AGUARDANDO_PAGAMENTO_ENTRADA"

        enviar_foto(chat_id, IMAGEM_TUTORIAL_PIX)
        time.sleep(0.5)
        enviar_mensagem(chat_id, TEXTO_INSTRUCOES_PIX)
        time.sleep(0.5)

        markup_pix = {
            "inline_keyboard": [
                [{"text": "✅ Confirmar Pagamento", "callback_data": "verificar_pagamento"}],
                [{"text": "💬 Suporte", "url": LINK_SUPORTE}]
            ]
        }
        enviar_mensagem(chat_id, f"`{codigo_pix}`", markup_pix)

        # Reinicia o remarketing do zero começando pelo Vídeo 3 após 4 minutos
        etapa_atual = "TAXA" if user_info.get("status") == "PENDENTE_TAXA_SEGURANCA" else "ENTRADA"
        agendar_remarketing(chat_id, etapa_atual, 0)
    else:
        enviar_mensagem(chat_id, f"❌ *Erro de comunicação com o banco. Tente novamente!*\n`{erro}`")


# --- MOTOR DE REMARKETING INFINITO ---
def agendar_remarketing(chat_id, tipo_funil, contagem):
    # Primeiro remarketing em 4 minutos, depois segue a sequência normal
    if contagem == 0:
        tempo = timedelta(minutes=4)
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
        args=[chat_id, tipo_funil, contagem],
        id=f"rmk_{chat_id}",
        replace_existing=True
    )


def disparar_remarketing(chat_id, tipo_funil, contagem):
    status_atual = usuarios.get(chat_id, {}).get("status")

    if status_atual != tipo_funil:
        return

    def envio_background():
        # ETAPA 1: Deu /start e não clicou no botão da 1ª oferta
        # 1º remarketing (contagem 0) = Vídeo 3 | Próximos = sequência Vídeo 1 -> Vídeo 3 -> Vídeo 1 -> Vídeo 3...
        if tipo_funil == "INICIO_SEM_CLIQUE":
            markup_inicio = {
                "inline_keyboard": [
                    [{"text": "🔥 QUERO ENTRAR NO VIP AGORA", "callback_data": "abrir_oferta_ninfa"}]
                ]
            }
            if contagem % 2 == 0:
                legenda = "🚨 **SUA VAGA NO VIP ESTÁ PRESTES A EXPIRAR!**\n\nNão perca o acesso aos conteúdos mais exclusivos e proibidos da internet. Toque abaixo antes que o link feche!\n\n👇 **Garanta seu acesso agora:**"
                enviar_video(chat_id, VIDEO_3_PROMESSA, legenda, markup_inicio)
            else:
                legenda = "🔥 **O GRUPO VIP ESTÁ RECEBENDO NOVOS VÍDEOS AGORA!**\n\nCasadas no sigilo, câmeras escondidas e vazados reais sem censura.\n\n👇 **Toque abaixo para entrar:**"
                enviar_video(chat_id, VIDEO_1_NARRADO, legenda, markup_inicio)

        # ETAPA 2: Abriu a 2ª oferta (Ninfa) e não gerou Pix -> Reenvia Foto da Ninfa + 2 botões
        elif tipo_funil == "VENDO_OFERTA_NINFA":
            markup_ninfa = {
                "inline_keyboard": [
                    [{"text": "✅ VIP + Drive da Ninfa (R$ 14,89)", "callback_data": "comprar_1489"}],
                    [{"text": "❌ Apenas o VIP Principal (R$ 9,90)", "callback_data": "comprar_990"}]
                ]
            }
            legenda_ninfa = (
                "🔞 **SUA OFERTA DO DRIVE DA NINFA DE 19 ANOS VAI EXPIRAR!**\n\n"
                "Mais de **400 vídeos amadores sem censura** + acesso vitalício ao VIP Principal por um valor simbólico.\n\n"
                "👇 **Escolha seu pacote agora:**"
            )
            enviar_foto(chat_id, FOTO_OFERTA_NINFA, legenda_ninfa, markup_ninfa)

        # ETAPA 3: Gerou Pix da Entrada e não pagou -> Reinicia com Vídeo 3 e alterna 3 -> 1 -> 2
        elif tipo_funil == "ENTRADA":
            if contagem > 3:
                markup = {"inline_keyboard": [[{"text": "💣 Última Chance com Desconto (R$ 4,90)", "callback_data": "pagar_taxa_490"}]]}
            else:
                markup = {"inline_keyboard": [[{"text": "🔥 Gerar Novo PIX - VIP (R$ 9,90)", "callback_data": "comprar_990"}]]}

            ciclo = contagem % 3
            if ciclo == 0:
                legenda = "🚨 **SEU ACESSO ESTÁ SENDO CANCELADO...**\n\nVocê vai mesmo perder isso? Câmeras escondidas, casadas no sigilo e conteúdos deletados da internet que você não acha em lugar nenhum. Finalize agora!"
                enviar_video(chat_id, VIDEO_3_PROMESSA, legenda, markup)
            elif ciclo == 1:
                legenda = "🔥 **MAIS DE 10.000 VAZADOS REAIS...**\n\nO grupo inteiro já está assistindo e só falta você. Conteúdos brutais que ninguém tem coragem de postar. Você tem poucos minutos!"
                enviar_video(chat_id, VIDEO_1_NARRADO, legenda, markup)
            else:
                legenda = "👀 **VEJA COMO ESSE VÍDEO TERMINOU LÁ NO VIP...**\n\nO final é assustador. Libere o seu acesso agora mesmo, sem enrolação. Aperte o botão e entre!"
                enviar_video(chat_id, VIDEO_2_LONGO, legenda, markup)

        # ETAPA 4: Pagou entrada, mas não pagou a Taxa de Segurança -> Reinicia com Vídeo 3 e alterna 3 -> 1 -> 2
        elif tipo_funil == "TAXA":
            if contagem > 3:
                markup = {"inline_keyboard": [[{"text": "🔒 Taxa com Desconto Especial (R$ 4,90)", "callback_data": "pagar_taxa_490"}]]}
            else:
                markup = {"inline_keyboard": [[{"text": "🔒 Pagar Taxa Reembolsável (R$ 12,90)", "callback_data": "pagar_taxa_1290"}]]}

            ciclo = contagem % 3
            if ciclo == 0:
                legenda = "⚠️ **SUA ENTRADA NO VIP ESTÁ BLOQUEADA AGUARDANDO ATIVAÇÃO!**\n\nConclua a ativação de segurança (100% reembolsada no seu PIX assim que entrar) para receber o link do grupo agora!"
                enviar_video(chat_id, VIDEO_3_PROMESSA, legenda, markup)
            elif ciclo == 1:
                legenda = "🔥 **SEU ACESSO JÁ ESTÁ PAGO, SÓ FALTA LIBERAR O LINK!**\n\nAtive seu dispositivo agora mesmo para entrar imediatamente no grupo VIP."
                enviar_video(chat_id, VIDEO_1_NARRADO, legenda, markup)
            else:
                legenda = "⏳ **ÚLTIMO AVISO ANTES DO CANCELAMENTO DO SEU ACESSO!**\n\nFinalize a verificação reembolsável abaixo e entre agora."
                enviar_video(chat_id, VIDEO_2_LONGO, legenda, markup)

    threading.Thread(target=envio_background).start()
    agendar_remarketing(chat_id, tipo_funil, contagem + 1)


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
    dados = request.get_json(force=True, silent=True)
    if not dados:
        dados = request.form.to_dict() if request.form else {}

    print(f"Webhook PushinPay | Args: {dict(request.args)} | Body: {dados}")

    if not dados and not request.args:
        return {"status": "Webhook ativo!"}, 200

    status_bruto = dados.get("status") or (dados.get("data", {}).get("status") if isinstance(dados.get("data"), dict) else "")
    status = str(status_bruto).lower()

    tx_id = dados.get("id") or (dados.get("data", {}).get("id") if isinstance(dados.get("data"), dict) else None)
    chat_id = request.args.get("chat_id") or dados.get("external_reference")

    if not chat_id and tx_id:
        tx_norm = str(tx_id).lower()
        for cid, info in usuarios.items():
            if str(info.get("tx_id", "")).lower() == tx_norm:
                chat_id = cid
                break

    if status in ["paid", "approved", "concluded", "settled"] and chat_id:
        processar_pagamento_aprovado(chat_id, tx_id)

    return {"status": "ok"}, 200


@app.route(f"/webhook/telegram/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)
    if not update:
        return {"status": "ok"}, 200

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        texto = update["message"].get("text", "")

        if texto.startswith("/start"):
            usuarios[chat_id] = {"status": "INICIO_SEM_CLIQUE", "tx_id": None}

            def fluxo_inicial():
                enviar_video(chat_id, VIDEO_1_NARRADO)
                time.sleep(2)

                markup_principal = {
                    "inline_keyboard": [
                        [{"text": "🔥 QUERO ENTRAR NO VIP AGORA", "callback_data": "abrir_oferta_ninfa"}]
                    ]
                }
                enviar_video(chat_id, VIDEO_2_LONGO, TEXTO_OFERTA_PRINCIPAL, markup_principal)

            threading.Thread(target=fluxo_inicial).start()
            agendar_remarketing(chat_id, "INICIO_SEM_CLIQUE", 0)

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        botao = query["data"]

        if botao == "abrir_oferta_ninfa":
            responder_clique_botao(query["id"])
            usuarios.setdefault(chat_id, {})["status"] = "VENDO_OFERTA_NINFA"

            def enviar_segunda_oferta():
                markup_ninfa = {
                    "inline_keyboard": [
                        [{"text": "✅ VIP + Drive da Ninfa (R$ 14,89)", "callback_data": "comprar_1489"}],
                        [{"text": "❌ Apenas o VIP Principal (R$ 9,90)", "callback_data": "comprar_990"}]
                    ]
                }
                enviar_foto(chat_id, FOTO_OFERTA_NINFA, TEXTO_OFERTA_NINFA, markup_ninfa)

            threading.Thread(target=enviar_segunda_oferta).start()
            agendar_remarketing(chat_id, "VENDO_OFERTA_NINFA", 0)

        elif botao == "verificar_pagamento":
            responder_clique_botao(query["id"])
            tx_id = usuarios.get(chat_id, {}).get("tx_id")

            def checar_pix():
                if not tx_id:
                    enviar_mensagem(chat_id, "⚠️ *Nenhum PIX ativo encontrado.* Gere um novo código acima para continuar.")
                    return

                enviar_mensagem(chat_id, "🔍 *Verificando seu pagamento junto ao banco, aguarde...*")
                pago = consultar_pagamento_pushinpay(tx_id)

                if pago:
                    processar_pagamento_aprovado(chat_id, tx_id)
                else:
                    enviar_mensagem(
                        chat_id,
                        "⏳ *Pagamento ainda não identificado!*\n\nO banco ainda não confirmou o seu PIX. Assim que concluir o pagamento no aplicativo do seu banco, toque em **✅ Confirmar Pagamento** novamente."
                    )

            threading.Thread(target=checar_pix).start()

        else:
            responder_clique_botao(query["id"])
            # Valores de TESTE (< R$ 1,00 e R$ 1,10). Depois do teste, volte para os originais:
            valores = {
                "comprar_1489": "0.60",     # Original: "14.89"
                "comprar_990": "0.50",      # Original: "9.90"
                "pagar_taxa_1290": "1.10",  # Original: "12.90"
                "pagar_taxa_490": "0.55"    # Original: "4.90"
            }
            if botao in valores:
                threading.Thread(target=entregar_pix_completo, args=(chat_id, valores[botao])).start()

    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

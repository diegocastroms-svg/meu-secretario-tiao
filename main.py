import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import time

# --- CONFIGURAÇÕES ---
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
GOOGLE_JSON_STR = os.environ.get('GOOGLE_JSON')

bot = telebot.TeleBot(TOKEN, threaded=False)

def perguntar_gemini(prompt_texto):
    """Função com nome válido e tratamento de erro real"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        # 1. Se a API retornar um erro oficial do Google (Cota, Chave, etc)
        if 'error' in data:
            return f"❌ ERRO_API: {data['error'].get('message', 'Erro desconhecido')}"

        # 2. Se a resposta for válida
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']

        # 3. Se vier vazio (Bloqueio de segurança residual ou formato)
        return f"⚠️ RESPOSTA_VAZIA | DEBUG: {json.dumps(data)}"

    except Exception as e:
        return f"💥 ERRO_CONEXAO: {str(e)}"

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@bot.message_handler(func=lambda m: True)
def tratar_tudo(message):
    try:
        if message.content_type != 'text':
            bot.reply_to(message, "Envie texto para o teste final!")
            return

        bot.send_chat_action(message.chat.id, 'typing')
        
        instrucao = f"Analise: '{message.text}'. Responda estritamente: FINANCEIRO | Item | Valor ou AGENDA | O que | Quando."
        ai_msg = perguntar_gemini(instrucao).strip()
        
        # Se a IA respondeu no formato certo, salva
        if "|" in ai_msg and "ERRO" not in ai_msg:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_msg.split('|')
            aba_nome = "Financeiro" if "FINANCEIRO" in partes[0] else "Agenda"
            aba = sheet.worksheet(aba_nome)
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            # Se for erro ou resposta fora do padrão, o bot fala o que aconteceu
            bot.reply_to(message, ai_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Geral: {str(e)}")

# Limpeza de Webhook (Evita 409)
bot.remove_webhook()
time.sleep(3)
print("🚀 Tião Online com Debug Ativo!")
bot.infinity_polling()

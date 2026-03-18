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
    """Versão V1 - Nome do modelo padronizado"""
    # URL sem o '-latest', usando o nome base que é mais aceito na v1
    url = f"https://generativeai.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        if 'error' in data:
            return f"❌ ERRO_API: {data['error'].get('message')} | CODE: {data['error'].get('code')}"

        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']

        return f"⚠️ RESPOSTA_VAZIA | DEBUG: {json.dumps(data)}"

    except Exception as e:
        return f"💥 ERRO_CONEXAO: {str(e)}"

def conectar_planilha():
    if not GOOGLE_JSON_STR:
        raise Exception("Variável GOOGLE_JSON não configurada!")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@bot.message_handler(func=lambda m: True)
def tratar_tudo(message):
    try:
        if message.content_type != 'text':
            bot.reply_to(message, "Mande texto para o teste final!")
            return

        bot.send_chat_action(message.chat.id, 'typing')
        
        instrucao = f"Analise: '{message.text}'. Responda: FINANCEIRO | Item | Valor ou AGENDA | O que | Quando."
        ai_msg = perguntar_gemini(instrucao).strip()
        
        if "|" in ai_msg and "ERRO" not in ai_msg:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_msg.split('|')
            aba_nome = "Financeiro" if "FINANCEIRO" in partes[0] else "Agenda"
            aba = sheet.worksheet(aba_nome)
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            bot.reply_to(message, ai_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro: {str(e)}")

bot.remove_webhook()
time.sleep(3)
bot.infinity_polling()

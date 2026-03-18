import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import time

# CONFIGURAÇÕES
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
GOOGLE_JSON_STR = os.environ.get('GOOGLE_JSON')

bot = telebot.TeleBot(TOKEN, threaded=False)

def perguntar_gemini(prompt_texto):
    """Fala direto com a API do Gemini sem intermediários"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_texto}]}]}
    headers = {'Content-Type': 'application/json'}
    res = requests.post(url, json=payload, headers=headers)
    return res.json()['candidates'][0]['content']['parts'][0]['text']

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@bot.message_handler(func=lambda m: True)
def tratar_tudo(message):
    try:
        # Se for áudio, avisamos que nesta versão manual focaremos no texto primeiro para validar
        if message.content_type != 'text':
            bot.reply_to(message, "Por enquanto, mande apenas texto para validarmos a conexão! 🚀")
            return

        instrucao = f"Analise: '{message.text}'. Se gasto: 'FINANCEIRO | Item | Valor'. Se agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        ai_msg = perguntar_gemini(instrucao).strip()
        
        if "|" in ai_msg:
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

# Limpa qualquer conexão travada (Erro 409)
bot.remove_webhook()
time.sleep(2)
print("🚀 Modo Manual Ativo!")
bot.infinity_polling()

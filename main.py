import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json
import time

# CONFIGURAÇÕES
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
GOOGLE_JSON_STR = os.environ.get('GOOGLE_JSON')

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def processar_texto_ai(texto, msg):
    try:
        prompt = f"Analise: '{texto}'. Se for gasto: 'FINANCEIRO | Item | Valor'. Se for agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        response = model.generate_content(prompt)
        ai_msg = response.text.strip()
        
        if "|" in ai_msg:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_msg.split('|')
            tipo = partes[0].strip()
            
            if "FINANCEIRO" in tipo:
                aba = sheet.worksheet("Financeiro")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(msg, f"✅ Salvo no Financeiro: {partes[1].strip()}")
            elif "AGENDA" in tipo:
                aba = sheet.worksheet("Agenda")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(msg, f"📅 Agendado: {partes[1].strip()}")
        else:
            bot.reply_to(msg, ai_msg)
    except Exception as e:
        bot.reply_to(msg, f"❌ Erro: {str(e)}")

@bot.message_handler(content_types=['text'])
def tratar_texto(message):
    processar_texto_ai(message.text, message)

@bot.message_handler(content_types=['voice', 'audio'])
def tratar_audio(message):
    try:
        bot.reply_to(message, "Ouvindo... 🎧")
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        response = model.generate_content([
            "Transcreva e classifique: 'FINANCEIRO | Item | Valor' ou 'AGENDA | O que | Quando'.",
            {"mime_type": "audio/ogg", "data": downloaded_file}
        ])
        processar_texto_ai(response.text, message)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Áudio: {str(e)}")

print("🚀 Iniciando limpo...")
bot.polling(non_stop=True, interval=1)

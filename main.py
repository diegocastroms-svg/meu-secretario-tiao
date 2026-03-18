import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json

# CONFIGURAÇÕES
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
GOOGLE_JSON_STR = os.environ.get('GOOGLE_JSON')

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def processar_texto_ai(mensagem_texto, telegram_msg):
    try:
        prompt = f"Analise: '{mensagem_texto}'. Se gasto: 'FINANCEIRO | Item | Valor'. Se agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        ai_response = model.generate_content(prompt).text.strip()
        
        if "|" in ai_response:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_response.split('|')
            tipo = partes[0].strip()
            
            if "FINANCEIRO" in tipo:
                aba = sheet.worksheet("Financeiro")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(telegram_msg, f"✅ Salvo no Financeiro: {partes[1].strip()}")
            elif "AGENDA" in tipo:
                aba = sheet.worksheet("Agenda")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(telegram_msg, f"📅 Agendado: {partes[1].strip()}")
        else:
            bot.reply_to(telegram_msg, ai_response)
    except Exception as e:
        bot.reply_to(telegram_msg, f"❌ Erro na Planilha: {str(e)}")

# TRATAMENTO DE TEXTO
@bot.message_handler(func=lambda message: True)
def msg_texto(message):
    processar_texto_ai(message.text, message)

# TRATAMENTO DE ÁUDIO 🎤
@bot.message_handler(content_types=['voice', 'audio'])
def msg_audio(message):
    try:
        bot.reply_to(message, "Ouvindo áudio... 🎧")
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # O Gemini Flash aceita o arquivo direto se mandarmos como bytes
        response = model.generate_content([
            "Transcreva este áudio e responda no formato: FINANCEIRO | Item | Valor ou AGENDA | O que | Quando.",
            {"mime_type": "audio/ogg", "data": downloaded_file}
        ])
        
        processar_texto_ai(response.text, message)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro no Áudio: {str(e)}")

print("🚀 Bot ATIVO e ouvindo áudios!")
bot.polling(non_stop=True)

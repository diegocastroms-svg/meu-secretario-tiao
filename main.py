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

# threaded=False evita que o bot abra várias "vias" e cause o erro 409
bot = telebot.TeleBot(TOKEN, threaded=False)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@bot.message_handler(content_types=['text', 'voice', 'audio'])
def tratar_mensagem(message):
    try:
        if message.content_type == 'text':
            texto_usuario = message.text
        else:
            bot.reply_to(message, "Ouvindo áudio... 🎧")
            file_info = bot.get_file(message.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            # Gemini processando áudio diretamente
            response = model.generate_content([
                "Transcreva e classifique: 'FINANCEIRO | Item | Valor' ou 'AGENDA | O que | Quando'.",
                {"mime_type": "audio/ogg", "data": downloaded_file}
            ])
            texto_usuario = response.text

        # Processamento da IA para classificar
        prompt = f"Analise: '{texto_usuario}'. Se gasto: 'FINANCEIRO | Item | Valor'. Se agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        ai_response = model.generate_content(prompt).text.strip()
        
        if "|" in ai_response:
            partes = ai_response.split('|')
            tipo = partes[0].strip()
            
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            aba_nome = "Financeiro" if "FINANCEIRO" in tipo else "Agenda"
            aba = sheet.worksheet(aba_nome)
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            bot.reply_to(message, ai_response)

    except Exception as e:
        bot.reply_to(message, f"❌ Erro: {str(e)}")

# LIMPEZA DE WEBHOOK (Resolve o Erro 409)
bot.remove_webhook()
time.sleep(2)

print("🚀 Bot ON e limpo!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)

import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json

# CONFIGURAÇÕES FIXAS (TOKEN E PLANILHA)
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
GOOGLE_JSON_STR = os.environ.get('GOOGLE_JSON')

# Inicializa Bot
bot = telebot.TeleBot(TOKEN)

# Configura Gemini (Ajustado para evitar o erro 404)
genai.configure(api_key=GEMINI_KEY)
# Mudamos para 'gemini-1.5-flash' apenas, que é o padrão estável atual
model = genai.GenerativeModel('gemini-1.5-flash')

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def processar_texto_ai(mensagem_texto, telegram_msg):
    try:
        prompt = f"Analise: '{mensagem_texto}'. Se gasto: 'FINANCEIRO | Item | Valor'. Se agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        
        if "|" in ai_response:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_response.split('|')
            tipo = partes[0].strip()
            
            if "FINANCEIRO" in tipo:
                aba = sheet.worksheet("Financeiro")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(telegram_msg, f"✅ Salvo no Financeiro: {partes[1].strip()} - R$ {partes[2].strip()}")
            elif "AGENDA" in tipo:
                aba = sheet.worksheet("Agenda")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(telegram_msg, f"📅 Agendado: {partes[1].strip()} para {partes[2].strip()}")
        else:
            bot.reply_to(telegram_msg, ai_response)
    except Exception as e:
        bot.reply_to(telegram_msg, f"❌ Erro Técnico: {str(e)}")

# TRATAMENTO DE TEXTO
@bot.message_handler(content_types=['text'])
def msg_texto(message):
    processar_texto_ai(message.text, message)

# TRATAMENTO DE ÁUDIO 🎤
@bot.message_handler(content_types=['voice', 'audio'])
def msg_audio(message):
    try:
        aviso = bot.reply_to(message, "Ouvindo áudio... 🎧")
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # O Gemini agora recebe o áudio para transcrever e classificar
        response = model.generate_content([
            "Transcreva este áudio e classifique. Se for gasto: 'FINANCEIRO | Item | Valor'. Se for agenda: 'AGENDA | O que | Quando'.",
            {"mime_type": "audio/ogg", "data": downloaded_file}
        ])
        
        bot.delete_message(message.chat.id, aviso.message_id)
        processar_texto_ai(response.text, message)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro no Áudio: {str(e)}")

print("🚀 Bot ATIVO e corrigido!")
# O non_stop=True ajuda a ignorar conflitos temporários de rede
bot.polling(non_stop=True)

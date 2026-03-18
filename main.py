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

# 1. PROTEÇÃO CONTRA ERRO 409 (Conexão Única)
bot = telebot.TeleBot(TOKEN, threaded=False)

# 2. CONFIGURAÇÃO DO GEMINI (Nome estável)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def conectar_planilha():
    if not GOOGLE_JSON_STR:
        raise Exception("GOOGLE_JSON não configurado no Render!")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def processar_e_salvar(texto_ai, message):
    try:
        if "|" in texto_ai:
            partes = texto_ai.split('|')
            tipo = partes[0].strip()
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            aba_nome = "Financeiro" if "FINANCEIRO" in tipo else "Agenda"
            aba = sheet.worksheet(aba_nome)
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            bot.reply_to(message, texto_ai)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Planilha: {str(e)}")

@bot.message_handler(content_types=['text'])
def msg_texto(message):
    try:
        prompt = f"Analise: '{message.text}'. Se gasto: 'FINANCEIRO | Item | Valor'. Se agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        response = model.generate_content(prompt)
        processar_e_salvar(response.text.strip(), message)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Gemini: {str(e)}")

@bot.message_handler(content_types=['voice', 'audio'])
def msg_audio(message):
    try:
        bot.reply_to(message, "Ouvindo... 🎧")
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 3. CORREÇÃO DO ÁUDIO (inline_data para evitar 404/Erro Interno)
        response = model.generate_content(
            contents=[{
                "parts": [
                    {"text": "Transcreva e formate como: FINANCEIRO | Item | Valor ou AGENDA | O que | Quando."},
                    {"inline_data": {"mime_type": "audio/ogg", "data": downloaded_file}}
                ]
            }]
        )
        processar_e_salvar(response.text.strip(), message)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Áudio: {str(e)}")

# --- START LIMPO ---
print("🧹 Limpando conexões e aguardando 5 segundos...")
bot.remove_webhook()
time.sleep(5) 

print("🚀 Tião Online e Blindado!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)

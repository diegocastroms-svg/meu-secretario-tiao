import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json
import time

# --- CONFIGURAÇÕES FIXAS ---
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
GOOGLE_JSON_STR = os.environ.get('GOOGLE_JSON')

# Inicializa o Bot (threaded=False evita o erro 409 de conflito)
bot = telebot.TeleBot(TOKEN, threaded=False)

# Configura Gemini com o nome de modelo oficial (corrige o erro 404)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

def conectar_planilha():
    """Conecta ao Google Sheets usando a chave do Render"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def processar_e_salvar(texto_bruto, message):
    """Analisa o texto com IA e salva na aba correta"""
    try:
        prompt = f"Analise: '{texto_bruto}'. Se gasto: 'FINANCEIRO | Item | Valor'. Se agenda: 'AGENDA | O que | Quando'. Senão, responda curto."
        response = model.generate_content(prompt)
        ai_msg = response.text.strip()
        
        if "|" in ai_msg:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_msg.split('|')
            tipo = partes[0].strip()
            
            # Define a aba baseada na resposta da IA
            aba_nome = "Financeiro" if "FINANCEIRO" in tipo else "Agenda"
            aba = sheet.worksheet(aba_nome)
            
            # Salva: Item, Valor e Data de hoje
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            bot.reply_to(message, ai_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Técnico: {str(e)}")

# --- TRATAMENTO DE MENSAGENS ---

@bot.message_handler(content_types=['text'])
def msg_texto(message):
    processar_e_salvar(message.text, message)

@bot.message_handler(content_types=['voice', 'audio'])
def msg_audio(message):
    try:
        aviso = bot.reply_to(message, "Ouvindo... 🎧")
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # O Gemini transcreve o áudio diretamente
        response = model.generate_content([
            "Transcreva este áudio e formate como: FINANCEIRO | Item | Valor ou AGENDA | O que | Quando.",
            {"mime_type": "audio/ogg", "data": downloaded_file}
        ])
        
        bot.delete_message(message.chat.id, aviso.message_id)
        processar_e_salvar(response.text, message)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro no Áudio: {str(e)}")

# --- INICIALIZAÇÃO LIMPA ---
print("🧹 Limpando conexões antigas...")
bot.remove_webhook()
time.sleep(2)

print("🚀 Tião Online! Teste agora com texto ou áudio.")
bot.infinity_polling(timeout=20, long_polling_timeout=10)

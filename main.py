import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json

# CONFIGURAÇÕES (LIDAS AUTOMATICAMENTE DO RENDER)
TOKEN = "8341233942:AAFEvYk6tsiCovhSYLPq0u9iJph7yqnuo0c"
GEMINI_KEY = "AIzaSyCQFmMNCca9xSEN57O9qX8rNpn9Fiirhfg"
SPREADSHEET_ID = "1s9c2U-zopGuspeX2HQ4cv0KY9OLu9gCuMWHTWAk24QU"
# A variável GOOGLE_JSON deve estar configurada no Painel do Render!
GOOGLE_JSON = os.environ.get('GOOGLE_JSON')

# Inicializa Bot e Inteligência Artificial
bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def conectar_planilha():
    """Função para abrir a conexão com o Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@bot.message_handler(func=lambda message: True)
def processar_mensagem(message):
    try:
        # Instrução mestre para o Gemini
        prompt = f"""
        Você é um secretário pessoal de alta performance. O usuário enviou: '{message.text}'.
        Analise a intenção:
        1. Se for um GASTO ou PAGAMENTO: Responda estritamente neste formato: FINANCEIRO | Item | Valor
        2. Se for um COMPROMISSO ou LEMBRETE: Responda estritamente neste formato: AGENDA | O que fazer | Quando
        3. Se for apenas conversa: Responda de forma curta e prestativa.
        """
        
        ai_response = model.generate_content(prompt).text.strip()
        
        # Se a IA identificar que deve salvar na planilha
        if "|" in ai_response:
            partes = ai_response.split('|')
            tipo = partes[0].strip()
            
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            
            if "FINANCEIRO" in tipo:
                aba = sheet.worksheet("Financeiro")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(message, f"✅ Anotei no seu Financeiro: {partes[1].strip()} - R$ {partes[2].strip()}")
            
            elif "AGENDA" in tipo:
                aba = sheet.worksheet("Agenda")
                aba.append_row([partes[1].strip(), partes[2].strip()])
                bot.reply_to(message, f"📅 Agendado com sucesso: {partes[1].strip()} para {partes[2].strip()}")
        
        else:
            # Resposta comum de chat
            bot.reply_to(message, ai_response)
            
    except Exception as e:
        print(f"Erro no processamento: {e}")
        bot.reply_to(message, "Recebi, mas não consegui salvar na planilha. Verifique se as abas 'Financeiro' e 'Agenda' existem!")

print("🚀 Bot do Copiloto de Trade ATIVO!")
bot.polling(non_stop=True)

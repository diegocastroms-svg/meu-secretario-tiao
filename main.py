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

# Inicialização com timeout longo para estabilidade
bot = telebot.TeleBot(TOKEN, threaded=False)

def perguntar_gemini(prompt_texto):
    """
    Usa o endpoint oficial v1. Blinda contra erros de resposta não-JSON.
    """
    url = f"https://generativeai.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
    }
    
    try:
        res = requests.post(url, json=payload, timeout=15)
        
        # FUNDAMENTAL: Só processa se o status for 200 (OK)
        if res.status_code == 200:
            data = res.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                return data['candidates'][0]['content']['parts'][0]['text']
            return "ERRO_IA: Resposta vazia."
        else:
            # Se der erro (400, 404, 500), ele retorna o código para debug
            return f"ERRO_GOOGLE_HTTP_{res.status_code}"
    except Exception as e:
        return f"ERRO_CONEXAO: {str(e)}"

def conectar_planilha():
    try:
        creds_dict = json.loads(GOOGLE_JSON_STR)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Erro gspread: {e}")
        return None

@bot.message_handler(func=lambda m: True)
def router(message):
    try:
        # 1. Feedback visual
        bot.send_chat_action(message.chat.id, 'typing')
        
        # 2. IA Processa o comando
        instrucao = f"Categorize e extraia: '{message.text}'. Formato: CATEGORIA | ITEM | VALOR"
        res_ai = perguntar_gemini(instrucao).strip()
        
        # 3. Lógica de Gravação
        if "|" in res_ai and "ERRO" not in res_ai:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = res_ai.split('|')
            
            # Decide a aba
            nome_aba = "Financeiro" if "FIN" in partes[0].upper() else "Agenda"
            aba = sheet.worksheet(nome_aba)
            
            # Adiciona: Item, Valor, Data
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Gravado em {nome_aba}: {partes[1].strip()}")
        else:
            # Se for erro ou resposta comum, apenas responde
            bot.reply_to(message, res_ai)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro de Processamento: {str(e)}")

# --- BOOTSTRAP (O segredo da estabilidade) ---
if __name__ == "__main__":
    print("🧹 Iniciando limpeza de conexões...")
    
    # FORÇA o Telegram a fechar qualquer conexão antiga e ignorar mensagens acumuladas
    # O parâmetro drop_pending_updates=True limpa o lixo que causa o erro 409
    requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True")
    
    time.sleep(3) # Tempo de respiro para os servidores do Telegram
    
    print("🚀 Tião Online e Estabilizado!")
    
    # Polling infinito com parâmetros de resiliência
    bot.infinity_polling(timeout=60, long_polling_timeout=30)

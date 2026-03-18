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
    """
    ENDPOINT DEFINITIVO: generativeai.googleapis.com
    MODELO: gemini-1.5-flash (Estável)
    """
    url = f"https://generativeai.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {"temperature": 0.1}
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        
        # Se o Google retornar erro (404, 400, 403), pegamos o texto puro para não travar o JSON
        if res.status_code != 200:
            return f"❌ Erro Google ({res.status_code}): {res.text[:100]}"
            
        data = res.json()
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']
        return "⚠️ IA retornou vazio."
        
    except Exception as e:
        return f"💥 Falha na API: {str(e)}"

def conectar_planilha():
    try:
        creds_dict = json.loads(GOOGLE_JSON_STR)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Erro credenciais: {e}")
        return None

@bot.message_handler(func=lambda m: True)
def processar_tudo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        # Prompt otimizado para não disparar filtros de segurança
        instrucao = f"Extraia os dados desta frase para uma planilha. Formato: CATEGORIA | ITEM | VALOR. Frase: '{message.text}'"
        resposta = perguntar_gemini(instrucao).strip()
        
        if "|" in resposta:
            client = conectar_planilha()
            if not client:
                bot.reply_to(message, "❌ Erro nas credenciais do Google Planilhas.")
                return
            
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = resposta.split('|')
            # Verifica qual aba usar
            aba_nome = "Financeiro" if "FIN" in partes[0].upper() else "Agenda"
            aba = sheet.worksheet(aba_nome)
            
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            bot.reply_to(message, resposta)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro no Bot: {str(e)}")

# --- EXECUÇÃO COM LIMPEZA DE CACHE ---
if __name__ == "__main__":
    print("🧹 Removendo sessões antigas para evitar Erro 409...")
    # O PULO DO GATO: Deleta qualquer conexão aberta antes de começar
    requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    time.sleep(2)
    
    print("🚀 Tião Online e Blindado!")
    # Reinicia o polling do zero
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

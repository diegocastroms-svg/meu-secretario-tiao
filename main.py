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
    """Versão V1 + Flash-Latest: Corrigido para evitar o erro 404 de modelo não encontrado"""
    # Endpoint atualizado para v1 oficial
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        # Se a API retornar erro de cota ou chave
        if 'error' in data:
            return f"❌ ERRO_API: {data['error'].get('message', 'Erro desconhecido')}"

        # Se a resposta for válida
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']

        # Se vier vazio (Bloqueio ou erro de formato)
        return f"⚠️ RESPOSTA_VAZIA | DEBUG: {json.dumps(data)}"

    except Exception as e:
        return f"💥 ERRO_CONEXAO: {str(e)}"

def conectar_planilha():
    if not GOOGLE_JSON_STR:
        raise Exception("Variável GOOGLE_JSON não encontrada no Render!")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON_STR)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@bot.message_handler(func=lambda m: True)
def tratar_tudo(message):
    try:
        if message.content_type != 'text':
            bot.reply_to(message, "Por favor, envie um texto para validar a conexão! 🚀")
            return

        bot.send_chat_action(message.chat.id, 'typing')
        
        instrucao = (
            f"Analise: '{message.text}'. "
            "Responda estritamente no formato: FINANCEIRO | Item | Valor ou AGENDA | O que | Quando. "
            "Se não for nenhum, responda: 'Não entendi'."
        )
        
        ai_msg = perguntar_gemini(instrucao).strip()
        
        # Se a IA respondeu no formato esperado e não é erro técnico
        if "|" in ai_msg and "ERRO" not in ai_msg and "VAZIA" not in ai_msg:
            client = conectar_planilha()
            sheet = client.open_by_key(SPREADSHEET_ID)
            partes = ai_msg.split('|')
            
            # Escolhe a aba baseada na resposta da IA
            aba_nome = "Financeiro" if "FINANCEIRO" in partes[0] else "Agenda"
            aba = sheet.worksheet(aba_nome)
            
            # Adiciona a linha (Item, Valor, Data)
            aba.append_row([partes[1].strip(), partes[2].strip(), time.strftime("%d/%m/%Y")])
            bot.reply_to(message, f"✅ Salvo em {aba_nome}: {partes[1].strip()}")
        else:
            # Se for um erro da API ou resposta fora do padrão, mostra ao usuário
            bot.reply_to(message, ai_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro Geral: {str(e)}")

# Limpeza para evitar Erro 409 (Conflito de Instância)
bot.remove_webhook()
time.sleep(3)
print("🚀 Tião Online - Versão V1 Flash-Latest!")
bot.infinity_polling()

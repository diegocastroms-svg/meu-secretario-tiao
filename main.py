# O código que faz o Tião entender suas mensagens e salvar na planilha
import os
import telebot
import google.generativeai as genai

# Aqui o código vai buscar suas chaves que vamos esconder no Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

@bot.message_handler(func=lambda message: True)
def responder(message):
    model = genai.GenerativeModel('gemini-1.5-flash')
    resposta = model.generate_content(f"Ajude o usuário: {message.text}")
    bot.reply_to(message, resposta.text)

bot.polling()

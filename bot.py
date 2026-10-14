import os
import threading
import time
from datetime import datetime
import pytz
import telebot
from telebot import types
import matplotlib
matplotlib.use('Agg')  # Бессерверный бекенд для работы с графиками на сервере
import matplotlib.pyplot as plt

# ==========================================
# 1. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ
# ==========================================

# Токен бота (лучше считывать из переменных окружения Render, либо указать напрямую)
TOKEN = os.environ.get('8984494226:AAHm4W2uYmdFeJYWwQFvEDjV5tl8UTVxZCU', 'ВАШ_ТОКЕН_БОТА_ЗДЕСЬ')
bot = telebot.TeleBot(TOKEN)

# Часовой пояс
TIMEZONE = pytz.timezone('Europe/Moscow')

# ID вашей рабочей группы (замените на реальный, обычно начинается с минуса, например: -1001234567890)
-1003917288247 = int(os.environ.get('GROUP_CHAT_ID', -1001234567890))

# Временное хранилище данных (в памяти бота)
reports_data = {
    'subscribers': [],    # Список кортежей: (datetime, count)
    'unsubscribers': [],  # Список кортежей: (datetime, count)
    'content_posts': []   # Список кортежей: (datetime, manager_id, count)
}

# ==========================================
# 2. ГЕНЕРАЦИЯ ГРАФИКОВ (MATPLOTLIB)
# ==========================================

def generate_analytics_chart():
    """Генерирует и сохраняет график динамики аудитории"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    
    if not reports_data['subscribers']:
        dates = [datetime.now(TIMEZONE).strftime('%d.%m')]
        subs = [0]
        unsubs = [0]
    else:
        dates = [item[0].strftime('%d.%m') for item in reports_data['subscribers']]
        subs = [item[1] for item in reports_data['subscribers']]
        unsubs = [item[1] for item in reports_data['unsubscribers']] if reports_data['unsubscribers'] else [0]*len(subs)

    ax.plot(dates, subs, marker='o', color='green', label='Прирост (подписчики)', linewidth=2)
    ax.plot(dates, unsubs, marker='x', color='red', label='Отток (отписки)', linewidth=2)

    ax.set_title('Динамика аудитории группы', fontsize=14, fontweight='bold')
    ax.set_xlabel('Дата')
    ax.set_ylabel('Количество человек')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    
    chart_path = 'analytics_chart.png'
    plt.tight_layout()
    plt.savefig(chart_path, dpi=200)
    plt.close()
    return chart_path

# ==========================================
# 3. КОМАНДЫ И ОБРАБОТКА ОТЧЕТОВ В ГРУППЕ
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "🤖 **Бот аналитики и отчетности запущен!**\n\n"
        "Доступные команды в группе:\n"
        "• `/content [число]` — сдать отчет по контенту (пример: `/content 5`)\n"
        "• `/traffic [подписчики] [отписки]` — сдать отчет по трафику (пример: `/traffic 120 15`)\n"
        "• `/analytics` — показать текущий график и сводку"
    )
    bot.reply_to(message, text, parse_mode='Markdown')

# Обработка отчета контент-менеджера: /content 5
@bot.message_handler(commands=['content'])
def process_content_report(message):
    # Разрешаем принимать отчеты только в целевой группе (или везде, если GROUP_CHAT_ID не проверяется жестко)
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Укажите количество постов. Пример: `/content 5`", parse_mode='Markdown')
            return
        
        count = int(args[1])
        now = datetime.now(TIMEZONE)
        user_name = message.from_user.first_name
        
        reports_data['content_posts'].append((now, message.from_user.id, count))
        bot.reply_to(message, f"✅ Отчет контент-менеджера ({user_name}) принят!\n📝 Постов за сегодня: **{count}**", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Пожалуйста, введите числовое значение после команды /content.")

# Обработка отчета трафик-менеджера: /traffic 120 15
@bot.message_handler(commands=['traffic'])
def process_traffic_report(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Укажите подписчиков и отписки. Пример: `/traffic 120 15`", parse_mode='Markdown')
            return
        
        subs = int(args[1])
        unsubs = int(args[2])
        now = datetime.now(TIMEZONE)
        user_name = message.from_user.first_name
        
        reports_data['subscribers'].append((now, subs))
        reports_data['unsubscribers'].append((now, unsubs))
        
        bot.reply_to(
            message, 
            f"✅ Отчет трафик-менеджера ({user_name}) сохранен!\n➕ Подписчиков: **{subs}**\n➖ Отписок: **{unsubs}**",
            parse_mode='Markdown'
        )
    except ValueError:
        bot.reply_to(message, "❌ Пожалуйста, используйте числа. Пример: `/traffic 120 15`")

# Команда вызова аналитики и графиков
@bot.message_handler(commands=['analytics'])
def send_analytics(message):
    bot.reply_to(message, "📊 Формирую график аналитики...")
    chart_path = generate_analytics_chart()
    
    total_subs = sum(x[1] for x in reports_data['subscribers'])
    total_unsubs = sum(x[1] for x in reports_data['unsubscribers'])
    growth = total_subs - total_unsubs
    total_posts = sum(x[2] for x in reports_data['content_posts'])

    caption = (
        "📈 **Сводная аналитика группы**\n\n"
        f"• Всего постов: **{total_posts}**\n"
        f"• Всего подписок: **+{total_subs}**\n"
        f"• Всего отписок: **-{total_unsubs}**\n"
        f"• Чистый прирост: **{'+' if growth >= 0 else ''}{growth}**"
    )

    with open(chart_path, 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption=caption, parse_mode='Markdown')

# ==========================================
# 4. АВТОМАТИЧЕСКИЕ НАПОМИНАНИЯ (ФОНОВЫЙ ПОТОК)
# ==========================================

def reminder_scheduler():
    """Фоновый поток для отправки ежедневных напоминаний в группу"""
    while True:
        now = datetime.now(TIMEZONE)
        # Отправка напоминания в группе каждый день в 20:00
        if now.hour == 20 and now.minute == 0:
            try:
                bot.send_message(
                    GROUP_CHAT_ID, 
                    "🔔 **Вечернее напоминание!**\nКоллеги, не забудьте сдать отчеты за день:\n"
                    "• Контент: `/content [посты]`\n"
                    "• Трафик: `/traffic [подписчики] [отписки]`",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Ошибка отправки напоминания в группу: {e}")
            time.sleep(60)  # Пауза минуту, чтобы сообщение не дублировалось
        time.sleep(30)

# Запуск планировщика в фоновом режиме
reminder_thread = threading.Thread(target=reminder_scheduler, daemon=True)
reminder_thread.start()

# ==========================================
# 5. ЗАПУСК БОТА
# ==========================================

if __name__ == '__main__':
    print("Бот запущен и готов к работе в группе...")
    bot.infinity_polling(skip_pending=True)
  

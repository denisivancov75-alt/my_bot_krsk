import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Берем токен из переменной окружения (для Railway)
TOKEN = os.getenv("TOKEN")

# Файлы
ORDERS_FILE = "zayavki.txt"   # Заявки (доходы)
EXPENSES_FILE = "rashody.txt" # Расходы

def write_to_file(filename, text):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception as e:
        print(f"Ошибка записи: {e}")

def read_file(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

# Расчет итогов
def calculate_totals():
    orders_text = read_file(ORDERS_FILE)
    expenses_text = read_file(EXPENSES_FILE)
    total_income = 0
    total_expenses = 0

    # Подсчет доходов из заявок
    if orders_text:
        for line in orders_text.splitlines():
            parts = line.split("|")
            for part in parts:
                if "Сумма" in part:
                    try:
                        total_income += int(part.split(":")[1].strip())
                    except:
                        pass

    # Подсчет расходов (просто общая сумма)
    if expenses_text:
        for line in expenses_text.splitlines():
            parts = line.split("|")
            for part in parts:
                if "Расход" in part:
                    try:
                        total_expenses += int(part.split(":")[1].strip())
                    except:
                        pass

    profit = total_income - total_expenses
    return total_income, total_expenses, profit

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚚 Создать заявку", callback_data="new")],
        [InlineKeyboardButton("💰 Заполнить расходы", callback_data="expenses")],
        [InlineKeyboardButton("📊 Отчет", callback_data="report")],
        [InlineKeyboardButton("🗑️ Очистить отчет", callback_data="clear")]
    ]
    await update.message.reply_text("🤖 Бот учета грузоперевозок", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "new":
        # Меню выбора техники
        keyboard = [
            [InlineKeyboardButton("🌀 Стиральная машинка", callback_data="tech_wash")],
            [InlineKeyboardButton("❄️ Холодильник", callback_data="tech_fridge")],
            [InlineKeyboardButton("🍽️ Посудомойка", callback_data="tech_dish")],
            [InlineKeyboardButton("📦 Прочее", callback_data="tech_other")]
        ]
        await query.edit_message_text(
            text="🛠️ Выберите тип техники:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data.startswith("tech_"):
        tech_names = {
            "tech_wash": "🌀 Стиральная машинка",
            "tech_fridge": "❄️ Холодильник",
            "tech_dish": "🍽️ Посудомойка",
            "tech_other": "📦 Прочее"
        }
        user_data[user_id] = {"type": "order", "tech": tech_names[query.data]}
        await query.edit_message_text(text="📍 Введите адрес:")
    elif query.data == "expenses":
        user_data[user_id] = {"type": "expense"}
        await query.edit_message_text(text="📅 Введите дату расхода (например: 15.10):")
    elif query.data == "report":
        orders = read_file(ORDERS_FILE)
        expenses = read_file(EXPENSES_FILE)
        total_income, total_expenses, profit = calculate_totals()
        await query.edit_message_text(
            text=f"📊 Отчет:\n\n"
                 f"🚚 Заявки:\n{orders}\n\n"
                 f"💰 Расходы:\n{expenses}\n\n"
                 f"💵 Итого заработано: {total_income}\n"
                 f"💸 Итого потрачено: {total_expenses}\n"
                 f"✅ Чистыми: {profit}"
        )
    elif query.data == "clear":
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data="clear_yes")],
            [InlineKeyboardButton("❌ Нет, оставить", callback_data="clear_no")]
        ]
        await query.edit_message_text(text="⚠️ Вы уверены, что хотите обнулить весь отчет?", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "clear_yes":
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for f in [ORDERS_FILE, EXPENSES_FILE]:
            file_path = os.path.join(base_dir, f)
            if os.path.exists(file_path):
                os.remove(file_path)
        await query.edit_message_text(text="✅ Отчет успешно обнулен. Данные удалены.")
    elif query.data == "clear_no":
        await query.edit_message_text(text="✅ Отчет сохранен. Ничего не удалено.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_data:
        await update.message.reply_text("Пожалуйста, нажмите /start и выберите действие.")
        return

    step = len(user_data[user_id])
    user_type = user_data[user_id].get("type")

    if user_type == "order":
        if step == 2:  # адрес
            user_data[user_id]["address"] = text
            await update.message.reply_text("📞 Введите номер телефона:")
        elif step == 3:  # телефон
            user_data[user_id]["phone"] = text
            await update.message.reply_text("🕒 Введите время (например: 14:30):")
        elif step == 4:  # время
            user_data[user_id]["time"] = text
            await update.message.reply_text("💰 Введите сумму, которую забрали (доход):")
        elif step == 5:  # сумма
            user_data[user_id]["income"] = text
            order_data = user_data.pop(user_id)
            order_str = (f"📅 {order_data['tech']} | 📍 Адрес: {order_data['address']} | "
                         f"📞 Телефон: {order_data['phone']} | 🕒 Время: {order_data['time']} | "
                         f"💰 Сумма: {order_data['income']}")
            write_to_file(ORDERS_FILE, order_str)
            await update.message.reply_text(f"✅ Заявка сохранена!\n\n{order_str}\n\nНажмите /start для нового действия.")

    elif user_type == "expense":
        if step == 1:  # дата
            user_data[user_id]["date"] = text
            await update.message.reply_text("💰 Введите сумму расхода:")
        elif step == 2:  # сумма расхода
            user_data[user_id]["expense"] = text
            expense_data = user_data.pop(user_id)
            expense_str = f"📅 {expense_data['date']} | 💰 Расход: {expense_data['expense']}"
            write_to_file(EXPENSES_FILE, expense_str)
            await update.message.reply_text(f"✅ Расход сохранен!\n\n{expense_str}\n\nНажмите /start для нового действия.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
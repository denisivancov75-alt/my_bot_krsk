import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = "8800374629:AAGrSBvsTbJI3d2pYYNYc-2HByvU9iU4GgQ"

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

# Функция для автоматического подсчета итогов
def calculate_totals():
    orders_text = read_file(ORDERS_FILE)
    expenses_text = read_file(EXPENSES_FILE)
    
    total_income = 0
    total_expenses = 0

    if orders_text:
        for line in orders_text.splitlines():
            parts = line.split("|")
            for part in parts:
                if "Доход" in part:
                    try:
                        total_income += int(part.split(":")[1].strip())
                    except:
                        pass

    if expenses_text:
        for line in expenses_text.splitlines():
            parts = line.split("|")
            for part in parts:
                if "Бензин" in part:
                    try:
                        total_expenses += int(part.split(":")[1].strip())
                    except:
                        pass
                if "Запчасти" in part:
                    try:
                        total_expenses += int(part.split(":")[1].strip())
                    except:
                        pass
                if "Еда" in part:
                    try:
                        total_expenses += int(part.split(":")[1].strip())
                    except:
                        pass
                if "Процент" in part:
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
        [InlineKeyboardButton("✏️ Редактировать заявку", callback_data="edit")],
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
        user_data[user_id] = {"type": "order"}
        await query.edit_message_text(text="📅 Введите дату и время (например: 15.10 14:30):")
    elif query.data == "edit":
        user_data[user_id] = {"type": "edit"}
        await query.edit_message_text(text="✏️ Введите номер заявки, которую хотите редактировать (например: 1):")
    elif query.data == "expenses":
        user_data[user_id] = {"type": "expense"}
        await query.edit_message_text(text="📅 Введите дату для расходов (например: 15.10):")
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
        await query.edit_message_text(text="⚠️ Вы уверены, что хотите обнулить (удалить) весь отчет?", reply_markup=InlineKeyboardMarkup(keyboard))
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
        await update.message.reply_text("Пожалуйста, нажмите /start и выберите 'Создать заявку' или 'Заполнить расходы'.")
        return

    step = len(user_data[user_id])
    user_type = user_data[user_id].get("type")

    if user_type == "order":
        if step == 1:
            user_data[user_id]["date"] = text
            await update.message.reply_text("📍 Введите адрес, откуда забрали груз:")
        elif step == 2:
            user_data[user_id]["from"] = text
            await update.message.reply_text("🏁 Введите адрес, куда отвезли груз:")
        elif step == 3:
            user_data[user_id]["to"] = text
            await update.message.reply_text("💰 Введите сумму, которую заработали (доход):")
        elif step == 4:
            user_data[user_id]["income"] = text
            order_data = user_data.pop(user_id)
            order_str = f"📅 {order_data['date']} | 🚚 Откуда: {order_data['from']} | 🏁 Куда: {order_data['to']} | 💰 Доход: {order_data['income']}"
            write_to_file(ORDERS_FILE, order_str)
            await update.message.reply_text(f"✅ Заявка сохранена!\n\n{order_str}\n\nНажмите /start для нового действия.")

    elif user_type == "edit":
        if step == 1:
            user_data[user_id]["edit_index"] = text
            await update.message.reply_text("✏️ Найти и редактировать заявку с этим номером? (Пример: 1)")
        elif step == 2:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, ORDERS_FILE)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                index = int(user_data[user_id]["edit_index"]) - 1
                if 0 <= index < len(lines):
                    lines[index] = text + "\n"
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                    await update.message.reply_text("✅ Заявка редактирована!")
                else:
                    await update.message.reply_text("❌ Заявка с таким номером не существует.")
            except FileNotFoundError:
                await update.message.reply_text("❌ Заявок пока нет.")

    elif user_type == "expense":
        if step == 1:
            user_data[user_id]["date"] = text
            await update.message.reply_text("⛽ Введите расходы на бензин:")
        elif step == 2:
            user_data[user_id]["fuel"] = text
            await update.message.reply_text("🔧 Введите расходы на запчасти:")
        elif step == 3:
            user_data[user_id]["parts"] = text
            await update.message.reply_text("🍔 Введите расходы на еду:")
        elif step == 4:
            user_data[user_id]["food"] = text
            await update.message.reply_text("💸 Введите процент (например, 50%):")
        elif step == 5:
            user_data[user_id]["percent"] = text
            expense_data = user_data.pop(user_id)
            expense_str = f"📅 {expense_data['date']} | ⛽ Бензин: {expense_data['fuel']} | 🔧 Запчасти: {expense_data['parts']} | 🍔 Еда: {expense_data['food']} | 💸 Процент: {expense_data['percent']}"
            write_to_file(EXPENSES_FILE, expense_str)
            await update.message.reply_text(f"✅ Расходы сохранены!\n\n{expense_str}\n\nНажмите /start для нового действия.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
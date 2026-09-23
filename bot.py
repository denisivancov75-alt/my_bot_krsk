import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TOKEN")

ORDERS_FILE = "zayavki.txt"   # Заявки
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

def read_lines(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return []

def write_lines(filename, lines):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

# Расчет итогов (только закрытые заявки)
def calculate_totals():
    orders_text = read_file(ORDERS_FILE)
    expenses_text = read_file(EXPENSES_FILE)
    total_income = 0
    total_expenses = 0

    if orders_text:
        for line in orders_text.splitlines():
            if "🟢" in line:  # только закрытые
                parts = line.split("|")
                for part in parts:
                    if "Сумма" in part:
                        try:
                            total_income += int(part.split(":")[1].strip())
                        except:
                            pass

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
        [InlineKeyboardButton("✅ Закрыть заявку", callback_data="close_order")],
        [InlineKeyboardButton("💰 Заполнить расходы", callback_data="expenses")],
        [InlineKeyboardButton("📊 Отчет", callback_data="report")],
        [InlineKeyboardButton("🗑️ Очистить отчет", callback_data="clear")]
    ]
    await update.message.reply_text("🤖 Бот учета заявок", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "new":
        user_data[user_id] = {"type": "order"}
        await query.edit_message_text(text="👤 Введите имя клиента:")
    elif query.data == "close_order":
        # Показываем список открытых заявок
        lines = read_lines(ORDERS_FILE)
        open_orders = []
        for i, line in enumerate(lines):
            if "🟡" in line:
                open_orders.append((i, line.strip()))
        if not open_orders:
            await query.edit_message_text(text="📭 Нет открытых заявок.")
            return
        user_data[user_id] = {"type": "close", "open_orders": open_orders}
        text = "📋 Выберите заявку для закрытия (введите её номер):\n\n"
        for num, (idx, line) in enumerate(open_orders, start=1):
            text += f"{num}. {line}\n\n"
        await query.edit_message_text(text=text)
    elif query.data == "expenses":
        user_data[user_id] = {"type": "expense"}
        await query.edit_message_text(text="📅 Введите дату расхода:")
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
        await query.edit_message_text(text="✅ Отчет успешно обнулен.")
    elif query.data == "clear_no":
        await query.edit_message_text(text="✅ Отчет сохранен.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_data:
        await update.message.reply_text("Пожалуйста, нажмите /start и выберите действие.")
        return

    user_type = user_data[user_id].get("type")

    # ===== СОЗДАНИЕ ЗАЯВКИ =====
    if user_type == "order":
        # Заполняем поля по порядку
        keys_order = ["name", "address", "phone", "time"]
        prompts = {
            "name": "📍 Введите адрес:",
            "address": "📞 Введите номер телефона:",
            "phone": "🕒 Введите время прибытия:",
            "time": "💰 Введите сумму (можно указать 0):"
        }

        current = user_data[user_id]
        filled = [k for k in keys_order if k in current]

        if len(filled) < 4:
            key = keys_order[len(filled)]
            current[key] = text
            # Если следующее поле - time, то задаем следующий вопрос
            filled = [k for k in keys_order if k in current]
            if len(filled) < 4:
                next_key = keys_order[len(filled)]
                await update.message.reply_text(prompts[next_key])
            else:
                # Все поля заполнены - сохраняем заявку
                order_data = user_data.pop(user_id)
                order_str = (f"🟡 {order_data['name']} | 📍 Адрес: {order_data['address']} | "
                             f"📞 Телефон: {order_data['phone']} | 🕒 Время: {order_data['time']} | "
                             f"💰 Сумма: 0")
                write_to_file(ORDERS_FILE, order_str)
                await update.message.reply_text(f"✅ Заявка создана и открыта!\n\n{order_str}\n\nЕё нужно будет закрыть после выполнения.")

    # ===== ЗАКРЫТИЕ ЗАЯВКИ =====
    elif user_type == "close":
        open_orders = user_data[user_id]["open_orders"]
        try:
            num = int(text.strip())
            if 1 <= num <= len(open_orders):
                line_index, line_text = open_orders[num - 1]
                user_data[user_id]["selected_index"] = line_index
                await update.message.reply_text("💰 Введите сумму, которую заработали за эту заявку:")
            else:
                await update.message.reply_text("❌ Неверный номер. Попробуйте снова.")
        except ValueError:
            await update.message.reply_text("❌ Введите число.")

    elif user_type == "close_sum":
        # Это состояние должно быть установлено перед запросом суммы
        pass

    # ===== РАСХОДЫ =====
    elif user_type == "expense":
        if "date" not in user_data[user_id]:
            user_data[user_id]["date"] = text
            await update.message.reply_text("💰 Введите сумму расхода:")
        else:
            user_data[user_id]["expense"] = text
            expense_data = user_data.pop(user_id)
            expense_str = f"📅 {expense_data['date']} | 💰 Расход: {expense_data['expense']}"
            write_to_file(EXPENSES_FILE, expense_str)
            await update.message.reply_text(f"✅ Расход сохранен!\n\n{expense_str}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
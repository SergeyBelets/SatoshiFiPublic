#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import logging
import qrcode
import io
from urllib.parse import urlencode
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
DEVELOPER_ID = int(os.getenv('DEVELOPER_ID', 0))

def init_db():
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'pending',
        registered_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_of_week INTEGER,
        lesson_number INTEGER,
        start_time TEXT,
        subject TEXT,
        requirements TEXT,
        created_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS teacher_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_parent_id INTEGER,
        parent_name TEXT,
        message_text TEXT,
        received_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS parent_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        to_parent_id INTEGER,
        from_teacher_id INTEGER,
        teacher_name TEXT,
        message_text TEXT,
        sent_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sent_announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_teacher_id INTEGER,
        teacher_name TEXT,
        announcement_text TEXT,
        sent_at TIMESTAMP,
        recipients_count INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sent_homework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_teacher_id INTEGER,
        teacher_name TEXT,
        homework_text TEXT,
        sent_at TIMESTAMP,
        recipients_count INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS message_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_type TEXT,
        message_id INTEGER,
        recipient_id INTEGER,
        sent_successfully BOOLEAN,
        sent_at TIMESTAMP
    )''')
    # Платежные таблицы (упрощенные)
    c.execute('''CREATE TABLE IF NOT EXISTS money_collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        amount INTEGER NOT NULL,
        teacher_phone TEXT,
        purpose_code TEXT,
        deadline DATE,
        is_active BOOLEAN DEFAULT true,
        created_by INTEGER,
        created_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS parent_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collection_id INTEGER REFERENCES money_collections(id),
        parent_id INTEGER,
        parent_name TEXT,
        amount INTEGER,
        payment_method TEXT,
        status TEXT DEFAULT 'pending',
        payment_comment TEXT,
        paid_at TIMESTAMP,
        confirmed_by INTEGER,
        confirmed_at TIMESTAMP,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS teacher_payment_settings (
        teacher_id INTEGER PRIMARY KEY,
        phone_number TEXT,
        receive_notifications BOOLEAN DEFAULT true,
        updated_at TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_user_role(user_id):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE telegram_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_name(user_id):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT full_name, username FROM users WHERE telegram_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0] or result[1] or f"ID{user_id}"
    return f"ID{user_id}"

def get_main_menu(role):
    if role == 'developer':
        keyboard = [['👥 Пользователи', '📊 Статистика'], ['👨‍🏫 Управление', '📢 Рассылка']]
    elif role == 'teacher':
        keyboard = [
            ['📢 Создать объявление', '📚 Создать домашнее задание'],
            ['📢 Просмотр объявлений', '📚 Просмотр домашних заданий'],
            ['📋 Управление сообщениями', '📅 Расписание'],
            ['📊 Статистика класса', '💰 Сборы денег']
        ]
    elif role == 'parent':
        keyboard = [
            ['📢 Объявления', '📚 Домашние задания'], 
            ['📅 Расписание', '✍️ Написать учителю'],
            ['↩️ Ответить учителю', '💰 Мои сборы']
        ]
    else:
        return None
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_payment_menu(role):
    if role == 'teacher':
        keyboard = [
            ['💰 Создать сбор', '📊 Статистика сборов'],
            ['⏳ Ожидают подтверждения', '❌ Отклоненные'],
            ['⚙️ Настройка телефона', '📋 Все сборы'],
            ['🔙 Назад']
        ]
    elif role == 'parent':
        keyboard = [
            ['💳 К оплате', '✅ Оплаченные'],
            ['📊 История платежей'],
            ['🔙 Назад']
        ]
    else:
        return None
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def clear_user_context(context):
    context.user_data.pop('waiting_for', None)
    context.user_data.pop('selecting_parent', None)
    context.user_data.pop('parent_list', None)
    context.user_data.pop('target_parent_id', None)
    context.user_data.pop('messages_for_forwarding', None)
    context.user_data.pop('replying_to_teacher_id', None)
    context.user_data.pop('creating_collection', None)
    context.user_data.pop('setting_up_payment', None)
    context.user_data.pop('collection_title', None)
    context.user_data.pop('collection_description', None)
    context.user_data.pop('collection_amount', None)
    context.user_data.pop('temp_phone', None)

def generate_payment_comment_code(collection_id, parent_id):
    """Генерирует уникальный код для комментария к переводу"""
    return f"SB{collection_id:03d}{parent_id % 1000:03d}"

def generate_sbp_qr(phone, amount, purpose, comment_code):
    """Генерирует QR-код для СБП"""
    # Очищаем номер телефона от лишних символов
    clean_phone = ''.join(filter(str.isdigit, phone))
    if clean_phone.startswith('8'):
        clean_phone = '7' + clean_phone[1:]
    elif not clean_phone.startswith('7'):
        clean_phone = '7' + clean_phone
    
    sbp_url = f"https://qr.nspk.ru/AD10006M/{clean_phone}?amount={amount}&purpose={purpose}&comment={comment_code}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(sbp_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    clear_user_context(context)
    
    await update.message.reply_text(f"🆔 Ваш Telegram ID: {user_id}")
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE telegram_id = ?', (user_id,))
    existing = c.fetchone()
    
    if existing:
        role = existing[0]
    else:
        role = 'developer' if user_id == DEVELOPER_ID else 'pending'
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                  (user_id, user.username, user.full_name, role, datetime.now()))
        conn.commit()
        
        if role == 'pending' and DEVELOPER_ID != user_id:
            try:
                await context.bot.send_message(
                    DEVELOPER_ID,
                    f"🆕 Новый пользователь:\nID: {user_id}\nИмя: {user.full_name or 'Не указано'}\nUsername: @{user.username or 'нет'}\n\n/make_teacher {user_id} - назначить учителем\n/make_parent {user_id} - подтвердить родителя"
                )
            except:
                pass
    
    conn.close()
    
    if role == 'developer':
        await update.message.reply_text("Сброс меню...", reply_markup=ReplyKeyboardRemove())
        markup = get_main_menu('developer')
        text = "🎛 Админ-панель активна\nВы разработчик системы"
        await update.message.reply_text(text, reply_markup=markup)
    elif role == 'teacher':
        text = "👨‍🏫 Добро пожаловать, учитель!\nИспользуйте меню для управления классом"
        markup = get_main_menu('teacher')
        await update.message.reply_text(text, reply_markup=markup)
    elif role == 'parent':
        text = "👨‍👩‍👧 Добро пожаловать, родитель!\nВы будете получать объявления и домашние задания"
        markup = get_main_menu('parent')
        await update.message.reply_text(text, reply_markup=markup)
    else:
        text = "👋 Добро пожаловать!\nОжидайте подтверждения от администратора"
        await update.message.reply_text(text)

async def setup_teacher_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'teacher':
        return
    
    context.user_data['setting_up_payment'] = 'phone'
    await update.message.reply_text(
        "⚙️ Настройка телефона для СБП\n\n"
        "Введите ваш номер телефона (в формате +7xxxxxxxxxx или 8xxxxxxxxxx):"
    )

async def create_money_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'teacher':
        await update.message.reply_text("Только учитель может создавать сборы")
        return
    
    # Проверяем, настроен ли телефон
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT phone_number FROM teacher_payment_settings WHERE teacher_id = ?", (user_id,))
    payment_info = c.fetchone()
    conn.close()
    
    if not payment_info or not payment_info[0]:
        keyboard = [['⚙️ Настройка телефона'], ['🔙 Назад']]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Сначала нужно настроить ваш номер телефона для СБП",
            reply_markup=markup
        )
        return
    
    context.user_data['creating_collection'] = 'title'
    await update.message.reply_text("💰 Создание сбора денег\n\nВведите название (например: 'Экскурсия в планетарий'):")

async def send_payment_request_to_parents(context, collection_id):
    """Отправляет запрос на оплату всем родителям"""
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    # Получаем данные сбора
    c.execute("""SELECT title, description, amount, teacher_phone, purpose_code, deadline 
                 FROM money_collections WHERE id = ?""", (collection_id,))
    collection = c.fetchone()
    
    # Получаем всех родителей
    c.execute("SELECT telegram_id, full_name FROM users WHERE role = 'parent'")
    parents = c.fetchall()
    
    if not collection or not parents:
        conn.close()
        return 0
    
    title, desc, amount, teacher_phone, purpose_code, deadline = collection
    sent_count = 0
    
    for parent_id, parent_name in parents:
        try:
            # Создаем запись о платеже
            comment_code = generate_payment_comment_code(collection_id, parent_id)
            
            c.execute("""INSERT INTO parent_payments 
                        (collection_id, parent_id, parent_name, amount, payment_comment, status)
                        VALUES (?, ?, ?, ?, ?, 'pending')""",
                     (collection_id, parent_id, parent_name or "Родитель", amount, comment_code))
            
            # Формируем сообщение
            deadline_str = datetime.fromisoformat(deadline).strftime('%d.%m.%Y') if deadline else "не указан"
            
            message = f"💰 Сбор денег: {title}\n\n"
            if desc:
                message += f"📝 {desc}\n\n"
            message += f"💵 Сумма: {amount} рублей\n"
            message += f"📅 Срок: {deadline_str}\n\n"
            
            # Инструкции по СБП
            message += "💳 Оплата через СБП:\n\n"
            message += f"📱 Номер: {teacher_phone}\n"
            message += f"Сумма: {amount} руб\n"
            message += f"Комментарий: {comment_code}\n\n"
            message += f"⚠️ ОБЯЗАТЕЛЬНО указывайте комментарий: {comment_code}\n"
            message += "Это нужно для автоматического учета вашего платежа\n\n"
            message += "После оплаты нажмите кнопку 'Я оплатил'"
            
            # Кнопки
            keyboard = [
                [InlineKeyboardButton("📱 QR-код СБП", callback_data=f"qr_{collection_id}_{parent_id}")],
                [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{collection_id}_{parent_id}")],
                [InlineKeyboardButton("❌ Не могу оплатить", callback_data=f"cannot_pay_{collection_id}_{parent_id}")]
            ]
            
            markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(parent_id, message, reply_markup=markup)
            sent_count += 1
            
        except Exception as e:
            logger.error(f"Ошибка отправки сбора родителю {parent_id}: {e}")
    
    conn.commit()
    conn.close()
    return sent_count

async def show_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все платежи ожидающие подтверждения"""
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'teacher':
        return
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    c.execute("""SELECT pp.id, pp.parent_name, pp.amount, pp.payment_comment, 
                        mc.title, pp.paid_at
                 FROM parent_payments pp
                 JOIN money_collections mc ON pp.collection_id = mc.id
                 WHERE pp.status = 'paid' AND mc.created_by = ?
                 ORDER BY pp.paid_at DESC""", (user_id,))
    
    pending = c.fetchall()
    conn.close()
    
    if not pending:
        await update.message.reply_text("Нет платежей ожидающих подтверждения")
        return
    
    message = "⏳ Платежи ожидающие подтверждения:\n\n"
    keyboard = []
    
    # Кнопка подтвердить все
    if len(pending) > 1:
        keyboard.append([InlineKeyboardButton("✅ Подтвердить все", callback_data="confirm_all")])
        keyboard.append([InlineKeyboardButton("❌ Отклонить все", callback_data="reject_all")])
    
    for payment in pending:
        payment_id, parent_name, amount, comment, title, paid_at = payment
        paid_time = datetime.fromisoformat(paid_at).strftime('%d.%m %H:%M')
        
        message += f"💰 {parent_name}\n"
        message += f"📝 {title}\n"
        message += f"💵 {amount} руб.\n"
        message += f"🏷 {comment}\n"
        message += f"⏰ {paid_time}\n"
        
        # Кнопки для каждого платежа
        keyboard.append([
            InlineKeyboardButton(f"✅ {parent_name}", callback_data=f"confirm_single_{payment_id}"),
            InlineKeyboardButton(f"❌ {parent_name}", callback_data=f"reject_single_{payment_id}")
        ])
        
        message += "\n"
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_payments")])
    markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=markup)

async def show_rejected_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает отклоненные платежи"""
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'teacher':
        return
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    c.execute("""SELECT pp.parent_name, pp.amount, mc.title, pp.notes, pp.confirmed_at
                 FROM parent_payments pp
                 JOIN money_collections mc ON pp.collection_id = mc.id
                 WHERE pp.status = 'rejected' AND mc.created_by = ?
                 ORDER BY pp.confirmed_at DESC LIMIT 10""", (user_id,))
    
    rejected = c.fetchall()
    conn.close()
    
    if not rejected:
        await update.message.reply_text("Нет отклоненных платежей")
        return
    
    message = "❌ Отклоненные платежи:\n\n"
    
    for payment in rejected:
        parent_name, amount, title, notes, rejected_at = payment
        rejected_time = datetime.fromisoformat(rejected_at).strftime('%d.%m %H:%M')
        
        message += f"👤 {parent_name}\n"
        message += f"📝 {title}\n"
        message += f"💵 {amount} руб.\n"
        message += f"⏰ Отклонен: {rejected_time}\n"
        if notes:
            message += f"📄 Причина: {notes}\n"
        message += "\n"
    
    await update.message.reply_text(message)

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    if data == "confirm_all":
        # Подтверждаем все ожидающие платежи
        c.execute("""UPDATE parent_payments 
                    SET status = 'confirmed', confirmed_by = ?, confirmed_at = ?
                    WHERE status = 'paid' AND collection_id IN 
                    (SELECT id FROM money_collections WHERE created_by = ?)""",
                 (user_id, datetime.now().isoformat(), user_id))
        
        affected = c.rowcount
        await query.edit_message_text(f"✅ Подтверждены все платежи ({affected} шт.)")
    
    elif data == "reject_all":
        # Отклоняем все ожидающие платежи
        c.execute("""UPDATE parent_payments 
                    SET status = 'rejected', confirmed_by = ?, confirmed_at = ?, notes = 'Массовое отклонение'
                    WHERE status = 'paid' AND collection_id IN 
                    (SELECT id FROM money_collections WHERE created_by = ?)""",
                 (user_id, datetime.now().isoformat(), user_id))
        
        affected = c.rowcount
        await query.edit_message_text(f"❌ Отклонены все платежи ({affected} шт.)")
    
    elif data.startswith("confirm_single_"):
        payment_id = int(data.replace("confirm_single_", ""))
        
        # Получаем данные платежа
        c.execute("""SELECT pp.parent_name, pp.parent_id, mc.title 
                    FROM parent_payments pp
                    JOIN money_collections mc ON pp.collection_id = mc.id
                    WHERE pp.id = ?""", (payment_id,))
        payment_info = c.fetchone()
        
        if payment_info:
            parent_name, parent_id, title = payment_info
            
            # Подтверждаем платеж
            c.execute("""UPDATE parent_payments 
                        SET status = 'confirmed', confirmed_by = ?, confirmed_at = ?
                        WHERE id = ?""",
                     (user_id, datetime.now().isoformat(), payment_id))
            
            await query.edit_message_text(f"✅ Платеж от {parent_name} подтвержден")
            
            # Уведомляем родителя
            try:
                await context.bot.send_message(
                    parent_id,
                    f"✅ Ваш платеж подтвержден!\n\n📝 {title}\n💰 Сумма получена учителем"
                )
            except:
                pass
    
    elif data.startswith("reject_single_"):
        payment_id = int(data.replace("reject_single_", ""))
        
        # Получаем данные платежа
        c.execute("""SELECT pp.parent_name, pp.parent_id, mc.title 
                    FROM parent_payments pp
                    JOIN money_collections mc ON pp.collection_id = mc.id
                    WHERE pp.id = ?""", (payment_id,))
        payment_info = c.fetchone()
        
        if payment_info:
            parent_name, parent_id, title = payment_info
            
            # Отклоняем платеж
            c.execute("""UPDATE parent_payments 
                        SET status = 'rejected', confirmed_by = ?, confirmed_at = ?, notes = 'Отклонено учителем'
                        WHERE id = ?""",
                     (user_id, datetime.now().isoformat(), payment_id))
            
            await query.edit_message_text(f"❌ Платеж от {parent_name} отклонен")
            
            # Уведомляем родителя
            try:
                await context.bot.send_message(
                    parent_id,
                    f"❌ Ваш платеж отклонен\n\n📝 {title}\nОбратитесь к учителю для уточнения"
                )
            except:
                pass
    
    elif data.startswith("paid_"):
        # Родитель сообщает, что оплатил
        data_parts = data.split('_')
        collection_id = int(data_parts[1])
        parent_id = int(data_parts[2])
        
        c.execute("""UPDATE parent_payments 
                    SET status = 'paid', paid_at = ? 
                    WHERE collection_id = ? AND parent_id = ?""",
                 (datetime.now().isoformat(), collection_id, parent_id))
        
        # Получаем данные для уведомления учителя
        c.execute("""SELECT mc.title, pp.parent_name, pp.amount, pp.payment_comment
                    FROM money_collections mc 
                    JOIN parent_payments pp ON mc.id = pp.collection_id
                    WHERE mc.id = ? AND pp.parent_id = ?""",
                 (collection_id, parent_id))
        payment_info = c.fetchone()
        
        if payment_info:
            title, parent_name, amount, comment = payment_info
            
            # Уведомляем родителя
            await query.edit_message_text(
                f"✅ Спасибо! Ваш платеж отмечен как выполненный\n\n"
                f"💰 {title}\n"
                f"💵 {amount} руб.\n"
                f"🏷 Код: {comment}\n\n"
                f"Учитель подтвердит получение денег в ближайшее время"
            )
            
            # Уведомляем учителя
            await notify_teacher_about_payment(context, collection_id, parent_name, amount, comment, "paid")
    
    elif data.startswith("cannot_pay_"):
        # Родитель не может оплатить
        data_parts = data.split('_')
        collection_id = int(data_parts[2])
        parent_id = int(data_parts[3])
        
        c.execute("""UPDATE parent_payments 
                    SET status = 'cannot_pay', notes = 'Родитель не может оплатить'
                    WHERE collection_id = ? AND parent_id = ?""",
                 (collection_id, parent_id))
        
        await query.edit_message_text(
            "Мы отметили, что у вас трудности с оплатой. "
            "Учитель свяжется с вами для решения вопроса."
        )
        
        c.execute("SELECT parent_name FROM parent_payments WHERE collection_id = ? AND parent_id = ?",
                 (collection_id, parent_id))
        result = c.fetchone()
        parent_name = result[0] if result else "Неизвестный родитель"
        
        await notify_teacher_about_payment(context, collection_id, parent_name, 0, "", "cannot_pay")
    
    elif data.startswith("qr_"):
        # Отправляем QR-код для СБП
        data_parts = data.split('_')
        collection_id = int(data_parts[1])
        parent_id = int(data_parts[2])
        
        c.execute("""SELECT mc.title, mc.amount, mc.teacher_phone, pp.payment_comment
                    FROM money_collections mc 
                    JOIN parent_payments pp ON mc.id = pp.collection_id
                    WHERE mc.id = ? AND pp.parent_id = ?""",
                 (collection_id, parent_id))
        qr_info = c.fetchone()
        
        if qr_info:
            title, amount, phone, comment = qr_info
            try:
                qr_bio = generate_sbp_qr(phone, amount, title, comment)
                
                await context.bot.send_photo(
                    chat_id=query.from_user.id,
                    photo=qr_bio,
                    caption=f"📱 QR-код для оплаты через СБП\n\n{title}\n{amount} руб.\nКод: {comment}"
                )
            except Exception as e:
                logger.error(f"Ошибка генерации QR-кода: {e}")
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="Ошибка генерации QR-кода. Воспользуйтесь переводом по номеру телефона."
                )
    
    elif data == "back_to_payments":
        markup = get_payment_menu('teacher')
        await query.message.reply_text("💰 Управление сборами:", reply_markup=markup)
    
    conn.commit()
    conn.close()

async def notify_teacher_about_payment(context, collection_id, parent_name, amount, comment, action):
    """Уведомляет учителя о действиях родителей"""
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT created_by FROM money_collections WHERE id = ?", (collection_id,))
    teacher_result = c.fetchone()
    conn.close()
    
    if not teacher_result:
        return
    
    teacher_id = teacher_result[0]
    
    if action == "paid":
        message = f"💰 Новый платеж!\n\n"
        message += f"👤 {parent_name}\n"
        message += f"💵 {amount} руб.\n"
        message += f"🏷 Код: {comment}\n\n"
        message += f"Используйте меню 'Ожидают подтверждения' для управления платежами"
        markup = None
    else:
        message = f"⚠️ {parent_name} не может оплатить сбор"
        markup = None
    
    try:
        await context.bot.send_message(teacher_id, message, reply_markup=markup)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления учителю: {e}")

async def show_collection_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'teacher':
        return
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    c.execute("""SELECT mc.id, mc.title, mc.amount,
                        COUNT(CASE WHEN pp.status = 'confirmed' THEN 1 END) as confirmed,
                        COUNT(CASE WHEN pp.status = 'paid' THEN 1 END) as paid,
                        COUNT(CASE WHEN pp.status = 'cannot_pay' THEN 1 END) as cannot_pay,
                        COUNT(pp.id) as total,
                        SUM(CASE WHEN pp.status = 'confirmed' THEN pp.amount ELSE 0 END) as total_confirmed
                 FROM money_collections mc
                 LEFT JOIN parent_payments pp ON mc.id = pp.collection_id
                 WHERE mc.is_active = 1 AND mc.created_by = ?
                 GROUP BY mc.id, mc.title, mc.amount
                 ORDER BY mc.created_at DESC""", (user_id,))
    
    collections = c.fetchall()
    conn.close()
    
    if not collections:
        await update.message.reply_text("Активных сборов нет")
        return
    
    message = "📊 Статус сборов:\n\n"
    
    for collection in collections:
        coll_id, title, amount, confirmed, paid, cannot_pay, total, total_confirmed = collection
        pending = total - confirmed - paid - cannot_pay
        
        message += f"📝 {title}\n"
        message += f"💵 {amount} руб. с человека\n"
        message += f"✅ Подтверждено: {confirmed}/{total}\n"
        message += f"⏳ Ожидает подтверждения: {paid}\n"
        message += f"❌ Не могут оплатить: {cannot_pay}\n"
        message += f"⏸️ Не ответили: {pending}\n"
        message += f"💰 Собрано: {total_confirmed} руб.\n\n"
    
    await update.message.reply_text(message)

async def show_parent_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status_filter=None):
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'parent':
        return
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    query = """SELECT mc.title, pp.amount, pp.status, pp.payment_comment, 
                      mc.deadline, pp.paid_at, pp.confirmed_at
               FROM money_collections mc
               JOIN parent_payments pp ON mc.id = pp.collection_id
               WHERE pp.parent_id = ? AND mc.is_active = 1"""
    
    params = [user_id]
    
    if status_filter:
        if status_filter == 'pending':
            query += " AND pp.status = 'pending'"
        elif status_filter == 'paid':
            query += " AND pp.status IN ('paid', 'confirmed')"
    
    query += " ORDER BY mc.created_at DESC"
    
    c.execute(query, params)
    payments = c.fetchall()
    conn.close()
    
    if not payments:
        status_text = {
            'pending': 'к оплате',
            'paid': 'оплаченных'
        }.get(status_filter, '')
        
        await update.message.reply_text(f"Нет сборов {status_text}")
        return
    
    if status_filter == 'pending':
        message = "💳 Сборы к оплате:\n\n"
    elif status_filter == 'paid':
        message = "✅ Оплаченные сборы:\n\n"
    else:
        message = "📊 Все сборы:\n\n"
    
    for payment in payments:
        title, amount, status, comment, deadline, paid_at, confirmed_at = payment
        
        status_emoji = {
            'pending': '⏳',
            'paid': '💰',
            'confirmed': '✅',
            'cannot_pay': '❌'
        }.get(status, '❓')
        
        status_text = {
            'pending': 'Ожидает оплаты',
            'paid': 'Оплачено, ожидает подтверждения',
            'confirmed': 'Подтверждено учителем',
            'cannot_pay': 'Отмечено как невозможно оплатить'
        }.get(status, 'Неизвестный статус')
        
        message += f"{status_emoji} {title}\n"
        message += f"💵 {amount} руб.\n"
        message += f"📊 {status_text}\n"
        
        if deadline:
            deadline_date = datetime.fromisoformat(deadline).strftime('%d.%m.%Y')
            message += f"📅 Срок: {deadline_date}\n"
        
        if comment:
            message += f"🏷 Код: {comment}\n"
        
        message += "\n"
    
    await update.message.reply_text(message)

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    day_names = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    
    today_dow = today.weekday()
    c.execute("SELECT lesson_number, start_time, subject, requirements FROM schedule WHERE day_of_week = ? ORDER BY lesson_number", (today_dow,))
    today_lessons = c.fetchall()
    
    tomorrow_dow = tomorrow.weekday()
    c.execute("SELECT lesson_number, start_time, subject, requirements FROM schedule WHERE day_of_week = ? ORDER BY lesson_number", (tomorrow_dow,))
    tomorrow_lessons = c.fetchall()
    
    conn.close()
    
    def format_lessons(lessons):
        if not lessons:
            return "Уроков нет"
        formatted = ""
        for lesson in lessons:
            lesson_num, time_slot, subject, requirements = lesson
            req_text = f" ({requirements})" if requirements else ""
            formatted += f"{lesson_num}. {time_slot} - {subject}{req_text}\n"
        return formatted
    
    text = f"📅 СЕГОДНЯ - {day_names[today_dow]} ({today.strftime('%d.%m')}):\n"
    text += format_lessons(today_lessons)
    
    text += f"\n📅 ЗАВТРА - {day_names[tomorrow_dow]} ({tomorrow.strftime('%d.%m')}):\n"
    text += format_lessons(tomorrow_lessons)
    
    await update.message.reply_text(text)

async def show_sent_announcements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT id, teacher_name, announcement_text, sent_at, recipients_count FROM sent_announcements ORDER BY sent_at DESC LIMIT 10")
    announcements = c.fetchall()
    conn.close()
    
    if not announcements:
        await update.message.reply_text("📢 Отправленных объявлений пока нет")
        return
    
    text = "📢 Последние отправленные объявления:\n\n"
    
    for ann in announcements:
        ann_id, teacher_name, ann_text, sent_at, recipients = ann
        sent_time = datetime.fromisoformat(sent_at).strftime('%d.%m %H:%M')
        preview = (ann_text[:60] + '...') if len(ann_text) > 60 else ann_text
        text += f"🔹 ID{ann_id} | {teacher_name} ({sent_time})\n"
        text += f"Получателей: {recipients}\n"
        text += f"{preview}\n\n"
    
    await update.message.reply_text(text)

async def show_sent_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT id, teacher_name, homework_text, sent_at, recipients_count FROM sent_homework ORDER BY sent_at DESC LIMIT 10")
    homework_list = c.fetchall()
    conn.close()
    
    if not homework_list:
        await update.message.reply_text("📚 Отправленных домашних заданий пока нет")
        return
    
    text = "📚 Последние отправленные домашние задания:\n\n"
    
    for hw in homework_list:
        hw_id, teacher_name, hw_text, sent_at, recipients = hw
        sent_time = datetime.fromisoformat(sent_at).strftime('%d.%m %H:%M')
        preview = (hw_text[:60] + '...') if len(hw_text) > 60 else hw_text
        text += f"🔹 ID{hw_id} | {teacher_name} ({sent_time})\n"
        text += f"Получателей: {recipients}\n"
        text += f"{preview}\n\n"
    
    await update.message.reply_text(text)

async def teacher_messages_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['💬 Сообщения от родителей', '✉️ Написать родителю'],
        ['📤 Переслать сообщение'],
        ['🔙 Назад']
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('📋 Управление сообщениями:', reply_markup=markup)

async def show_parent_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT id, from_parent_id, parent_name, message_text, received_at FROM teacher_messages ORDER BY received_at DESC LIMIT 10")
    messages = c.fetchall()
    conn.close()
    
    if not messages:
        await update.message.reply_text("Нет сообщений от родителей")
        return
    
    text = "💬 Последние сообщения от родителей:\n\n"
    keyboard = []
    
    for msg in messages:
        msg_id, parent_id, parent_name, msg_text, received_at = msg
        received_time = datetime.fromisoformat(received_at).strftime('%d.%m %H:%M')
        preview = (msg_text[:50] + '...') if len(msg_text) > 50 else msg_text
        text += f"🔹 ID{msg_id} | {parent_name} ({received_time}):\n{preview}\n\n"
        keyboard.append([f"↩️ Ответить на ID{msg_id}"])
    
    keyboard.append(['🔙 Назад'])
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=markup)

async def show_teacher_messages_for_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT id, from_teacher_id, teacher_name, message_text, sent_at FROM parent_messages WHERE to_parent_id = ? ORDER BY sent_at DESC LIMIT 10", (user_id,))
    messages = c.fetchall()
    conn.close()
    
    if not messages:
        await update.message.reply_text("Нет сообщений от учителей")
        return
    
    text = "↩️ Последние сообщения от учителей:\n\n"
    keyboard = []
    
    for msg in messages:
        msg_id, teacher_id, teacher_name, msg_text, sent_at = msg
        sent_time = datetime.fromisoformat(sent_at).strftime('%d.%m %H:%M')
        preview = (msg_text[:50] + '...') if len(msg_text) > 50 else msg_text
        text += f"🔹 ID{msg_id} | {teacher_name} ({sent_time}):\n{preview}\n\n"
        keyboard.append([f"↩️ Ответить на ID{msg_id}"])
    
    keyboard.append(['🔙 Назад'])
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=markup)

async def select_parent_for_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, full_name, username FROM users WHERE role = 'parent' ORDER BY full_name")
    parents = c.fetchall()
    conn.close()
    
    if not parents:
        await update.message.reply_text("Нет зарегистрированных родителей")
        return
    
    text = "Выберите родителя для отправки сообщения:\n\n"
    keyboard = []
    
    for parent in parents:
        parent_id, full_name, username = parent
        name = full_name or username or f"ID{parent_id}"
        keyboard.append([f"📨 {name}"])
    
    keyboard.append(['🔙 Назад'])
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    context.user_data['selecting_parent'] = True
    context.user_data['parent_list'] = {parent[0]: parent[1] or parent[2] or f"ID{parent[0]}" for parent in parents}
    
    await update.message.reply_text(text, reply_markup=markup)

async def show_messages_for_forwarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT id, from_parent_id, parent_name, message_text, received_at FROM teacher_messages ORDER BY received_at DESC LIMIT 15")
    messages = c.fetchall()
    conn.close()
    
    if not messages:
        await update.message.reply_text("Нет сообщений от родителей для пересылки")
        return
    
    text = "📤 Выберите сообщение для пересылки всем родителям:\n\n"
    keyboard = []
    
    for msg in messages:
        msg_id, parent_id, parent_name, msg_text, received_at = msg
        received_time = datetime.fromisoformat(received_at).strftime('%d.%m %H:%M')
        preview = (msg_text[:40] + '...') if len(msg_text) > 40 else msg_text
        text += f"🔹 {parent_name} ({received_time}):\n{preview}\n\n"
        keyboard.append([f"📤 Переслать от {parent_name}"])
    
    keyboard.append(['🔙 Назад'])
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    context.user_data['messages_for_forwarding'] = {msg[2]: {'id': msg[0], 'parent_name': msg[2], 'text': msg[3]} for msg in messages}
    
    await update.message.reply_text(text, reply_markup=markup)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_role = get_user_role(user_id)
    
    if not user_role or user_role == 'pending':
        await update.message.reply_text("Ожидайте подтверждения от администратора")
        return
    
    waiting_for = context.user_data.get('waiting_for')
    creating_collection = context.user_data.get('creating_collection')
    setting_up_payment = context.user_data.get('setting_up_payment')
    
    # Проверка на кнопки меню во время ожидания ввода
    menu_buttons = ['📢 Создать объявление', '📚 Создать домашнее задание', '📢 Просмотр объявлений', 
                   '📚 Просмотр домашних заданий', '📋 Управление сообщениями', '📅 Расписание', 
                   '📊 Статистика класса', '💰 Сборы денег', '💬 Сообщения от родителей', '✉️ Написать родителю',
                   '📤 Переслать сообщение', '📢 Объявления', '📚 Домашние задания', 
                   '✍️ Написать учителю', '↩️ Ответить учителю', '💰 Мои сборы', '💰 Создать сбор',
                   '📊 Статистика сборов', '⚙️ Настройка телефона', '💳 К оплате', '✅ Оплаченные', 
                   '📊 История платежей', '📋 Все сборы', '⏳ Ожидают подтверждения', '❌ Отклоненные', '🔙 Назад']
    
    if (waiting_for or creating_collection or setting_up_payment) and text in menu_buttons:
        clear_user_context(context)
        await update.message.reply_text("❌ Операция отменена. Обрабатываю новую команду...")
    
    # Обработка настройки телефона
    if setting_up_payment == 'phone':
        # Очистка и валидация номера телефона
        clean_phone = ''.join(filter(str.isdigit, text))
        if len(clean_phone) == 11 and clean_phone.startswith('8'):
            clean_phone = '+7' + clean_phone[1:]
        elif len(clean_phone) == 11 and clean_phone.startswith('7'):
            clean_phone = '+' + clean_phone
        elif len(clean_phone) == 10:
            clean_phone = '+7' + clean_phone
        else:
            await update.message.reply_text("Неверный формат номера. Попробуйте еще раз:")
            return
        
        # Сохраняем телефон
        conn = sqlite3.connect('classroom.db')
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO teacher_payment_settings 
                    (teacher_id, phone_number, updated_at)
                    VALUES (?, ?, ?)""",
                 (user_id, clean_phone, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        # Подтверждение настройки
        message = f"✅ Номер телефона сохранен: {clean_phone}\n\nТеперь вы можете создавать сборы денег"
        
        clear_user_context(context)
        markup = get_payment_menu('teacher')
        await update.message.reply_text(message, reply_markup=markup)
        return
    
    # Обработка создания сбора
    if creating_collection:
        if creating_collection == 'title':
            context.user_data['collection_title'] = text
            context.user_data['creating_collection'] = 'description'
            await update.message.reply_text("Введите описание сбора (например: 'Автобус, входные билеты, обед'):")
            
        elif creating_collection == 'description':
            context.user_data['collection_description'] = text
            context.user_data['creating_collection'] = 'amount'
            await update.message.reply_text("Введите сумму с одного ребенка в рублях:")
            
        elif creating_collection == 'amount':
            try:
                amount = int(text)
                if amount <= 0:
                    await update.message.reply_text("Сумма должна быть больше 0. Введите корректную сумму:")
                    return
                    
                title = context.user_data.get('collection_title')
                description = context.user_data.get('collection_description')
                
                # Получаем телефон учителя
                conn = sqlite3.connect('classroom.db')
                c = conn.cursor()
                c.execute("SELECT phone_number FROM teacher_payment_settings WHERE teacher_id = ?", (user_id,))
                teacher_info = c.fetchone()
                
                if teacher_info:
                    phone = teacher_info[0]
                    purpose_code = f"SB{datetime.now().strftime('%m%d%H%M')}"
                    
                    c.execute("""INSERT INTO money_collections 
                                (title, description, amount, teacher_phone, purpose_code, is_active, created_by, created_at)
                                VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                             (title, description, amount, phone, purpose_code, user_id, datetime.now().isoformat()))
                    
                    collection_id = c.lastrowid
                    conn.commit()
                    conn.close()
                    
                    # Отправляем запрос родителям
                    sent_count = await send_payment_request_to_parents(context, collection_id)
                    
                    clear_user_context(context)
                    markup = get_payment_menu('teacher')
                    await update.message.reply_text(f"✅ Сбор '{title}' создан и отправлен {sent_count} родителям\nСумма: {amount} руб. с человека", reply_markup=markup)
                else:
                    conn.close()
                    await update.message.reply_text("Ошибка: не найден ваш телефон. Настройте его в меню.")
            except ValueError:
                await update.message.reply_text("Введите корректную сумму (только цифры):")
        return
    
    # ОБРАБОТКА ОТВЕТА РОДИТЕЛЯ УЧИТЕЛЮ
    if waiting_for == 'replying_to_teacher' and user_role == 'parent':
        target_teacher_id = context.user_data.get('replying_to_teacher_id')
        parent_name = get_user_name(user_id)
        
        if target_teacher_id:
            try:
                await context.bot.send_message(target_teacher_id, f"↩️ Ответ родителя {parent_name}:\n\n{text}")
                await update.message.reply_text("✅ Ваш ответ отправлен учителю")
            except:
                await update.message.reply_text("❌ Не удалось отправить ответ")
            
            clear_user_context(context)
        return
    
    # Ответ родителя на конкретное сообщение учителя
    if text.startswith('↩️ Ответить на ID') and user_role == 'parent':
        try:
            msg_id = int(text.replace('↩️ Ответить на ID', ''))
            
            conn = sqlite3.connect('classroom.db')
            c = conn.cursor()
            c.execute("SELECT from_teacher_id, teacher_name, message_text FROM parent_messages WHERE id = ? AND to_parent_id = ?", (msg_id, user_id))
            message_data = c.fetchone()
            conn.close()
            
            if message_data:
                teacher_id, teacher_name, original_text = message_data
                preview = (original_text[:100] + '...') if len(original_text) > 100 else original_text
                
                context.user_data['waiting_for'] = 'replying_to_teacher'
                context.user_data['replying_to_teacher_id'] = teacher_id
                
                await update.message.reply_text(f"↩️ Отвечаю на сообщение от {teacher_name}:\n\n> {preview}\n\nВведите ваш ответ:")
            else:
                await update.message.reply_text("❌ Сообщение не найдено")
        except:
            await update.message.reply_text("❌ Ошибка при обработке ответа")
        return
    
    # Обработка выбора родителя для личного сообщения
    if context.user_data.get('selecting_parent') and text.startswith('📨'):
        parent_name = text.replace('📨 ', '')
        parent_list = context.user_data.get('parent_list', {})
        
        selected_parent_id = None
        for parent_id, name in parent_list.items():
            if name == parent_name:
                selected_parent_id = parent_id
                break
        
        if selected_parent_id:
            context.user_data['waiting_for'] = 'personal_message'
            context.user_data['target_parent_id'] = selected_parent_id
            context.user_data.pop('selecting_parent', None)
            context.user_data.pop('parent_list', None)
            await update.message.reply_text(f"Напишите сообщение для родителя {parent_name}:")
            return
    
    # Обработка пересылки сообщений
    if text.startswith('📤 Переслать от '):
        parent_name = text.replace('📤 Переслать от ', '')
        messages_for_forwarding = context.user_data.get('messages_for_forwarding', {})
        
        if parent_name in messages_for_forwarding:
            msg_info = messages_for_forwarding[parent_name]
            original_text = msg_info['text']
            
            conn = sqlite3.connect('classroom.db')
            c = conn.cursor()
            c.execute("SELECT telegram_id FROM users WHERE role = 'parent'")
            parents = c.fetchall()
            conn.close()
            
            sent_count = 0
            for parent in parents:
                try:
                    await context.bot.send_message(parent[0], f"📤 Пересланное сообщение от родителя {parent_name}:\n\n{original_text}")
                    sent_count += 1
                except:
                    pass
            
            await update.message.reply_text(f"✅ Сообщение от {parent_name} переслано {sent_count} родителям")
            clear_user_context(context)
            return
    
    # Ответ учителя на сообщение родителя
    if text.startswith('↩️ Ответить на ID') and user_role == 'teacher':
        try:
            msg_id = int(text.replace('↩️ Ответить на ID', ''))
            
            conn = sqlite3.connect('classroom.db')
            c = conn.cursor()
            c.execute("SELECT from_parent_id, parent_name, message_text FROM teacher_messages WHERE id = ?", (msg_id,))
            message_data = c.fetchone()
            conn.close()
            
            if message_data:
                parent_id, parent_name, original_text = message_data
                preview = (original_text[:100] + '...') if len(original_text) > 100 else original_text
                
                context.user_data['waiting_for'] = 'replying_to_message'
                context.user_data['target_parent_id'] = parent_id
                
                await update.message.reply_text(f"↩️ Отвечаю на сообщение от {parent_name}:\n\n> {preview}\n\nВведите ваш ответ:")
            else:
                await update.message.reply_text("❌ Сообщение не найдено")
        except:
            await update.message.reply_text("❌ Ошибка при обработке ответа")
        return
    
    # Обработка ввода текста для различных функций
    if waiting_for == 'announcement' and user_role == 'teacher':
        teacher_name = get_user_name(user_id)
        conn = sqlite3.connect('classroom.db')
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users WHERE role = 'parent'")
        parents = c.fetchall()
        
        # Сохраняем объявление в базу
        c.execute("INSERT INTO sent_announcements (from_teacher_id, teacher_name, announcement_text, sent_at, recipients_count) VALUES (?, ?, ?, ?, ?)",
                  (user_id, teacher_name, text, datetime.now().isoformat(), len(parents)))
        announcement_id = c.lastrowid
        conn.commit()
        
        sent_count = 0
        for parent in parents:
            try:
                await context.bot.send_message(parent[0], f"📢 Объявление от учителя {teacher_name}:\n\n{text}")
                c.execute("INSERT INTO message_recipients (message_type, message_id, recipient_id, sent_successfully, sent_at) VALUES (?, ?, ?, ?, ?)",
                         ('announcement', announcement_id, parent[0], True, datetime.now().isoformat()))
                sent_count += 1
            except:
                c.execute("INSERT INTO message_recipients (message_type, message_id, recipient_id, sent_successfully, sent_at) VALUES (?, ?, ?, ?, ?)",
                         ('announcement', announcement_id, parent[0], False, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Объявление отправлено {sent_count} из {len(parents)} родителям")
        clear_user_context(context)
        return
        
    elif waiting_for == 'homework' and user_role == 'teacher':
        teacher_name = get_user_name(user_id)
        conn = sqlite3.connect('classroom.db')
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users WHERE role = 'parent'")
        parents = c.fetchall()
        
        # Сохраняем домашнее задание в базу
        c.execute("INSERT INTO sent_homework (from_teacher_id, teacher_name, homework_text, sent_at, recipients_count) VALUES (?, ?, ?, ?, ?)",
                  (user_id, teacher_name, text, datetime.now().isoformat(), len(parents)))
        homework_id = c.lastrowid
        conn.commit()
        
        sent_count = 0
        for parent in parents:
            try:
                await context.bot.send_message(parent[0], f"📚 Домашнее задание от учителя {teacher_name}:\n\n{text}")
                c.execute("INSERT INTO message_recipients (message_type, message_id, recipient_id, sent_successfully, sent_at) VALUES (?, ?, ?, ?, ?)",
                         ('homework', homework_id, parent[0], True, datetime.now().isoformat()))
                sent_count += 1
            except:
                c.execute("INSERT INTO message_recipients (message_type, message_id, recipient_id, sent_successfully, sent_at) VALUES (?, ?, ?, ?, ?)",
                         ('homework', homework_id, parent[0], False, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Домашнее задание отправлено {sent_count} из {len(parents)} родителям")
        clear_user_context(context)
        return
    
    elif waiting_for == 'personal_message' and user_role == 'teacher':
        teacher_name = get_user_name(user_id)
        target_parent_id = context.user_data.get('target_parent_id')
        
        if target_parent_id:
            try:
                await context.bot.send_message(target_parent_id, f"📨 Личное сообщение от учителя {teacher_name}:\n\n{text}")
                
                # Сохраняем сообщение для возможности ответа
                conn = sqlite3.connect('classroom.db')
                c = conn.cursor()
                c.execute("INSERT INTO parent_messages (to_parent_id, from_teacher_id, teacher_name, message_text, sent_at) VALUES (?, ?, ?, ?, ?)",
                         (target_parent_id, user_id, teacher_name, f"📨 Личное сообщение: {text}", datetime.now().isoformat()))
                conn.commit()
                conn.close()
                
                await update.message.reply_text("✅ Личное сообщение отправлено родителю")
            except:
                await update.message.reply_text("❌ Не удалось отправить сообщение")
            
            clear_user_context(context)
        return
    
    elif waiting_for == 'replying_to_message' and user_role == 'teacher':
        target_parent_id = context.user_data.get('target_parent_id')
        teacher_name = get_user_name(user_id)
        
        if target_parent_id:
            try:
                await context.bot.send_message(target_parent_id, f"↩️ Ответ учителя {teacher_name}:\n\n{text}")
                
                # Сохраняем ответ для возможности дальнейшего ответа
                conn = sqlite3.connect('classroom.db')
                c = conn.cursor()
                c.execute("INSERT INTO parent_messages (to_parent_id, from_teacher_id, teacher_name, message_text, sent_at) VALUES (?, ?, ?, ?, ?)",
                         (target_parent_id, user_id, teacher_name, f"↩️ Ответ: {text}", datetime.now().isoformat()))
                conn.commit()
                conn.close()
                
                await update.message.reply_text("✅ Ответ отправлен родителю")
            except:
                await update.message.reply_text("❌ Не удалось отправить ответ")
            
            clear_user_context(context)
        return
        
    elif waiting_for == 'message_to_teacher' and user_role == 'parent':
        user_name = update.effective_user.full_name or update.effective_user.username or str(user_id)
        
        conn = sqlite3.connect('classroom.db')
        c = conn.cursor()
        c.execute("INSERT INTO teacher_messages (from_parent_id, parent_name, message_text, received_at) VALUES (?, ?, ?, ?)",
                  (user_id, user_name, text, datetime.now().isoformat()))
        c.execute("SELECT telegram_id FROM users WHERE role = 'teacher'")
        teachers = c.fetchall()
        conn.commit()
        conn.close()
        
        for teacher in teachers:
            try:
                await context.bot.send_message(teacher[0], f"✍️ Сообщение от родителя {user_name}:\n\n{text}\n\n(ID: {user_id})")
            except:
                pass
        
        await update.message.reply_text("✅ Ваше сообщение отправлено учителю")
        clear_user_context(context)
        return

    # Обработка кнопок меню
    if user_role == 'teacher':
        if text == '📢 Создать объявление':
            clear_user_context(context)
            context.user_data['waiting_for'] = 'announcement'
            await update.message.reply_text("📢 Создание объявления\n\nОтправьте текст объявления:")
        elif text == '📚 Создать домашнее задание':
            clear_user_context(context)
            context.user_data['waiting_for'] = 'homework'
            await update.message.reply_text("📚 Домашнее задание\n\nОтправьте текст домашнего задания:")
        elif text == '💰 Сборы денег':
            clear_user_context(context)
            markup = get_payment_menu('teacher')
            await update.message.reply_text("💰 Управление сборами:", reply_markup=markup)
        elif text == '💰 Создать сбор':
            clear_user_context(context)
            await create_money_collection(update, context)
        elif text == '📊 Статистика сборов':
            clear_user_context(context)
            await show_collection_status(update, context)
        elif text == '⚙️ Настройка телефона':
            clear_user_context(context)
            await setup_teacher_payment_info(update, context)
        elif text == '⏳ Ожидают подтверждения':
            clear_user_context(context)
            await show_pending_payments(update, context)
        elif text == '❌ Отклоненные':
            clear_user_context(context)
            await show_rejected_payments(update, context)
        elif text == '📋 Все сборы':
            clear_user_context(context)
            # Показываем все сборы с подробностями
            conn = sqlite3.connect('classroom.db')
            c = conn.cursor()
            c.execute("""SELECT mc.title, mc.description, mc.amount, mc.created_at
                         FROM money_collections mc
                         WHERE mc.created_by = ? AND mc.is_active = 1
                         ORDER BY mc.created_at DESC""", (user_id,))
            collections = c.fetchall()
            conn.close()
            
            if not collections:
                await update.message.reply_text("У вас нет активных сборов")
            else:
                message = "📋 Все ваши сборы:\n\n"
                for title, desc, amount, created_at in collections:
                    created_date = datetime.fromisoformat(created_at).strftime('%d.%m.%Y')
                    message += f"💰 {title}\n"
                    if desc:
                        message += f"📝 {desc}\n"
                    message += f"💵 {amount} руб.\n"
                    message += f"📅 Создан: {created_date}\n\n"
                await update.message.reply_text(message)
        elif text == '📢 Просмотр объявлений':
            clear_user_context(context)
            await show_sent_announcements(update, context)
        elif text == '📚 Просмотр домашних заданий':
            clear_user_context(context)
            await show_sent_homework(update, context)
        elif text == '📋 Управление сообщениями':
            clear_user_context(context)
            await teacher_messages_menu(update, context)
        elif text == '📅 Расписание':
            clear_user_context(context)
            await show_schedule(update, context)
        elif text == '📊 Статистика класса':
            clear_user_context(context)
            conn = sqlite3.connect('classroom.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users WHERE role = 'parent'")
            parents = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'")
            teachers = c.fetchone()[0]
            conn.close()
            await update.message.reply_text(f"📊 Статистика:\nРодителей: {parents}\nУчителей: {teachers}")
        elif text == '💬 Сообщения от родителей':
            clear_user_context(context)
            await show_parent_messages(update, context)
        elif text == '✉️ Написать родителю':
            clear_user_context(context)
            await select_parent_for_message(update, context)
        elif text == '📤 Переслать сообщение':
            clear_user_context(context)
            await show_messages_for_forwarding(update, context)
        elif text == '🔙 Назад':
            clear_user_context(context)
            markup = get_main_menu('teacher')
            await update.message.reply_text("👨‍🏫 Главное меню:", reply_markup=markup)
    
    elif user_role == 'parent':
        if text == '📢 Объявления':
            clear_user_context(context)
            await update.message.reply_text("📢 Здесь отображаются объявления от учителя")
        elif text == '📚 Домашние задания':
            clear_user_context(context)
            await update.message.reply_text("📚 Здесь отображаются домашние задания")
        elif text == '✍️ Написать учителю':
            clear_user_context(context)
            context.user_data['waiting_for'] = 'message_to_teacher'
            await update.message.reply_text("✍️ Напишите ваше сообщение учителю:")
        elif text == '↩️ Ответить учителю':
            clear_user_context(context)
            await show_teacher_messages_for_parent(update, context)
        elif text == '📅 Расписание':
            clear_user_context(context)
            await show_schedule(update, context)
        elif text == '💰 Мои сборы':
            clear_user_context(context)
            markup = get_payment_menu('parent')
            await update.message.reply_text("💰 Мои платежи:", reply_markup=markup)
        elif text == '💳 К оплате':
            clear_user_context(context)
            await show_parent_payment_status(update, context, 'pending')
        elif text == '✅ Оплаченные':
            clear_user_context(context)
            await show_parent_payment_status(update, context, 'paid')
        elif text == '📊 История платежей':
            clear_user_context(context)
            await show_parent_payment_status(update, context)
        elif text == '🔙 Назад':
            clear_user_context(context)
            markup = get_main_menu('parent')
            await update.message.reply_text('👨‍👩‍👧 Главное меню:', reply_markup=markup)
    
    elif user_role == 'developer':
        if text in ['👥 Пользователи', '📊 Статистика']:
            clear_user_context(context)
            await admin_panel(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        return
    
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    stats = c.fetchall()
    conn.close()
    
    text = "🎛 Панель управления\n\nСтатистика:\n"
    for role, count in stats:
        text += f"• {role}: {count}\n"
    
    await update.message.reply_text(text)

async def make_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID or not context.args:
        return
    
    target_id = int(context.args[0])
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("UPDATE users SET role = 'teacher' WHERE telegram_id = ?", (target_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Пользователь {target_id} назначен учителем")
    try:
        await context.bot.send_message(target_id, "🎉 Вы назначены учителем!\nНажмите /start для обновления меню.")
    except:
        pass

async def make_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID or not context.args:
        return
    
    target_id = int(context.args[0])
    conn = sqlite3.connect('classroom.db')
    c = conn.cursor()
    c.execute("UPDATE users SET role = 'parent' WHERE telegram_id = ?", (target_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Пользователь {target_id} подтвержден как родитель")
    try:
        await context.bot.send_message(target_id, "🎉 Вы подтверждены как родитель!\nНажмите /start для обновления меню.")
    except:
        pass

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("make_teacher", make_teacher))
    app.add_handler(CommandHandler("make_parent", make_parent))
    app.add_handler(CallbackQueryHandler(handle_payment_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    logger.info(f"Bot starting... Developer ID: {DEVELOPER_ID}")
    app.run_polling()

if __name__ == '__main__':
    main()

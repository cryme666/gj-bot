import telebot, os
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from csv_utils import *

load_dotenv()

admins = os.getenv('admins').split(',')
API_KEY = os.getenv('API_KEY')
bot = telebot.TeleBot(API_KEY)

user_orders = {}
user_comments = {}  

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    
    btn_products = InlineKeyboardButton("Переглянути продукти", callback_data='view_products')
    markup.add(btn_products)
    
    bot.send_message(message.chat.id, 'Привіт! Оберіть одну з опцій:', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'view_products')
def handle_view_products_callback(call):
    products = get_products()
    text = 'Наявні позиції:'
    
    markup = InlineKeyboardMarkup()
    
    for num, product in enumerate(products, 1):
        text += f"\n{num}) {product['name']} - {product['price']} грн"
        
        button = InlineKeyboardButton(f"Обрати {product['name']}", callback_data=f"select_{num}_1")
        markup.add(button)

    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def handle_quantity_selection(call):
    _, product_num, quantity = call.data.split('_')
    product_num = int(product_num)
    quantity = int(quantity)

    products = get_products()
    product = products[product_num - 1]

    if call.from_user.id not in user_orders:
        user_orders[call.from_user.id] = {}
    

    user_orders[call.from_user.id][product_num] = {'product': product, 'quantity': quantity}


    markup = InlineKeyboardMarkup()
    btn_increase = InlineKeyboardButton("+1", callback_data=f"select_{product_num}_{quantity + 1}")
    btn_decrease = InlineKeyboardButton("-1", callback_data=f"select_{product_num}_{max(1, quantity - 1)}")
    btn_back = InlineKeyboardButton("Повернутися до продуктів", callback_data="view_products")
    btn_confirm = InlineKeyboardButton("Зробити замовлення", callback_data="confirm_order")
    markup.add(btn_increase, btn_decrease)
    markup.add(btn_back)
    markup.add(btn_confirm)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Ви обрали {product['name']} у кількості: {quantity}",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'confirm_order')
def confirm_order(call):
   
    orders = user_orders.get(call.from_user.id, {})

    if orders:
        text = "Підтвердження замовлення:\n"
        total_price = 0
        for order in orders.values():
            product = order['product']
            quantity = order['quantity']
            price = int(product['price']) * quantity
            total_price += price
            text += f"{product['name']} - {quantity} шт. на {price} грн\n"

        text += f"\nЗагальна вартість: {total_price} грн"
        
        markup = InlineKeyboardMarkup()
        btn_add_comment = InlineKeyboardButton("Додати коментар", callback_data="add_comment")
        btn_confirm = InlineKeyboardButton("Підтвердити замовлення", callback_data="finalize_order")
        markup.add(btn_add_comment)
        markup.add(btn_confirm)
        
    
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == 'add_comment')
def add_comment(call):
    msg = bot.send_message(call.message.chat.id, 'Будь ласка, напишіть свій коментар до замовлення:')
    bot.register_next_step_handler(msg, save_comment, call)

def save_comment(message, call):
    user_comments[message.from_user.id] = message.text
    
    bot.send_message(message.chat.id, 'Ваш коментар збережено!')

    confirm_order(call)


@bot.callback_query_handler(func=lambda call: call.data == 'finalize_order')
def finalize_order(call):
   
    orders = user_orders.pop(call.from_user.id, None)
    comment = user_comments.pop(call.from_user.id, "")

    if orders:
        text = "Нове замовлення:\n"
        total_price = 0
        for order in orders.values():
            product = order['product']
            quantity = order['quantity']
            price = int(product['price']) * quantity
            total_price += price
            text += f"{product['name']} - {quantity} шт. на {price} грн\n"

        text += f"\nЗагальна вартість: {total_price} грн\nВід @{call.from_user.username}"
        
        if comment:
            text += f"\nКоментар: {comment}"

        for admin in admins:
            bot.send_message(admin, text)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='Ваше замовлення прийнято! ✅'
        )

def bot_start():
    bot.send_message(admins[0],'Бот запущений')
    bot.polling(non_stop=True)

if __name__ == '__main__':
    bot_start()
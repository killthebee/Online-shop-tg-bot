from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler,
                            ConversationHandler, Filters, MessageHandler)
import logging
import redis
import requests
import json
import time
import redis_db as rdb
from functools import partial
import os

STORE, PRODUCT, CONFIRMATION, INCART, EMAIL_INFO, PHONE_INFO, CONFIRM_INFO = range(7)


def fetch_bearer_token():

    client_id = os.environ.get['CLIENT_ID']
    data = {
      'client_id': client_id,
      'grant_type': 'implicit'
    }
    url = 'https://api.moltin.com/oauth/access_token'
    response = requests.post(url, data=data).json()
    token = response['access_token']
    return token


def start(update, context, r):

    keyboard = [
        [InlineKeyboardButton("Ivan fish", callback_data='fish1')],
        [InlineKeyboardButton("Efim fish", callback_data='fish2')],
        [InlineKeyboardButton("Gleb fish", callback_data='fish3')],
        [InlineKeyboardButton("Oleg fish", callback_data='fish4')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        user_id = update.message.from_user.id
        r.set(user_id, 'start stage')
        update.message.reply_text(
        'Пожалуйста, выберете товар',
        reply_markup=reply_markup
    )

    elif update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        r.set(user_id, 'cart stage')
        bot = context.bot
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        bot.send_message(
            chat_id=query.message.chat_id,
            text='Пожалуйста, выберете товар',
            reply_markup=reply_markup,
         )
    return STORE


def fetch_product_info(sku):

    sku_to_prod_id_dict = {
        'fish4': '31237b58-a1ca-405e-8114-9b60a9415b57',
        'fish3': 'a43ab362-f172-4593-948a-4a6ef4277b84',
        'fish2': '3eca7f83-14f1-4df1-ac5b-51bd0bc01746',
        'fish1': '97d1ae83-f80d-48cb-9511-4bfca0d77054',
    }
    prod_id = sku_to_prod_id_dict[sku]
    token = fetch_bearer_token()
    headers = {'Authorization': 'Bearer %s'%(token)}

    url = 'https://api.moltin.com/v2/products/%s'%(prod_id)
    response = requests.get(url, headers=headers).json()
    product_data = response['data']
    name = product_data['name']
    price = '%s$ for 1pc'%(product_data['price'][0]['amount']*0.01)
    stock = '%s pcs on stock'%(product_data['meta']['stock']['level'])
    description = product_data['description']
    media_id = product_data['relationships']['main_image']['data']['id']
    url = 'https://api.moltin.com/v2/files/%s'%(media_id)
    response = requests.get(url, headers=headers).json()
    photo_url = response['data']['link']['href']
    product_info = {
        'name': name,
        'price': price,
        'stock': stock,
        'description': description,
        'photo_url': photo_url,
    }
    return product_info


def make_product_page(update, context):

    query = update.callback_query
    bot = context.bot
    sku = str(query.data)
    keyboard = [
        [InlineKeyboardButton("5 pcs", callback_data='05%s'%(sku)),
        InlineKeyboardButton("10 pcs", callback_data='10%s'%(sku)),
        InlineKeyboardButton("15 pcs", callback_data='15%s'%(sku))],
        [InlineKeyboardButton("В корзину", callback_data='CART')],
        [InlineKeyboardButton("НАЗАД", callback_data='FALLBACK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    product_info = fetch_product_info(sku)
    text = '%s\n\n%s\n%s\n\n%s'%(
        product_info['name'],
        product_info['price'],
        product_info['stock'],
        product_info['description'],
    )

    bot.delete_message(
         chat_id=query.message.chat_id,
         message_id=query.message.message_id,
    )
    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=product_data['photo_url'],
        caption=text,
        reply_markup=reply_markup,
    )
    return PRODUCT


def confirm(update, context):

    query = update.callback_query
    bot = context.bot
    pcs = str(query.data)[0:2]
    sku = str(query.data)[2:]
    keyboard = [
        [InlineKeyboardButton("Добавить в корзину", callback_data='ADD%s%s'%(pcs, sku)),
         InlineKeyboardButton("Отмена", callback_data='FALLBACK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = 'Добавить в корзину %s штук?'%(pcs)
    bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
         )
    return CONFIRMATION


def add_to_cart(update, context):

    query = update.callback_query
    bot = context.bot
    user_id = query.from_user.id
    pcs = int(query.data[3:5])
    sku = query.data[5:]
    sku_to_prod_id_dict = {
        'fish4': '31237b58-a1ca-405e-8114-9b60a9415b57',
        'fish3': 'a43ab362-f172-4593-948a-4a6ef4277b84',
        'fish2': '3eca7f83-14f1-4df1-ac5b-51bd0bc01746',
        'fish1': '97d1ae83-f80d-48cb-9511-4bfca0d77054',
    }
    prod_id = sku_to_prod_id_dict[sku]
    token = fetch_bearer_token()
    headers = {
        'Authorization': 'Bearer %s'%(token),
        'Content-type': 'application/json; charset=utf-8',
        }

    data = {'data':
        {
            'id':prod_id,
            'type':'cart_item',
            'quantity':pcs,
        }
    }
    data_json = json.dumps(data)
    url = 'https://api.moltin.com/v2/carts/%s/items'%(user_id)
    response = requests.post(url=url, headers=headers, data=data_json)
    bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text='готово',
    )
    time.sleep(1)
    bot.delete_message(
         chat_id=query.message.chat_id,
         message_id=query.message.message_id,
    )
    return PRODUCT


def cancel(update, context):

    query = update.callback_query
    bot = context.bot
    bot.delete_message(
         chat_id=query.message.chat_id,
         message_id=query.message.message_id,
    )
    return PRODUCT


def cart_handler(update, context, r):

    query = update.callback_query
    bot = context.bot
    user_id = query.from_user.id
    r.set(user_id, 'cart stage')
    token = fetch_bearer_token()
    headers = headers = {
        'Authorization': 'Bearer %s'%(token),
    }

    if query.data.startswith('delete'):

        prod_id = query.data[6:]
        url = 'https://api.moltin.com/v2/carts/%s/items/%s'%(user_id, prod_id)
        response = requests.delete(url=url, headers=headers)

    url = 'https://api.moltin.com/v2/carts/%s/items'%(user_id).json()
    response = requests.get(url=url, headers=headers)
    keyboard = [
        [InlineKeyboardButton('Оплатить', callback_data='PAY')],
        [InlineKeyboardButton('В меню', callback_data='FALLBACK')]
    ]
    items = response['data']
    total_value = 0
    text = ''
    for item_data in items:

        name_row = item_data['name']
        description_row = item_data['description']
        price = item_data['unit_price']['amount']/100
        price_row = '$%s per piece'%(price)
        quantity = item_data['quantity']
        total_value_of_item = round(quantity * price, 2)
        quantity_row = '%spc/pcs in cart for $%s'%(quantity, total_value_of_item)

        additional_text = '%s\n%s\n%s\n%s\n\n\n'%(
            name_row,
            description_row,
            price_row,
            quantity_row,
        )
        text = text + additional_text
        total_value = total_value + total_value_of_item
        inline_keyboard_button_text = 'Удалить %s'%(name_row)

        callback_data = 'delete%s'%(item_data['id'])
        delete_button = [InlineKeyboardButton(inline_keyboard_button_text, callback_data=callback_data)]
        keyboard.insert(-2, delete_button)

    text = text + 'Total: $%s'%(total_value)

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.delete_message(
         chat_id=query.message.chat_id,
         message_id=query.message.message_id,
    )
    bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    return INCART


def ask_for_user_email(update, context, r):

    query = update.callback_query
    user_id = query.from_user.id
    r.set(user_id, 'cart stage')
    bot = context.bot
    bot.send_message(
        chat_id=query.message.chat_id,
        text='пожалуйста, пришлите ваш емеил'
    )
    return EMAIL_INFO


def handle_email(update, context, r):

    user_message = update.message.text
    user_id = update.message.from_user.id
    if '@' in user_message and '.' in user_message:
        text = 'Пожалуйста, пришлите ваш телефон'
        update.message.reply_text(text)
        first_name = user.first_name
        last_name = user.last_name
        name = '%s %s'%(first_name, last_name)

        token = fetch_bearer_token()
        headers = {
            'Authorization': 'Bearer %s'%(token),
            'Content-Type': 'application/json',
        }
        url = 'https://api.moltin.com/v2/customers'
        data = { 'data': {
               "type": "customer",
               "name": name,
               "email": user_message,
               }
        }
        data_json = json.dumps(data)
        response = requests.post(url, headers=headers, data=data_json).json()
        try:
            response['error']
            text = 'Имеил не распознан, попробуйте отправить имеил ещё раз!'
            update.message.reply_text(text)
            return EMAIL_INFO
        except KeyError:
            key_for_client_email = 'client_%s'%(user_id)
            r.set(key_for_client_email, user_message)
            return PHONE_INFO
    else:
        text = 'Имеил не распознан, попробуйте отправить имеил ещё раз!'
        update.message.reply_text(text)


def handle_phone(update, context, r):

    user_message = update.message.text
    user_id = update.message.from_user.id
    key_for_client_email = 'client_%s'%(user_id)
    client_email = r.get(key_for_client_email)
    try:
        int(user_message)
    except ValueError:
        text = 'Телефон не распознан, попробуйте отправить его ещё раз!'
        update.message.reply_text(text)
    if ((user_message.startswith('8') or user_message.startswith('+7')) and
        (len(user_message) == 11 or len(user_message) == 12)):

            keyboard = [
                [InlineKeyboardButton('Верно', callback_data='RIGHT')],
                [InlineKeyboardButton('Не верно', callback_data='WRONG')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = 'Ваш email: %s\nВаш телефон: %s'%(client_email, user_message)
            update.message.reply_text(text, reply_markup=reply_markup)
            return CONFIRM_INFO
    else:
        text = 'Телефон не распознан, попробуйте отправить его ещё раз!'
        update.message.reply_text(text)


def confirm_info(update, context):

    query = update.callback_query
    bot = context.bot
    if query.data == 'RIGHT':
        bot.send_message(
            chat_id=query.message.chat_id,
            text='Спасибо, с вами скоро свяжутся!',
        )
        return ConversationHandler.END
    elif query.data == 'WRONG':
        bot.send_message(
            chat_id=query.message.chat_id,
            text='Пожалуйста, пришлите ваш емеил',
        )
        return EMAIL_INFO


def error(update, context):

    logger.warning('Update "%s" caused error "%s"', update, context.error)


def end(update, context):

    text = 'Приходите ещё!'
    update.message.reply_text(text)
    return ConversationHandler.END


def main():

    logger = logging.getLogger(__name__)

    r = rdb.connect_to_db()
    partial_start = partial(start, r=r)
    partial_cart_handler = partial(cart_handler, r=r)
    partial_ask_for_user_email = partial(ask_for_user_email, r=r)
    partial_handle_phone = partial(handle_phone, r=r)
    partial_handle_email = partial(handle_email, r=r)

    token = os.environ.get['TG_TOKEN']
    updater = Updater(token, use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', partial_start)],
        states={
            STORE: [CallbackQueryHandler(make_product_page, pattern='^' +'(?s)^([^a-zA-Z]*[A-Za-z]){4}.*'+'$')],
            PRODUCT: [CallbackQueryHandler(partial_start, pattern='^' + 'FALLBACK' + '$'),
                     CallbackQueryHandler(confirm, pattern='^' + '(?s)^[0-9]{2}.*' + '$')],
            CONFIRMATION: [CallbackQueryHandler(cancel, pattern='^' + 'FALLBACK' + '$'),
                          CallbackQueryHandler(add_to_cart, pattern='^' +'(?s)^([^a-zA-Z]*[A-Za-z]){3}.*'+'$')],
            INCART: [CallbackQueryHandler(partial_start, pattern='^' + 'FALLBACK' + '$'),
                    CallbackQueryHandler(partial_cart_handler, pattern='^' +'(?s)^([^a-zA-Z]*[A-Za-z]){6}.*'+'$'),
                    CallbackQueryHandler(partial_ask_for_user_email, pattern='^' +'PAY'+'$')],
            EMAIL_INFO: [MessageHandler(Filters.text, partial_handle_email)],
            PHONE_INFO: [MessageHandler(Filters.text, partial_handle_phone)],
            CONFIRM_INFO: [CallbackQueryHandler(confirm_info, pattern='^' +'(?s)^([^a-zA-Z]*[A-Za-z]){5}.*'+'$')],
        },
        fallbacks=[CommandHandler('end', end)]
    )
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()

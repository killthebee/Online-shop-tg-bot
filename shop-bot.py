from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, Filters, MessageHandler)
import logging
import redis_db as r
import moltin
from functools import partial
import os


STORE, PRODUCT, CONFIRMATION, INCART, EMAIL_INFO, PHONE_INFO, CONFIRM_INFO = range(7)


def start(update, context):

    products = moltin.fetch_products()
    keyboard = []
    for name, prod_id in products:
        product_button = [InlineKeyboardButton(name, callback_data=prod_id)]
        keyboard.append(product_button)
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        user_id = update.message.from_user.id
        r.write_user_info_to_db(user_id, 'start')
        update.message.reply_text(
        'Пожалуйста, выберете товар',
        reply_markup=reply_markup
    )
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        r.write_user_info_to_db(user_id, 'cart')
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


def create_product_page(update, context):

    query = update.callback_query
    bot = context.bot
    prod_id = query.data
    keyboard = [
        [InlineKeyboardButton('5 pcs', callback_data='05%s'%(prod_id)),
        InlineKeyboardButton('10 pcs', callback_data='10%s'%(prod_id)),
        InlineKeyboardButton('15 pcs', callback_data='15%s'%(prod_id))],
        [InlineKeyboardButton('В корзину', callback_data='TOCART')],
        [InlineKeyboardButton('Назад', callback_data='FALLBACK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    product_data = moltin.fetch_product_data(prod_id)
    text = '%s\n\n%s\n%s\n\n%s'%(
        product_data['name'],
        product_data['price'],
        product_data['stock'],
        product_data['description'],
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
    pcs = query.data[0:2]
    prod_id = query.data[2:]
    keyboard = [
        [InlineKeyboardButton('Добавить в корзину', callback_data='ADD%s%s'%(pcs, prod_id)),
         InlineKeyboardButton('Отмена', callback_data='FALLBACK')]
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
    prod_id = query.data[5:]
    moltin.add_to_cart(pcs, prod_id, user_id)
    update.callback_query.answer('Готово!', alert=True)
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


def cart_handler(update, context):

    query = update.callback_query
    bot = context.bot
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton('Оплатить', callback_data='PAY')],
        [InlineKeyboardButton('В меню', callback_data='FALLBACK')]
    ]
    r.write_user_info_to_db(user_id, 'cart')

    if query.data.startswith('delete'):
        moltin.delete_item(user_id, query)

    items = moltin.fetch_products_in_cart(user_id)
    total_value = 0
    text = ''
    for item in items:

        name_raw = item['name']
        description_raw = item['description']
        price = item['unit_price']['amount']/100
        price_raw = '$%s per piece'%(price)
        quantity = item['quantity']
        total_value_of_item = round(quantity * price, 2)
        quantity_raw = '%spc/pcs in cart for $%s'%(quantity, total_value_of_item)

        additional_text = '%s\n%s\n%s\n%s\n\n\n'%(
            name_raw,
            description_raw,
            price_raw,
            quantity_raw,
        )
        text = text + additional_text
        total_value = total_value + total_value_of_item
        inline_keyboard_button_text = 'Удалить %s'%(name_raw)

        callback_data = 'delete%s'%(item['id'])
        delete_button = [InlineKeyboardButton(inline_keyboard_button_text, callback_data=callback_data)]
        keyboard.insert(-2, delete_button)

    total_value_text = 'Total: %s'%(total_value)
    text = text + total_value_text

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


def ask_for_user_email(update, context):

    query = update.callback_query
    user_id = query.from_user.id
    bot = context.bot
    bot.send_message(
        chat_id=query.message.chat_id,
        text='пожалуйста, пришлите ваш емеил'
    )
    return EMAIL_INFO


def handle_email(update, context):

    user_message = update.message.text
    info_update = update.message
    user = update.message.from_user
    user_id = user.id
    if '@' not in user_message or '.' not in user_message:

        text = 'Имеил не распознан, попробуйте отправить имеил ещё раз!'
        update.message.reply_text(text)
        return

    first_name = user.first_name
    last_name = user.last_name
    name = '%s %s'%(first_name, last_name)
    customer_created = moltin.create_customer(name , user_message)

    if customer_created:
        text = 'Пожалуйста, пришлите ваш телефон'
        update.message.reply_text(text)
        r.write_user_info_to_db(user_id, 'email', user_message)
        return PHONE_INFO
    else:
        text = 'Имеил не распознан, попробуйте отправить имеил ещё раз!'
        update.message.reply_text(text)


def handle_phone(update, context):

    user_message = update.message.text
    user_id = update.message.from_user.id
    user_email = r.fetch_email(user_id)
    if user_email is None:
        text = ('Произошли проблемы с распознованием вашего имела, введите'
        'имеил снова')
        update.message.reply_text(text)
        return EMAIL_INFO
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
            text = 'Ваш email: %s\nВаш телефон: %s'%(user_email, user_message)
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


def handle_error(update, context, logger):

    logger.warning('Update "%s" caused error "%s"', update, context.error)


def end(update, context):

    text = 'Приходите ещё!'
    update.message.reply_text(text)
    return ConversationHandler.END


def main():

    token = os.environ.get['TG_TOKEN']
    updater = Updater(token, use_context=True)

    dp = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    handle_error_partial = partial(handle_error, logger=logger)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STORE: [CallbackQueryHandler(create_product_page)],
            PRODUCT: [CallbackQueryHandler(start, pattern='FALLBACK'),
                     CallbackQueryHandler(cart_handler, pattern='TOCART'),
                     CallbackQueryHandler(confirm, pattern=r'^(?s)^[0-9]{2}.*$')],
            CONFIRMATION: [CallbackQueryHandler(cancel, pattern='FALLBACK'),
                          CallbackQueryHandler(add_to_cart, pattern=r'^(?s)^([^a-zA-Z]*[A-Za-z]){3}.*$')],
            INCART: [CallbackQueryHandler(start, pattern='FALLBACK'),
                    CallbackQueryHandler(cart_handler, pattern=r'^(?s)^([^a-zA-Z]*[A-Za-z]){6}.*$'),
                    CallbackQueryHandler(ask_for_user_email, pattern='PAY')],
            EMAIL_INFO: [MessageHandler(Filters.text, handle_email)],
            PHONE_INFO: [MessageHandler(Filters.text, handle_phone)],
            CONFIRM_INFO: [CallbackQueryHandler(confirm_info, pattern=r'^(?s)^([^a-zA-Z]*[A-Za-z]){5}.*$')],
        },
        fallbacks=[CommandHandler('end', end)]
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(handle_error_partial)


    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()

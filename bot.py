import os
import sys
from utils import *
from datetime import datetime

import telegram
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)


def start(update, context):
    update.message.reply_text("ברוכ/ה הבא/ה לריילזבוט!")
    update.message.reply_text("הכנס תחנת מוצא:")
    return CHOOSE_ORIGIN


def get_depart_station(update, context):
    user = update.message.from_user
    input_text = update.message.text
    logger.info("User {}, departure input: {}".format(user, input_text))
    # TODO - Validate input and fuzzy lookup
    context.user_data['depart_station'], score = get_fuzzy_station_name(update.message.text)
    update.message.reply_text("תחנת מוצא: {}".format(context.user_data['depart_station']))
    update.message.reply_text("הכנס/י תחנת יעד:")
    return CHOOSE_DEST


def get_dest_station(update, context):
    user = update.message.from_user
    logger.info("User {}, destination input: {}".format(user, update.message.text))
    # TODO - Validate input and fuzzy lookup
    context.user_data['dest_station'], score = get_fuzzy_station_name(update.message.text)
    update.message.reply_text("תחנת יעד: {}".format(context.user_data['dest_station']))

    if 'depart_station' in context.user_data and 'dest_station' in context.user_data:
        depart_station = context.user_data['depart_station']
        dest_station = context.user_data['dest_station']
        if depart_station == dest_station:
            update.message.reply_text("אנא הכנס/י תחנת מוצא ויעד שונות.")
            update.message.reply_text("הכנס תחנת מוצא:")
            return CHOOSE_ORIGIN
    else:
        update.message.reply_text("נתונים חסרים. אנא התחל/י מחדש")
        return ConversationHandler.END

    update.message.reply_text("עכשיו?", reply_markup=telegram.ReplyKeyboardMarkup([['לא', 'כן']]))

    return CHOOSE_TIME


def get_choose_time(update, context):
    user = update.message.from_user
    context.user_data['time_keyboard_input'] = update.message.text
    logger.info("User {}, keyboard 'now' input: {}".format(user, context.user_data['time_keyboard_input']))
    if context.user_data['time_keyboard_input'] == "כן":
        update.message.reply_text("מחפש רכבות קרובות...", reply_markup=telegram.ReplyKeyboardRemove())
        timestamp = datetime.now()
        get_route(update, context, timestamp)
        update.message.reply_text("איך עוד אפשר לעזור?",
                                  reply_markup=telegram.ReplyKeyboardMarkup([['סיימתי', 'חיפוש חדש', 'צור תזכורת']]))
        return PAST_ROUTE
    elif context.user_data['time_keyboard_input'] == "לא":
        update.message.reply_text("מתי?", 
                                  reply_markup=telegram.ReplyKeyboardMarkup([['בתאריך...', 'מחר', 'היום']]))
    else:
        update.message.reply_text("לא הצלחתי להבין.", reply_markup=telegram.ReplyKeyboardRemove())
        update.message.reply_text("לחפש רכבות לעכשיו?", reply_markup=telegram.ReplyKeyboardMarkup([['לא', 'כן']]))

        return CHOOSE_TIME
    return PARSE_DAY


def get_parsed_day(update, context):
    user = update.message.from_user
    context.user_data['day_keyboard_input'] = update.message.text
    logger.info("User {}, parsed day input: {}".format(user, context.user_data['day_keyboard_input']))
    if context.user_data['day_keyboard_input'] == "היום":
        context.user_data['date_input'] = datetime.now()
    elif context.user_data['day_keyboard_input'] == "מחר":
        context.user_data['date_input'] = datetime.now() + timedelta(hours=24)
    elif context.user_data['day_keyboard_input'] == "בתאריך...":
        update.message.reply_text("הכנס תאריך:", reply_markup=telegram.ReplyKeyboardRemove())
        return CUSTOM_DAY
    else:
        update.message.reply_text("לא הצלחתי להבין.", reply_markup=telegram.ReplyKeyboardRemove())
        update.message.reply_text("בחר חלון תאריכים לחיפוש רכבות:", 
                                  reply_markup=telegram.ReplyKeyboardMarkup([['בתאריך...', 'מחר', 'היום']]))
        return PARSE_DAY
    
    update.message.reply_text("באיזו שעה?", reply_markup=telegram.ReplyKeyboardRemove())

    return PARSE_HOUR


def get_custom_day(update, context):
    user = update.message.from_user
    manual_day_input = update.message.text
    logger.info("User {}, manual day input: {}".format(user, manual_day_input))
    found_time = parse(manual_day_input)
    if found_time is None or found_time.year < CUR_YEAR:
        update.message.reply_text("לא הצלחתי להבין.", reply_markup=telegram.ReplyKeyboardRemove())
        update.message.reply_text("בחר חלון תאריכים לחיפוש רכבות:", 
                                  reply_markup=telegram.ReplyKeyboardMarkup([['בתאריך...', 'מחר', 'היום']]))
        return PARSE_DAY
    context.user_data['date_input'] = found_time
    update.message.reply_text("אוקיי, ה-{}".format(context.user_data['date_input'].strftime("%d/%m/%Y")), 
                              reply_markup=telegram.ReplyKeyboardRemove())
    update.message.reply_text("באיזו שעה?", reply_markup=telegram.ReplyKeyboardRemove())

    return PARSE_HOUR


def get_parsed_hour(update, context):
    user = update.message.from_user
    logger.info("User {}, parsed time input: {}".format(user, update.message.text))
    context.user_data['time_input'] = update.message.text
    context.user_data['time_input'] = get_fuzzy_time(context.user_data['time_input'])
    if context.user_data['time_input'] is None:
        update.message.reply_text("לא הצלחתי להבין מתי. נסה/י שוב.")
        return PARSE_HOUR
    context.user_data['timestamp_input'] = datetime.combine(context.user_data['date_input'].date(), 
                                                            context.user_data['time_input'].time())
    update.message.reply_text("מחפש רכבות עבור: {}"
                              .format(context.user_data['timestamp_input'].strftime('%d/%m/%y %H:%M')))
    if (datetime.now() - context.user_data['timestamp_input']).total_seconds() > 30:
        update.message.reply_text("לא ניתן לקבל לוחות זמנים עבור רכבות עבר. הכנס/י תאריך ושעה אחרים.")
        update.message.reply_text("מתי?", reply_markup=telegram.ReplyKeyboardMarkup([['בתאריך...', 'מחר', 'היום']]))
        return PARSE_DAY
    get_route(update, context, context.user_data['timestamp_input'])
    update.message.reply_text("איך עוד אפשר לעזור?", 
                              reply_markup=telegram.ReplyKeyboardMarkup([['סיימתי', 'חיפוש חדש', 'צור תזכורת']]))
    return PAST_ROUTE


def past_route(update, context):
    user = update.message.from_user
    context.user_data['conv_end_message'] = update.message.text
    logger.info("User {}, past route input: {}".format(user, context.user_data['conv_end_message']))
    if context.user_data['conv_end_message'] == 'סיימתי':
        return happy_end(update, context)
    elif context.user_data['conv_end_message'] == 'חיפוש חדש':
        update.message.reply_text("הכנס תחנת מוצא:", reply_markup=telegram.ReplyKeyboardRemove())
        return CHOOSE_ORIGIN
    elif context.user_data['conv_end_message'] == 'צור תזכורת':
        update.message.reply_text("באיזו שעה להתריע?", reply_markup=telegram.ReplyKeyboardRemove())
        return TIME_SCHEDULE
    else:
        update.message.reply_text("לא הצלחתי להבין.")
        update.message.reply_text("איך עוד אפשר לעזור?",
                                  reply_markup=telegram.ReplyKeyboardMarkup([['סיימתי', 'חיפוש חדש', 'צור תזכורת']]))
        return PAST_ROUTE


def get_time_schedule(update, context):
    user = update.message.from_user
    sched_time_message = update.message.text
    logger.info("User {}, sched time input: {}".format(user, sched_time_message))
    found_time = get_fuzzy_time(sched_time_message)
    if found_time is None:
        update.message.reply_text("לא הצלחתי להבין מתי. נסה/י להזין שעה בפורמט כמו '08:30':")
        return TIME_SCHEDULE
    context.user_data['time_schedule'] = found_time.time()
    update.message.reply_text("אוקיי, ב{}".format(context.user_data['time_schedule'].strftime("%H:%M")))
    update.message.reply_text("באיזה ימים? הכנס/י רשימה מהצורה 'א,ב,ג...'.")
    return DAY_SCHEDULE


def get_day_schedule(update, context):
    user = update.message.from_user
    sched_day_message = update.message.text
    try:
        sanitized_days = [DAYS_DICT[x] for x in list(sched_day_message.replace(" ", "").replace(",", ""))]
        if len(sanitized_days) == 0:
            raise ValueError("לא נמצאו ימים")
    except:
        update.message.reply_text("לא הצלחתי להבין את טווח הימים. נסה/י להזין שוב ללא גרשיים או פיסוק מיותר.")
        return DAY_SCHEDULE

    # Pack needed job data in context.user_data
    update.message.reply_text("אתריע בימים: {}".format([REV_DAYS_DICT[x] for x in sanitized_days]))
    context.user_data['chat_id'] = update.effective_chat.id
    context.user_data['days'] = sanitized_days
    found_time = context.user_data['time_schedule']
    logger.info("User {}, adding schedule at time {}, days: {}".format(user, found_time, sanitized_days))
    context.job_queue.run_daily(notify, found_time, days=tuple(sanitized_days), context=context)
    update.message.reply_text("התראה נוספה בהצלחה.")
    return happy_end(update, context)


def timeout(update, context):
    user = context.effective_user
    chat_id = context.message.chat_id
    logger.info("User {} timed out".format(user))
    update.send_message(chat_id=chat_id, text="עקב חוסר פעילות נותקת מהמערכת.", reply_markup=telegram.ReplyKeyboardRemove())
    update.send_message(chat_id=chat_id, text="להתחלה לחצ/י על /start", reply_markup=telegram.ReplyKeyboardRemove())
    return ConversationHandler.END


def cancel(update, context):
    user = update.message.from_user
    logger.info("User {} canceled the conversation.".format(user))
    return happy_end(update, context)


def happy_end(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="ריילזבוט שמח לעזור!", reply_markup=telegram.ReplyKeyboardRemove())
    context.bot.send_message(chat_id=chat_id, text="להתחלה לחצ/י על /start", reply_markup=telegram.ReplyKeyboardRemove())
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update {} caused error {}'.format(update, context.error))


def main():

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSE_ORIGIN: [MessageHandler(Filters.text, get_depart_station)],
            CHOOSE_DEST: [MessageHandler(Filters.text, get_dest_station)],
            CHOOSE_TIME: [MessageHandler(Filters.text, get_choose_time)],
            PARSE_DAY: [MessageHandler(Filters.text, get_parsed_day)],
            CUSTOM_DAY: [MessageHandler(Filters.text, get_custom_day)],
            PARSE_HOUR: [MessageHandler(Filters.text, get_parsed_hour)],
            PAST_ROUTE: [MessageHandler(Filters.text, past_route)],
            TIME_SCHEDULE: [MessageHandler(Filters.text, get_time_schedule)],
            DAY_SCHEDULE: [MessageHandler(Filters.text, get_day_schedule, pass_job_queue=True)],
            ConversationHandler.TIMEOUT: [MessageHandler(None, timeout)]
        },

        fallbacks=[CommandHandler('cancel', cancel)],

        conversation_timeout=CONVERSATION_TIMEOUT
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':

    mode = os.getenv("MODE")
    TOKEN = os.getenv("TOKEN")
    logger.info("Starting bot")

    updater = Updater(TOKEN, use_context=True)

    if mode == "dev":
        logger.info("Dev mode")
        updater.start_polling()

        # app_url = "https://localhost/"
        # wakeup_wrapper(app_url)

    elif mode == "prod":
        logger.info("Production mode")

        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        # Code from https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks#heroku
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))

        # app_url = "https://{}.herokuapp.com/".format(HEROKU_APP_NAME)
        # wakeup_wrapper("127.0.0.1")

    else:
        logger.error("No MODE specified!")
        sys.exit(1)

    main()

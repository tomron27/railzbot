"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os
import sys
from utils import get_fuzzy_station_name
from route import get_routes
from datetime import datetime, timedelta
import dateparser

import telegram
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

DAYS_DICT = {'א': 6, 'ב': 0, 'ג': 1, 'ד': 2, 'ה': 3, 'ו': 4, 'ש': 5}
REV_DAYS_DICT = {v: k for k, v in DAYS_DICT.items()}

CHOOSE_ORIGIN, CHOOSE_DEST, CHOOSE_TIME, PARSE_TIME, PAST_ROUTE, TIME_SCHEDULE, DAY_SCHEDULE = range(7)


def start(update, context):
    update.message.reply_text("ברוכ/ה הבא/ה לריילזבוט!")
    update.message.reply_text("הכנס תחנת מוצא:")
    return CHOOSE_ORIGIN


def get_depart_station(update, context):
    user = update.message.from_user
    input_text = update.message.text
    logger.info("User {}, departure input: {}".format(user, input_text))
    res = get_fuzzy_station_name(update.message.text)
    # TODO - Validate input and fuzzy lookup
    found_station, score = res
    context.user_data['depart_station'] = found_station
    update.message.reply_text("תחנת מוצא: {}".format(found_station))
    update.message.reply_text("הכנס/י תחנת יעד:")
    return CHOOSE_DEST


def get_dest_station(update, context):
    user = update.message.from_user
    logger.info("User {}, destination input: {}".format(user, update.message.text))
    res = get_fuzzy_station_name(update.message.text)
    # TODO - Validate input and fuzzy lookup
    found_station, score = res
    context.user_data['dest_station'] = found_station
    update.message.reply_text("תחנת יעד: {}".format(found_station))

    if 'depart_station' in context.user_data and 'dest_station' in context.user_data:
        depart_station = context.user_data['depart_station']
        dest_station = context.user_data['dest_station']
        if depart_station == dest_station:
            update.message.reply_text("אנא הכנס/י תחנת מוצא ויעד שונות.")
            return CHOOSE_ORIGIN
    else:
        update.message.reply_text("נתונים חסרים. אנא התחל/י מחדש")
        return ConversationHandler.END

    time_reply_keyboard = [['אחר כך', 'עכשיו']]
    update.message.reply_text("מתי?", reply_markup=telegram.ReplyKeyboardMarkup(time_reply_keyboard,
                                                                                resize_keyboard=True,
                                                                                one_time_keyboard=True))

    return CHOOSE_TIME


def get_route(update, context, timestamp):
    depart_station = context.user_data['depart_station']
    dest_station = context.user_data['dest_station']
    res = get_routes(depart_station, dest_station, timestamp)
    update.message.reply_text(res, parse_mode=telegram.ParseMode.MARKDOWN)


def past_route_keyboard(update, context):
    conv_end_reply_keyboard = [['סיימתי', 'חיפוש חדש', 'צור תזכורת']]
    update.message.reply_text("איך עוד אפשר לעזור?", reply_markup=telegram.ReplyKeyboardMarkup(conv_end_reply_keyboard,
                                                                                               resize_keyboard=True,
                                                                                               one_time_keyboard=True))


def notify(context):
    recv_context = context.job.context
    chat_id = recv_context.user_data['chat_id']
    context.bot.send_message(chat_id=chat_id, text="תזכורת מסלולים:")
    depart_station = recv_context.user_data['depart_station']
    dest_station = recv_context.user_data['dest_station']
    res = get_routes(depart_station, dest_station, datetime.now())
    context.bot.send_message(chat_id=chat_id, text=res, parse_mode=telegram.ParseMode.MARKDOWN)


def get_depart_time(update, context):
    user = update.message.from_user
    logger.info("User {}, keyboard time input: {}".format(user, update.message.text))
    time_keyboard_input = update.message.text
    if time_keyboard_input == "עכשיו":
        update.message.reply_text("מחשב תוצאות עבור: {}".format(time_keyboard_input),
                                  reply_markup=telegram.ReplyKeyboardRemove())
        timestamp = datetime.now()
        get_route(update, context, timestamp)
        past_route_keyboard(update, context)
        return PAST_ROUTE
    else:
        update.message.reply_text("באיזה זמן?", reply_markup=telegram.ReplyKeyboardRemove())
        return PARSE_TIME


def get_parsed_time(update, context):
    user = update.message.from_user
    logger.info("User {}, parsed time input: {}".format(user, update.message.text))
    time_input = update.message.text
    found_time = dateparser.parse(time_input)
    if found_time is None:
        update.message.reply_text("לא הצלחתי להבין מתי. נסה/י להזין תאריך ושעה או טקסט כגון 'מחר 08:30'.")
        return PARSE_TIME
    now = datetime.now()
    if (now - found_time).total_seconds() > 30:
        update.message.reply_text("מחשב תוצאות עבור: {}".format(found_time.strftime('%d/%m/%y %H:%M')))
        update.message.reply_text("לא ניתן לקבל לוחות זמנים עבור רכבות עבר. הכנס/י זמן אחר.")
        return PARSE_TIME
    else:
        update.message.reply_text("מחשב תוצאות עבור: {}".format(found_time.strftime('%d/%m/%y %H:%M')))
        get_route(update, context, found_time)
        past_route_keyboard(update, context)
        return PAST_ROUTE


def past_route(update, context):
    user = update.message.from_user
    conv_end_message = update.message.text
    logger.info("User {}, past route input: {}".format(user, conv_end_message))
    if conv_end_message == 'סיימתי':
        update.message.reply_text('ריילזבוט שמח לעזור!', reply_markup=telegram.ReplyKeyboardRemove())
        return ConversationHandler.END
    if conv_end_message == 'חיפוש חדש':
        update.message.reply_text("הכנס תחנת מוצא:", reply_markup=telegram.ReplyKeyboardRemove())
        return CHOOSE_ORIGIN
    if conv_end_message == 'צור תזכורת':
        update.message.reply_text("באיזו שעה להתריע?", reply_markup=telegram.ReplyKeyboardRemove())
        return TIME_SCHEDULE


def get_time_schedule(update, context):
    user = update.message.from_user
    sched_time_message = update.message.text
    logger.info("User {}, sched time input: {}".format(user, sched_time_message))
    found_time = dateparser.parse(sched_time_message)
    if found_time is None:
        update.message.reply_text("לא הצלחתי להבין מתי. נסה/י להזין שעה בפורמט כמו '08:30'.")
        return TIME_SCHEDULE
    found_time = found_time.time()
    context.user_data['time_schedule'] = found_time
    update.message.reply_text("אתריע בשעה {}.".format(found_time.strftime("%H:%M")))
    update.message.reply_text("באיזה ימים? הכנס/י רשימה מהצורה 'א,ב,ג...'.")
    return DAY_SCHEDULE


def get_day_schedule(update, context):
    user = update.message.from_user
    sched_day_message = update.message.text
    if "," in sched_day_message:
        try:
            sanitized_days = [DAYS_DICT[x] for x in list(sched_day_message.replace(" ", "").replace(",", ""))]
            if len(sanitized_days) == 0:
                update.message.reply_text("לא הצלחתי להבין את טווח הימים. נסה/י להזין שוב ללא גרשיים או פיסוק מיותר.")
                return DAY_SCHEDULE
        except:
            update.message.reply_text("לא הצלחתי להבין את טווח הימים. נסה/י להזין שוב ללא גרשיים או פיסוק מיותר.")
            return DAY_SCHEDULE
    else:
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
    return ConversationHandler.END


def cancel(update, context):
    user = update.message.from_user
    logger.info("User {} canceled the conversation.".format(user))
    update.message.reply_text('ריילזבוט שמח לעזור!')

    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update {} caused error {}'.format(update, context.error))


def main():

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSE_ORIGIN: [MessageHandler(Filters.text, get_depart_station)],
            CHOOSE_DEST: [MessageHandler(Filters.text, get_dest_station)],
            CHOOSE_TIME: [MessageHandler(Filters.text, get_depart_time)],
            PARSE_TIME: [MessageHandler(Filters.text, get_parsed_time)],
            PAST_ROUTE: [MessageHandler(Filters.text, past_route)],
            TIME_SCHEDULE: [MessageHandler(Filters.text, get_time_schedule)],
            DAY_SCHEDULE: [MessageHandler(Filters.text, get_day_schedule, pass_job_queue=True)],
        },

        fallbacks=[CommandHandler('cancel', cancel)]
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
    elif mode == "prod":
        logger.info("Production mode")
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        # Code from https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks#heroku
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
    else:
        logger.error("No MODE specified!")
        sys.exit(1)

    main()

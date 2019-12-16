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

from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

CHOOSING_DEPART, CHOOSING_ARRIVE, CALC_RESULT = range(3)


def start(update, context):
    update.message.reply_text("ברוכ/ה הבא/ה לריילזבוט!")
    update.message.reply_text("הכנס/י תחנת מוצא:")
    return CHOOSING_DEPART


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

    return CHOOSING_ARRIVE


def get_dest_station(update, context):
    user = update.message.from_user
    logger.info("User {}, destination input: {}".format(user, update.message.text))
    res = get_fuzzy_station_name(update.message.text)
    # TODO - Validate input and fuzzy lookup
    found_station, score = res
    context.user_data['dest_station'] = found_station
    update.message.reply_text("תחנת יעד: {}".format(found_station))
    update.message.reply_text("מחשב תוצאות...")
    if 'depart_station' in context.user_data and 'dest_station' in context.user_data:
        depart_station = context.user_data['depart_station']
        dest_station = context.user_data['dest_station']
        if depart_station == dest_station:
            update.message.reply_text("לא מצחיק!")
            return CHOOSING_DEPART
        res = get_routes(depart_station, dest_station)
        update.message.reply_text(res)
    else:
        update.message.reply_text("נתונים חסרים. אנא התחל/י מחדש")
        return CHOOSING_DEPART

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
            0: [MessageHandler(Filters.text, get_depart_station)],
            1: [MessageHandler(Filters.text, get_dest_station)],
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

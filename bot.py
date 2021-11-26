from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import dotenv_values
from functools import partial
from typing import Dict, List, Optional
import logging

from custom_types import FunctionalFeature


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


FUNCTIONAL_FEATURES = FunctionalFeature()

user_info = {}

questions_data = {
    'start': {
        'type': 'beginning',
        'encoded_replies': {},
        'next_question': 'Привет, мы рады, что вы решили воспользоваться нашим чекером для проверки своего здоровья. '
        'Напоминаю, что наш чекер позволяет детектировать хроническую сердечную недостаточность (сокращенно ХСН) '
        'Для постановки правильного диагноза и лечения Вам необходимо ответить на несколько вопросов. '
        'Пожалуйста, отвечайте максимально честно! '
        'Первый вопрос: Наблюдается ли у вас отдышка?',
        'next_question_reply_keyboard': [['Нет', 'При нагрузке', 'В покое']]
    },
    'breathlessness': {
        'type': 'usual',
        'encoded_replies': {
            'Нет': 0,
            'При нагрузке': 1,
            'В покое': 2
            },
        'next_question': 'Понятно. Скажите пожалуйста, увеличился ли ваш вес за последнюю неделю?',
        'next_question_reply_keyboard': [['Нет', 'Да']]
    },
    'weight': {
        'type': 'usual',
        'encoded_replies': {
            'Нет': 0,
            'Да': 1
            },
        'next_question': 'Скажите пожалуйста, есть ли у вас жалобы на перебои в работе сердца',
        'next_question_reply_keyboard': [['Нет', 'Есть']]
    },
    'changed_heart_failure_complaints': {
        'type': 'usual',
        'encoded_replies': {
            'Нет': 0,
            'Есть': 1
            },
        'next_question': 'Скажите пожалуйста, работает ли у вас сердце в режиме галопа?',
        'next_question_reply_keyboard': [['Нет', 'Да']]
    },
    'heart_rhythm_type': {
        'type': 'usual',
        'encoded_replies': {
            'Нет': 0,
            'Да': 1
        },
        'next_question': 'Скажите пожалуйста, в каком положении вы обычно находитесь в постели?',
        'next_question_reply_keyboard': [['Горизонтально', 'С приподнятым головным концом (две и более подушек)',
                       'Просыпаюсь от удушья каждый раз', 'Сидя']]
    },
    'position_in_bed': {
        'type': 'usual',
        'encoded_replies': {
            'Горизонтально': 0,
            'С приподнятым головным концом (две и более подушек)': 1,
            'Просыпаюсь от удушья каждый раз': 2,
            'Сидя': 3
        },
        'next_question': 'Скажите пожалуйста, у вас шейные вены набухшие?',
        'next_question_reply_keyboard': [['Нет', 'Лежа', 'Стоя']]
    },
    'swollen_cervical_veins': {
        'type': 'usual',
        'encoded_replies': {
            'Нет': 0,
            'Лежа': 1,
            'Стоя': 2
        },
        'next_question': 'Скажите пожалуйста, у вас есть хрипы в легких?',
        'next_question_reply_keyboard': [['Нет', 'Нижние отделы', 'До лопаток', 'Над всей поверхностью легких']]
    },
    'wheezing_in_lungs': {
        'type': 'usual',
        'encoded_replies': {
                    'Нет': 0,
                    'Нижние отделы': 1,
                    'До лопаток': 2,
                    'Над всей поверхностью легких': 3
                },
        'next_question': 'Скажите пожалуйста, изменились ли у вас размеры печени?',
        'next_question_reply_keyboard': [['Не увеличена', 'До 5 см', 'Более 5 см']]
    },
    'liver_state': {
        'type': 'usual',
        'encoded_replies': {
                    'Не увеличена': 0,
                    'До 5 см': 1,
                    'Более 5 см': 2
                },
        'next_question': 'Скажите пожалуйста, есть ли у вас отек и если есть, то какой?',
        'next_question_reply_keyboard': [['Нет', 'Пастозность', 'Отеки', 'Анасарка']]
    },
    'edema': {
        'type': 'usual',
        'encoded_replies': {
                    'Нет': 0,
                    'Пастозность': 1,
                    'Отеки': 2,
                    'Анасарка': 3
                },
        'next_question': 'Скажите пожалуйста, какой у вас уровень систолического давления?',
        'next_question_reply_keyboard': [['Более 120 мм рт. ст.', '100-120 мм рт. ст.', 'Менее 120 мм рт. ст.']]
    },
    'systolic_pressure': {
        'type': 'final',
        'encoded_replies': {
            'Более 120 мм рт. ст.': 0,
            '100-120 мм рт. ст.': 1,
            'Менее 120 мм рт. ст.': 2
        },
        'next_question': '',
        'next_question_reply_keyboard': []
    },
}


def info(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Привет, меня зовут Original Symptom Checker bot. Мои создатели: "
                                  "Мраморов Никита и Роман Ефремов из группы J41325c")


# def start(update: Update, context: CallbackContext):
#     reply_keyboard = [['Нет', 'При нагрузке', 'В покое']]
#
#     update.message.reply_text(
#         'Привет, мы рады, что вы решили воспользоваться нашим чекером для проверки своего здоровья. '
#         'Напоминаю, что наш чекер позволяет детектировать хроническую сердечную недостаточность (сокращенно ХСН) '
#         'Для постановки правильного диагноза и лечения Вам необходимо ответить на несколько вопросов. '
#         'Пожалуйста, отвечайте максимально честно! '
#         'Первый вопрос: Наблюдается ли у вас отдышка?',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholer='Отдышка?'
#         )
#     )
#
#     return FUNCTIONAL_FEATURES.breathlessness
#
#
# def breathlessness(update: Update, context: CallbackContext):
#
#     reply_keyboard = [['Нет', 'Да']]
#     user_info['breathlessness'] = encoded_replies['breathlessness'][update.message.text]
#     logger.info('Patient breathlessness: %i', user_info['breathlessness'])
#
#     update.message.reply_text(
#         'Понятно. Скажите пожалуйста, увеличился ли ваш вес за последнюю неделю?',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholder='Вес увеличился?'
#         )
#     )
#
#     return FUNCTIONAL_FEATURES.weight
#
#
# def weight(update: Update, context: CallbackContext):
#
#     reply_keyboard = [['Нет', 'Есть']]
#     user_info['weight'] = encoded_replies['weight'][update.message.text]
#     logger.info('Patient weight: %i', user_info['weight'])
#
#     update.message.reply_text(
#         'Скажите пожалуйста, есть ли у вас жалобы на перебои в работе сердца',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholder='Жалобы на перебои в работе сердца?'
#         )
#     )
#
#     return FUNCTIONAL_FEATURES.changed_heart_failure_complaints
#
#
# def changed_heart_failure_complaints(update: Update, context: CallbackContext):
#
#     reply_keyboard = [['Нет', 'Есть']]
#     user_info['changed_heart_failure_complaints'] = encoded_replies['changed_heart_failure_complaints'][
#         update.message.text]
#     logger.info('Patient changed_heart_failure_complaints: %i', user_info['changed_heart_failure_complaints'])
#
#     update.message.reply_text(
#         'Скажите пожалуйста, работает ли у вас сердце в режиме галопа?',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholder='Сердце работает в галопе?'
#         )
#     )
#
#     return FUNCTIONAL_FEATURES.heart_rhythm_type
#
#
# def heart_rhythm_type(update: Update, context: CallbackContext):
#
#     reply_keyboard = [['Горизонтально', 'С приподнятым головным концом (две и более подушек)',
#                        'Просыпаюсь от удушья каждый раз', 'Сидя']]
#     user_info['heart_rhythm_type'] = encoded_replies['heart_rhythm_type'][update.message.text]
#     logger.info('Patient heart_rhythm_type: %i', user_info['heart_rhythm_type'])
#
#     update.message.reply_text(
#         'Скажите пожалуйста, в каком положении вы обычно находитесь в постели?',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholder='Ваше положение в постели?'
#         )
#     )
#
#     return FUNCTIONAL_FEATURES.position_in_bed
#
#
# def position_in_bed(update: Update, context: CallbackContext):
#
#     reply_keyboard = [['Нет', 'Есть']]
#     user_info['position_in_bed'] = encoded_replies['position_in_bed'][update.message.text]
#     logger.info('Patient position_in_bed: %i', user_info['position_in_bed'])
#
#     update.message.reply_text(
#         'Скажите пожалуйста, в каком положении вы обычно находитесь в постели?',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True, input_field_placeholder='Ваше положение в постели?'
#         )
#     )
#
#     return FUNCTIONAL_FEATURES.position_in_bed


def dialog_function(update: Update, context: CallbackContext,
             user_feature: str,
             question_type: str,
             encoded_replies: Dict,
             next_question: str,
             next_question_reply_keyboard: List[List[Optional]]) -> int:

    if not question_type == 'beginning':
        user_info[user_feature] = encoded_replies[user_feature][update.message.text]
        logger.info('Patient %s: %i', user_feature, user_info[user_feature])

    if not question_type == 'final':
        update.message.reply_text(
            next_question,
            reply_markup=ReplyKeyboardMarkup(
                next_question_reply_keyboard, one_time_keyboard=True
            )
        )

        return getattr(FUNCTIONAL_FEATURES, user_feature)
    else:
        points = sum(user_info.values())
        if not points:
            functional_class = 'отсутствие клинических признаков СН.'
        elif points <= 3:
            functional_class = 'I ФК'
        elif 4 <= points <= 6:
            functional_class = 'II ФК'
        elif 7 <= points <= 9:
            functional_class = 'III ФК'
        else:
            functional_class = 'IV ФК'
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Получены данные пациента: {user_info}.")
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Функциональный класс: {functional_class}.")


class QuestionFactory:
    def __init__(self):




def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    config = dotenv_values(".env")

    updater = Updater(token=config['TOKEN'])

    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', breathlessness)],
        states={
            FUNCTIONAL_FEATURES.breathlessness: [MessageHandler(Filters.regex('^(012)$'), breathlessness)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    #updater.idle()


if __name__ == '__main__':
    main()

import logging
import os
from typing import Dict, List, AnyStr

from dotenv import dotenv_values
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)

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
    'weight_changed': {
        'type': 'usual',
        'encoded_replies': {
            'Нет': 0,
            'Да': 1
        },
        'next_question': 'Скажите пожалуйста, есть ли у вас жалобы на перебои в работе сердца',
        'next_question_reply_keyboard': [['Нет', 'Есть']]
    },
    'heart_failure_complaints': {
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
        'next_question_reply_keyboard': [[]]
    },
}


def info(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Привет, меня зовут Original Symptom Checker bot. Мои создатели: "
                                  "Мраморов Никита и Роман Ефремов из группы J41325c")


def dialog_function(update: Update, context: CallbackContext,
                    user_feature: str,
                    question_type: str,
                    encoded_replies: Dict,
                    next_question: str,
                    next_question_reply_keyboard: List[List[AnyStr]]) -> int:
    if question_type != 'beginning':
        user_info[user_feature] = encoded_replies[update.message.text]
        logger.info('Patient %s: %i', user_feature, user_info[user_feature])

    if question_type != 'final':
        update.message.reply_text(
            next_question,
            reply_markup=ReplyKeyboardMarkup(
                next_question_reply_keyboard
            )
        )
        return getattr(FUNCTIONAL_FEATURES, user_feature) + 1
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
                                 text=f"Получены данные пациента: {user_info}.\n"
                                      f"Сумма баллов ФК: {points}")
        update.message.reply_text(
            f'Функциональный класс {functional_class}',
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


class Question:
    def __init__(self, question_name: str):
        self.question_name = question_name
        self.type = questions_data[question_name]['type']
        self.encoded_replies = questions_data[question_name]['encoded_replies']
        self.next_question = questions_data[question_name]['next_question']
        self.next_question_reply_keyboard = questions_data[question_name]['next_question_reply_keyboard']

        listkeys = list(questions_data.keys())
        previous_question = None
        for index, key in enumerate(listkeys):
            if key == question_name:
                previous_question = listkeys[index - 1]
                break

        self.regex = '|'.join(questions_data[previous_question]['next_question_reply_keyboard'][0]) \
            if question_name != 'start' else None

    def ask(self, update: Update, context: CallbackContext) -> int:
        return dialog_function(update=update,
                               context=context,
                               user_feature=self.question_name,
                               question_type=self.type,
                               encoded_replies=self.encoded_replies,
                               next_question=self.next_question,
                               next_question_reply_keyboard=self.next_question_reply_keyboard)


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    config = dotenv_values(".env")

    updater = Updater(token=config['TOKEN'])

    dispatcher = updater.dispatcher

    questions = {question_name: Question(question_name) for question_name in questions_data}

    entry_points = [CommandHandler(questions['start'].question_name, questions['start'].ask)]

    states = {
        getattr(FUNCTIONAL_FEATURES, question_name):
            [MessageHandler(Filters.regex(
                questions[question_name].regex),
                questions[question_name].ask
            )]
        for question_name in questions
    }
    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(config['PORT']),
                          url_path=config['TOKEN'])
    updater.bot.setWebhook('https://hidden-island-83862.herokuapp.com/' + config['TOKEN'])


if __name__ == '__main__':
    main()

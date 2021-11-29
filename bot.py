import logging
from typing import Dict, List, AnyStr
from json import load
from os import listdir
from dotenv import dotenv_values
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
import argparse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

user_info = {}
receipts = []


def get_functional_conclusion(update: Update,
                              context: CallbackContext,
                              next_: str):
    points = sum(user_info.values())
    if not points:
        functional_class = 'отсутствуют клинические признаки ХСН.'
    elif points <= 3:
        user_info['FK'] = 1
        functional_class = 'I ФК'
    elif 4 <= points <= 6:
        user_info['FK'] = 2
        functional_class = 'II ФК'
    elif 7 <= points <= 9:
        user_info['FK'] = 3
        functional_class = 'III ФК'
    else:
        user_info['FK'] = 4
        functional_class = 'IV ФК'
    added = 'Для продолжения отправьте любое сообщение.' if 'FK' in user_info else ''
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Получены данные пациента: {user_info}.\n"
                                  f"Сумма баллов ФК: {points}\n"
                                  f'У вас {functional_class}\n' + added,

                             reply_markup=ReplyKeyboardRemove())

    return next_ if next_ and functional_class != 'Отсутствие клинических признаков СН.' else ConversationHandler.END


def get_final_conclusion(update: Update, context: CallbackContext, next_: str, conditions: Dict):
    texts = []

    for condition in conditions:
        valid_num_of_conditons = len(condition)
        i = 0
        for feature in conditions[condition]:
            if isinstance(conditions[condition][feature], dict):
                if str(user_info[feature]) in conditions[condition][feature] and i == valid_num_of_conditons - 1:
                    texts.extend(conditions[condition][feature][str(user_info[feature])])
            elif isinstance(conditions[condition][feature], list):
                i += 1

    receipts.append('\n'.join(texts))
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f'Ваше лечение:\n\n{receipts[0]}',
                             reply_markup=ReplyKeyboardRemove())
    return next_ if next_ else ConversationHandler.END


def dialog_function(update: Update, 
                    context: CallbackContext,
                    user_feature: str,
                    next_: str,
                    question_type: str,
                    encoded_replies: Dict,
                    text: str,
                    next_question_reply_keyboard: List[List[AnyStr]],
                    conditions: Dict):
    if encoded_replies:
        user_info[user_feature] = encoded_replies[update.message.text]
        logger.info('Patient %s: %i', user_feature, user_info[user_feature])

    if question_type == 'reply':
        update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(
                next_question_reply_keyboard
            )
        )
        return next_
    elif question_type == 'functional_conclusion':
        return get_functional_conclusion(update, context, next_)
    elif question_type == 'final_conclusion':
        return get_final_conclusion(update, context, next_, conditions)
    else:
        if text:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=text)
            update.message.reply_text(
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'До свидания!', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


class Question:
    def __init__(self, question_name: str, questions_data: Dict, conditions: Dict):
        self.question_name = question_name
        self.type = questions_data[question_name]['type']
        self.encoded_replies = questions_data[question_name]['encoded_replies']
        self.text = questions_data[question_name]['text']
        self.next_question_reply_keyboard = questions_data[question_name]['next_question_reply_keyboard']
        self.next_ = questions_data[question_name]['next_']
        self.conditions = conditions

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
                               text=self.text,
                               next_question_reply_keyboard=self.next_question_reply_keyboard,
                               next_=self.next_,
                               conditions=self.conditions)


def preprocess_df(df: pd.DataFrame):
    df.rename(columns={'weigth_changed': 'weight_changed'}, inplace=True)
    values = {}
    for column in df.columns:
        uniques = df[column].unique()
        if len(uniques) > 5:
            values[column] = df[column].mean()
        else:
            values[column] = 0

    df.fillna(value=values, inplace=True)
    df = df[values.keys()].apply(pd.to_numeric)

    df.loc[df.systolic_pressure > 120, 'systolic_pressure'] = 0
    df.loc[((df.systolic_pressure >= 85) & (df.systolic_pressure <= 120)), 'systolic_pressure'] = 1
    df.loc[((df.systolic_pressure < 85) & (df.systolic_pressure != 0) & (
                df.systolic_pressure != 1)), 'systolic_pressure'] = 2

    df.loc[df.heart_rate >= 70, 'heart_rate'] = 0
    df.loc[((df.heart_rate < 70) & (df.heart_rate != 0)), 'heart_rate'] = 1

    df.loc[df.bmi >= 25, 'bmi'] = 0
    df.loc[((df.bmi < 25) & (df.bmi != 0)), 'bmi'] = 1

    df.loc[df.age >= 70, 'age'] = 1
    df.loc[((df.age < 70) & (df.age != 1)), 'age'] = 0

    df.loc[df['6_minute_walking_test_result'] >= 200, '6_minute_walking_test_result'] = 1
    df.loc[((df['6_minute_walking_test_result'] < 200) & (
                df['6_minute_walking_test_result'] != 1)), '6_minute_walking_test_result'] = 0

    df.loc[df.blood_hemoglobin_level >= 350, 'blood_hemoglobin_level'] = 1
    df.loc[((df.blood_hemoglobin_level < 350) & (df.blood_hemoglobin_level != 1)), 'blood_hemoglobin_level'] = 0

    return df


def get_receipts(df: pd.DataFrame, conditions: Dict) -> List:
    df_receipts = []

    for record in df.to_dict('records'):
        points = sum([record['breathlessness'],
                            record['weight_changed'],
                            record['heart_failure_complaints'],
                            record['heart_rhythm_type'],
                            record['position_in_bed'],
                            record['swollen_cervical_veins'],
                            record['wheezing_in_lungs'],
                            record['liver_state'],
                            record['edema'],
                            record['systolic_pressure']])

        if not points:
            df_receipts.append(['Отсутствие признаков ХСН'])
            continue
        elif points <= 3:
            record['FK'] = 1
        elif 4 <= points <= 6:
            record['FK'] = 2
        elif 7 <= points <= 9:
            record['FK'] = 3
        else:
            record['FK'] = 4

        df_texts = []
        for condition in conditions:
            valid_num_of_conditons = len(condition)
            i = 0
            for feature in conditions[condition]:
                if isinstance(conditions[condition][feature], dict):
                    if str(record[feature]) in conditions[condition][feature] and i == valid_num_of_conditons - 1:
                        df_texts.extend(conditions[condition][feature][str(record[feature])])
                elif isinstance(conditions[condition][feature], list):
                    i += 1
        df_receipts.append(df_texts)

    return df_receipts


def main() -> None:
    """
    Для запуска из консоли введи команду 'python3 bot.py <path_to_dataset>'
    Для запуска бота введи команду 'python3 bot.py'
    """

    config = dotenv_values(".env")

    updater = Updater(token=config['TOKEN'])

    dispatcher = updater.dispatcher

    question_files = listdir(config['QUESTIONS_PATH'])

    questions_data = {}
    for question_file in question_files:
        with open(config['QUESTIONS_PATH'] + question_file, 'r') as f:
            questions_data.update(load(f))

    conditions = {}
    condition_files = listdir(config['CONDITIONS_PATH'])
    for condition_file in condition_files:
        with open(config['CONDITIONS_PATH'] + condition_file, 'r') as f:
            conditions.update(load(f))

    parser = argparse.ArgumentParser(description='Process dataset.')
    parser.add_argument('--path', type=str, help='path to dataset', required=False)

    args = parser.parse_args()

    if args.path:
        df = pd.read_csv(args.path)
        df = preprocess_df(df)
        df['receipts'] = get_receipts(df, conditions)
        print(df.receipts.head())
        return
    else:
        questions = {question_name: Question(question_name, questions_data, conditions) for question_name in questions_data}

        entry_points = [CommandHandler(questions['start'].question_name, questions['start'].ask)]

        states = {
            question_name:
                [MessageHandler(Filters.regex(
                    questions[question_name].regex),
                    questions[question_name].ask
                )]
            for question_name in questions
        }

        conv_handler = ConversationHandler(
            entry_points=entry_points,
            states=states,
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        dispatcher.add_handler(conv_handler)

        updater.start_polling()

    # updater.start_webhook(listen="0.0.0.0",
    #                       port=int(config['PORT']),
    #                       webhook_url='https://hidden-island-83862.herokuapp.com/')
        updater.idle()


if __name__ == '__main__':
    main()

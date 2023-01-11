import os

import requests

import logging

from typing import Any, Dict, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv('TOKEN')

# State definitions for top level conversation
SELECTING_ACTION, ADDING_MEMBER, ADDING_SELF, DESCRIBING_SELF = map(chr, range(4))
# State definitions for second level conversation
SELECTING_LEVEL, SELECTING_GENDER = map(chr, range(4, 6))
# State definitions for descriptions conversation
SELECTING_FEATURE, TYPING = map(chr, range(6, 8))
# Meta states
STOPPING, SHOWING = map(chr, range(8, 10))
# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Different constants for this example
(
    PARENTS,
    CHILDREN,
    SELF,
    GENDER,
    MALE,
    FEMALE,
    AGE,
    NAME,
    START_OVER,
    FEATURES,
    CURRENT_FEATURE,
    CURRENT_LEVEL,
    N_GENDER,
    GOAL,
    LEVEL,
    EQUIPMENT,
    TIME,
    LIMITATIONS,
    EXPERIENCE,
    NUTRITION,
    HEART,
    SLEEP,
    STRESS,
) = map(chr, range(10, 33))


# Helper
def get_answer(prompt):
    # Send a POST request to the Flask app with the prompt
    url = "http://127.0.0.1:5000"
    data = {'prompt': prompt}
    headers = {'Content-Type': 'application/json'}

    response = requests.post(
        url, json=data, headers=headers
    )
    # Get the answer from the response
    answer = response.text
    return answer


# Top level conversation callbacks
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Select an action: Adding parent/child or show data."""
    text = (
        "You may choose to add a family member, yourself, show the gathered data, or end the "
        "conversation. To abort, simply type /stop."
    )

    buttons = [
        [
            InlineKeyboardButton(text="План тренировок", callback_data=str(ADDING_MEMBER)),
            InlineKeyboardButton(text="Настройки профиля", callback_data=str(ADDING_SELF)),
        ],
        [
            InlineKeyboardButton(text="Мои данные", callback_data=str(SHOWING)),
            InlineKeyboardButton(text="Done", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need to send a new message
    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "Hi, I'm Family Bot and I'm here to help you gather information about your family."
        )
        await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_ACTION


async def adding_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Add information about yourself."""
    context.user_data[CURRENT_LEVEL] = SELF
    text = "Okay, please tell me about yourself."
    button = InlineKeyboardButton(text="Add info", callback_data=str(MALE))
    keyboard = InlineKeyboardMarkup.from_button(button)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return DESCRIBING_SELF


async def show_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Pretty print gathered data."""

    def pretty_print(data: Dict[str, Any], level: str) -> str:
        people = data.get(level)
        if not people:
            return "\nNo information yet."

        return_str = ""
        if level == SELF:
            for person in data[level]:
                return_str += (f"\nИмя: {person.get(NAME, '-')}, Возраст: {person.get(AGE, '-')}, "
                               f"Пол: {person.get(N_GENDER, '-')}")
        else:
            male, female = _name_switcher(level)

            for person in data[level]:
                gender = female if person[GENDER] == FEMALE else male
                return_str += (
                    f"\n{gender}: Name: {person.get(NAME, '-')}, Age: {person.get(AGE, '-')}"
                )
        return return_str

    user_data = context.user_data
    text = f"Yourself:{pretty_print(user_data, SELF)}"
    text += f"\n\nParents:{pretty_print(user_data, PARENTS)}"
    text += f"\n\nChildren:{pretty_print(user_data, CHILDREN)}"

    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    user_data[START_OVER] = True
    return SHOWING


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End Conversation by command."""
    await update.message.reply_text("Okay, bye.")
    return END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation from InlineKeyboardButton."""
    await update.callback_query.answer()

    text = "See you around!"
    await update.callback_query.edit_message_text(text=text)

    return END


# Second level conversation callbacks
async def select_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    # Generate prompt for OpnAI
    def generate_prompt(
            gender='женщины', age='45',
            goal='сбросить вес', level='новичок',
            equipment='гантелей', time='3 дня в неделю',
            limitation='нет', experience='нет', nutrition='нет',
            heart='70', sleep='нормальный', stress='средний'):
        return """ Создай индивидуальный 6-недельный план тренировок для 
пользователя {} лет, с целью {}, текущим уровнем физической подготовки {}, 
наличием {}, наличием времени {}, физическими ограничениями {}, 
прошлый опыт тренировок {}, привычки питания {}, 
частота пульса в покое {}, режим сна {} , и уровни стресса {}.
    """.format(
            gender, age, goal, level, equipment, time,
            limitation, experience, nutrition, heart, sleep, stress
        )

    """Pretty print gathered data."""
    def pretty_print(data: Dict[str, Any], level: str) -> str:
        people = data.get(level)
        if not people:
            return "\nNo information yet."
        if level == SELF:
            for person in data[level]:
                name = person.get(NAME)
                age = person.get(AGE)
                gender = person.get(GENDER)
                goal = person.get(GOAL)
                equipment = person.get(EQUIPMENT)
                answer = get_answer(
                    generate_prompt(
                        gender=gender, age=age, goal=goal, equipment=equipment,

                    )
                )
                return answer

    user_data = context.user_data
    text = f"Yourself:{pretty_print(user_data, SELF)}"

    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    user_data[START_OVER] = True

    return SELECTING_LEVEL


async def select_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Choose to add mother or father."""
    level = update.callback_query.data
    context.user_data[CURRENT_LEVEL] = level

    text = "Please choose, whom to add."

    male, female = _name_switcher(level)

    buttons = [
        [
            InlineKeyboardButton(text=f"Add {male}", callback_data=str(MALE)),
            InlineKeyboardButton(text=f"Add {female}", callback_data=str(FEMALE)),
        ],
        [
            InlineKeyboardButton(text="Show data", callback_data=str(SHOWING)),
            InlineKeyboardButton(text="Back", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_GENDER


async def end_second_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


# Third level callbacks
async def select_feature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Select a feature to update for the person."""
    buttons = [
        [
            InlineKeyboardButton(text="Имя", callback_data=str(NAME)),
            InlineKeyboardButton(text="Пол", callback_data=str(N_GENDER)),
            InlineKeyboardButton(text="Возраст", callback_data=str(AGE)),
        ],
        [InlineKeyboardButton(text="Цель тренировок", callback_data=str(GOAL))],
        [InlineKeyboardButton(text="Текущий уровень физической подготовки", callback_data=str(LEVEL))],
        [InlineKeyboardButton(text="Доступное оборудование", callback_data=str(EQUIPMENT))],
        [InlineKeyboardButton(text="Доступное время", callback_data=str(TIME))],
        [InlineKeyboardButton(text="Физические ограничения", callback_data=str(LIMITATIONS))],
        [InlineKeyboardButton(text="Прошлый опыт тренировок", callback_data=str(EXPERIENCE))],
        [InlineKeyboardButton(text="Питание", callback_data=str(NUTRITION))],
        [InlineKeyboardButton(text="Сердце", callback_data=str(HEART))],
        [InlineKeyboardButton(text="Сон", callback_data=str(SLEEP))],
        [InlineKeyboardButton(text="Уровень стресса", callback_data=str(STRESS))],
        [InlineKeyboardButton(text="Done", callback_data=str(END))],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we collect features for a new person, clear the cache and save the gender
    if not context.user_data.get(START_OVER):
        context.user_data[FEATURES] = {GENDER: update.callback_query.data}
        text = "Please select a feature to update."

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # But after we do that, we need to send a new message
    else:
        text = "Got it! Please select a feature to update."
        if update.message is None:
            await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_FEATURE


async def ask_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Prompt user to input data for selected feature."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = f"Okay, tell me"

    await update.callback_query.answer()
    if context.user_data[CURRENT_FEATURE] == N_GENDER:
        buttons = [
            [
                InlineKeyboardButton(text="Мужской", callback_data="Мужской"),
                InlineKeyboardButton(text="Женский", callback_data="Женский"),
                InlineKeyboardButton(text="Другой", callback_data="Другой"),
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        text = "Пожалуйста, укажите свой пол. Выберите один из вариантов ниже"
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        if context.user_data[CURRENT_FEATURE] == GOAL:
            text = ("Какова ваша конечная цель в фитнесе? "
                    "(потеря веса, набор мышечной массы, общая физическая форма и т. д.)")
        await update.callback_query.edit_message_text(text=text)
    return TYPING


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Save input for feature and return to feature selection."""
    user_data = context.user_data
    # Determine if the update is a message update or a callback query update
    if update.message:
        # Update is a message update
        user_input = update.message.text
    else:
        # Update is a callback query update
        user_input = update.callback_query.data
    user_data[FEATURES][user_data[CURRENT_FEATURE]] = user_input
    user_data[START_OVER] = True
    return await select_feature(update, context)


async def end_describing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End gathering of features and return to parent conversation."""
    user_data = context.user_data
    level = user_data[CURRENT_LEVEL]
    if not user_data.get(level):
        user_data[level] = []
    user_data[level].append(user_data[FEATURES])
    # Print upper level menu
    if level == SELF:
        user_data[START_OVER] = True
        await start(update, context)
    else:
        await select_level(update, context)
    return END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Completely end conversation from within nested conversation."""
    await update.message.reply_text("Okay, bye.")
    return STOPPING


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Set up third level ConversationHandler (collecting features)
    description_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                select_feature, pattern="^" + str(MALE) + "$|^" + str(FEMALE) + "$"
            )
        ],
        states={
            SELECTING_FEATURE: [
                CallbackQueryHandler(ask_for_input, pattern="^(?!" + str(END) + ").*$")
            ],
            TYPING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_input),
                CallbackQueryHandler(save_input, pattern="^(?!" + str(END) + ").*$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(end_describing, pattern="^" + str(END) + "$"),
            CommandHandler("stop", stop_nested),
        ],
        map_to_parent={
            # Return to second level menu
            END: SELECTING_LEVEL,
            # End conversation altogether
            STOPPING: STOPPING,
        },
    )

    # Set up second level ConversationHandler (adding a person)
    add_member_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_level, pattern="^" + str(ADDING_MEMBER) + "$")],
        states={
            SELECTING_LEVEL: [
                CallbackQueryHandler(select_gender, pattern=f"^{PARENTS}$|^{CHILDREN}$")
            ],
            SELECTING_GENDER: [description_conv],
        },
        fallbacks=[
            CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
            CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
            CommandHandler("stop", stop_nested),
        ],
        map_to_parent={
            # After showing data return to top level menu
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation altogether
            STOPPING: END,
        },
    )

    # Set up top level ConversationHandler (selecting action)
    # Because the states of the third level conversation map to the ones of the second level
    # conversation, we need to make sure the top level conversation can also handle them
    selection_handlers = [
        add_member_conv,
        CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
        CallbackQueryHandler(adding_self, pattern="^" + str(ADDING_SELF) + "$"),
        CallbackQueryHandler(end, pattern="^" + str(END) + "$"),
    ]
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHOWING: [CallbackQueryHandler(start, pattern="^" + str(END) + "$")],
            SELECTING_ACTION: selection_handlers,
            SELECTING_LEVEL: selection_handlers,
            DESCRIBING_SELF: [description_conv],
            STOPPING: [CommandHandler("start", start)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    )

    application.add_handler(conv_handler)
    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()

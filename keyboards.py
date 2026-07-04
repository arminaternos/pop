from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from menus import MENU


def create_menu(menu_name):

    keyboard = []

    for text, callback in MENU[menu_name]["buttons"].items():
        keyboard.append(
            [InlineKeyboardButton(text, callback_data=callback)]
        )

    if menu_name != "main":
        keyboard.append(
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        )

    return InlineKeyboardMarkup(keyboard)
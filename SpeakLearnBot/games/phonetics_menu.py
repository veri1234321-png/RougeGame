from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.user_manager import user_manager
from games.base import BaseGame, GameSession, GameStatus
from games.game_phonetics.lesson_phonetics import LessonPhonetics
from games.game_phonetics.listening_test import ListeningTestGame
from games.game_registry import game_registry
from utils import safe_edit_message
from utils.localization import translator


class Phonetics(BaseGame):
    def __init__(self):
        super().__init__(game_id="phonetics")

    def get_display_name(self, lang: str) -> str:
        return translator.get_text("game_ph_name", lang)

    async def start_game(self, bot: Bot, user_id: int, message: Message) -> GameSession:
        user = await user_manager.get_user(user_id)
        lang = user.language if user else "en"

        session = GameSession(
            user_id=user_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            game_id=self.game_id,
            status=GameStatus.IN_PROGRESS,
            current_question=0,
            score=0,
            game_state={"lang": lang}
        )

        await self._send_game_menu(bot, session)
        return session

    async def _send_game_menu(self, bot: Bot, session: GameSession, message_id: int = 0):
        lang = session.game_state.get("lang", "en")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                # [InlineKeyboardButton(text=translator.get_text("game_ph_btn_sound", lang),
                #                       callback_data="phonetics:sounds")],
                # [InlineKeyboardButton(text=translator.get_text("game_ph_btn_repeat", lang),
                #                       callback_data="phonetics:repeat")],
                [InlineKeyboardButton(text=translator.get_text("game_ph_btn_lesson", lang),
                                      callback_data="phonetics:lesson")],
                [InlineKeyboardButton(text=translator.get_text("game_ph_btn_test", lang),
                                      callback_data="phonetics:test")],
                [InlineKeyboardButton(text=translator.get_text("back_button", lang),
                                      callback_data="show_menu")]
            ]
        )

        new_message_id = await safe_edit_message(
            bot=bot,
            chat_id=session.chat_id,
            message_id=session.message_id if message_id == 0 else message_id,
            text=translator.get_text("game_ph_text_choose_game", lang),
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        session.message_id = new_message_id


    async def resume_game(self, bot: Bot, session: GameSession):
        await self._send_game_menu(bot, session)

    async def handle_callback(self, bot: Bot, session: GameSession, callback: CallbackQuery) -> GameSession:
        lang = session.game_state.get("lang", "en")
        action, *data = callback.data.split(":")

        if action == "phonetics":
            subgame = data[0]

            if subgame == "test":
                game = ListeningTestGame()
                new_session = await game.start_game(
                    bot,
                    session.user_id,
                    callback.message
                )

                await callback.answer()
                return new_session
            elif subgame == "lesson":
                game = LessonPhonetics()
                new_session = await game.start_game(
                    bot,
                    session.user_id,
                    callback.message
                )

                await callback.answer()
                return new_session
            else:
                await callback.answer(
                    translator.get_text("game_ph_not_ready", lang),
                    show_alert=True
                )
        return session

    async def end_game(self, bot: Bot, session: GameSession, send_message: bool = True):
        pass


game_registry.register(Phonetics())
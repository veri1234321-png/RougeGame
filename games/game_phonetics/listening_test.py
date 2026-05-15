from aiogram import Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from data.phonetics_listening_test_data import LISTENING_TEST_QUESTIONS
from games.base import BaseGame, GameSession, GameStatus
from games.game_registry import game_registry
from utils.localization import translator
from database.user_manager import user_manager


async def get_user_language(user_id: int) -> str:
    user = await user_manager.get_user(user_id)
    return user.language if user else "en"


class ListeningTestGame(BaseGame):
    def __init__(self):
        super().__init__(game_id="phonetics_listening_test")

    def get_display_name(self, lang: str) -> str:
        return translator.get_text("game_ph_btn_test", lang)

    async def start_game(self, bot: Bot, user_id: int, message: Message) -> GameSession:
        lang = await get_user_language(user_id)

        session = GameSession(
            user_id=user_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            game_id=self.game_id,
            status=GameStatus.IN_PROGRESS,
            current_question=0,
            score=0,
            game_state={
                "lang": lang
            }
        )

        await self._send_question(bot, session)
        return session

    async def _send_question(self, bot: Bot, session: GameSession):
        q_index = session.current_question
        lang = await self._get_session_language(session)

        if q_index >= len(LISTENING_TEST_QUESTIONS):
            session.status = GameStatus.FINISHED
            await self.end_game(bot, session)
            return

        question = LISTENING_TEST_QUESTIONS[q_index]

        question_text = translator.get_text(question["question"], lang)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(i),
                        callback_data=f"lt_answer:{q_index}:{i}"
                    )
                    for i in range(1, 6)
                ]
            ]
        )

        sent_message = await bot.send_audio(
            chat_id=session.chat_id,
            audio=question["audio"],
            caption=question_text,
            reply_markup=keyboard,
            request_timeout=60
        )

        session.message_id = sent_message.message_id

    async def handle_callback(
        self,
        bot: Bot,
        session: GameSession,
        callback: CallbackQuery
    ) -> GameSession:

        await callback.answer()
        lang = await self._get_session_language(session)

        if callback.data.startswith("lt_answer:"):
            _, q_index_str, user_answer = callback.data.split(":")
            q_index = int(q_index_str)

            if q_index != session.current_question:
                return session

            question = LISTENING_TEST_QUESTIONS[q_index]
            correct_answer = question["correct"]

            if str(user_answer) == str(correct_answer):
                session.score += 1
                text = translator.get_text("lt_correct", lang)
            else:
                text = translator.get_text(
                    "lt_wrong",
                    lang
                ).format(correct=correct_answer)

            try:
                await bot.delete_message(
                    chat_id=session.chat_id,
                    message_id=session.message_id
                )
            except Exception:
                pass

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=translator.get_text(
                                "game_ph_btn_next",
                                lang
                            ),
                            callback_data="lt_next"
                        )
                    ]
                ]
            )

            result_message = await bot.send_message(
                chat_id=session.chat_id,
                text=text,
                reply_markup=keyboard
            )

            session.message_id = result_message.message_id
            return session

        elif callback.data == "lt_next":
            try:
                await bot.delete_message(
                    chat_id=session.chat_id,
                    message_id=session.message_id
                )
            except Exception:
                pass

            session.current_question += 1
            await self._send_question(bot, session)
            return session

        return session

    async def resume_game(self, bot: Bot, session: GameSession):
        await self._send_question(bot, session)

    async def end_game(
        self,
        bot: Bot,
        session: GameSession,
        send_message: bool = True
    ):
        if send_message:
            lang = await self._get_session_language(session)

            total = len(LISTENING_TEST_QUESTIONS)

            text = translator.get_text(
                "lt_finished",
                lang
            ).format(
                score=session.score,
                total=total
            )

            try:
                await bot.delete_message(
                    chat_id=session.chat_id,
                    message_id=session.message_id
                )
            except Exception:
                pass

            await bot.send_message(
                chat_id=session.chat_id,
                text=text
            )

    async def _get_session_language(self, session: GameSession) -> str:
        lang = session.game_state.get("lang")

        if not lang:
            lang = await get_user_language(session.user_id)
            session.game_state["lang"] = lang

        return lang


game_registry.register(ListeningTestGame())
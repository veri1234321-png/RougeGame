import os

from aiogram import Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)

import random

from SpeakLearnBot.data.phonetics_data import PHONETICS_LESSONS_DATA, POSITIVE_FEEDBACKS_PHONETICS
from SpeakLearnBot.utils.localization import translator
from SpeakLearnBot.database.user_manager import user_manager
from .base import BaseGame, GameSession, GameStatus
from .game_registry import game_registry
from SpeakLearnBot.utils.bot_helpers import safe_edit_message

"""
        session.status = GameStatus.FINISHED
"""
async def get_user_language(user_id: int) -> str:
    user = await user_manager.get_user(user_id)
    return user.language if user else "en"


class PhoneticsGame(BaseGame):
    def __init__(self):
        super().__init__(game_id="phonetics")

    def get_display_name(self, lang: str) -> str:
        return translator.get_text("game_phonetics_name", lang)

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
                "lang": lang,
                "current_lesson_index": None,
                "current_audio_index": None,
                "last_voice_id": None            },
        )
        await self._send_lesson_selection(bot, session)
        return session

    async def resume_game(self, bot: Bot, session: GameSession):
        lang = await self._get_session_language(session)
        resume_text = translator.get_text("game_phonetics_resume_text", lang)
        await bot.send_message(session.chat_id, resume_text)

        if session.game_state.get("current_lesson_index") is None:
            await self._send_lesson_selection(bot, session, as_new_message=True)
        else:
            await self._send_current_step(bot, session, is_new_step=True)

    async def _send_lesson_selection(
            self, bot: Bot, session: GameSession, as_new_message: bool = False
    ):
        lang = await self._get_session_language(session)

        await self._cleanup_previous_voice(bot, session)
        row = []
        buttons = []

        for index, lesson in enumerate(PHONETICS_LESSONS_DATA):
            button_text = translator.get_text(
                "game_phonetics_lesson_label" + str(index + 1), lang
            )
            button = InlineKeyboardButton(
                text=button_text,
                callback_data=f"phonetics_select_lesson:{index}",
            )
            row.append(button)

            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        menu_button = InlineKeyboardButton(
            text=translator.get_text("game_phonetics_button_menu_back", lang),
            callback_data="show_menu",
        )
        buttons.append([menu_button])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = translator.get_text("game_phonetics_choose_lesson", lang)

        if as_new_message:
            sent_message = await bot.send_message(
                chat_id=session.chat_id,
                text=text,
                reply_markup=keyboard,
            )
            session.message_id = sent_message.message_id
        else:
            new_message_id = await safe_edit_message(
                bot=bot,
                chat_id=session.chat_id,
                message_id=session.message_id,
                text=text,
                reply_markup=keyboard,
            )
            if new_message_id:
                session.message_id = new_message_id
            else:
                sent_message = await bot.send_message(
                    chat_id=session.chat_id,
                    text=text,
                    reply_markup=keyboard,
                )
                session.message_id = sent_message.message_id

    async def _cleanup_previous_voice(self, bot: Bot, session: GameSession):
        last_voice_id = session.game_state.get("last_voice_id")
        if last_voice_id:
            try:
                await bot.delete_message(
                    chat_id=session.chat_id, message_id=last_voice_id
                )
            except Exception:
                pass
            session.game_state["last_voice_id"] = None

    async def _send_current_step(
        self, bot: Bot, session: GameSession, is_new_step: bool = False
    ):
        lang = await self._get_session_language(session)

        lesson_index = session.game_state["current_lesson_index"]
        audio_index = session.game_state["current_audio_index"]


        lesson = PHONETICS_LESSONS_DATA[lesson_index]
        audio_files = lesson["audio_files"]
        current_audio_path = audio_files[audio_index]

        lesson_name = self._get_lesson_name(lesson_index, lang)
        step_text = self._format_step_text(
            lesson_name=lesson_name,
            step_number=audio_index + 1,
            total_steps=len(audio_files),
            lang=lang,
            session=session
        )

        if is_new_step:

            if session.message_id:
                try:
                    await bot.delete_message(chat_id=session.chat_id, message_id=session.message_id)
                except Exception:
                    pass
            await self._cleanup_previous_voice(bot, session)

            # отправляем новый voice
            await bot.send_chat_action(session.chat_id, "upload_voice")
            try:
                with open(current_audio_path, "rb") as f:
                    voice_bytes = f.read()
            except FileNotFoundError:
                error_text = translator.get_text(
                    "game_phonetics_audio_missing", lang
                ).format(path=current_audio_path)
                await bot.send_message(session.chat_id, error_text)
                return

            voice_msg = await bot.send_voice(
                chat_id=session.chat_id,
                voice=BufferedInputFile(
                    voice_bytes, filename=os.path.basename(current_audio_path)
                ),
            )
            session.game_state["last_voice_id"] = voice_msg.message_id

            keyboard = self._build_step_keyboard(
                lang=lang,
                lesson_index=lesson_index,
                audio_index=audio_index,
                total_steps=len(audio_files),
            )

            sent_message = await bot.send_message(
                chat_id=session.chat_id,
                text=step_text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            session.message_id = sent_message.message_id
        else:
            keyboard = self._build_step_keyboard(
                lang=lang,
                lesson_index=lesson_index,
                audio_index=audio_index,
                total_steps=len(audio_files),
            )
            new_message_id = await safe_edit_message(
                bot=bot,
                chat_id=session.chat_id,
                message_id=session.message_id,
                text=step_text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            if not new_message_id:
                sent = await bot.send_message(
                    chat_id=session.chat_id,
                    text=step_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
                session.message_id = sent.message_id

    def _build_step_keyboard(
        self,
        lang: str,
        lesson_index: int,
        audio_index: int,
        total_steps: int,
    ) -> InlineKeyboardMarkup:
        is_last = (audio_index + 1) >= total_steps

        if is_last:
            next_cb = "phonetics_finish_lesson"
            next_text_key = "game_phonetics_button_finish_lesson"
        else:
            next_cb = "phonetics_next_step"
            next_text_key = "game_phonetics_button_next_step"

        next_button = InlineKeyboardButton(
            text=translator.get_text(next_text_key, lang),
            callback_data=next_cb,
        )

        menu_button = InlineKeyboardButton(
            text=translator.get_text("game_phonetics_button_menu", lang),
            callback_data="phonetics_show_menu",
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[next_button], [menu_button]]
        )
        return keyboard


    async def handle_callback(
        self, bot: Bot, session: GameSession, callback: CallbackQuery
    ) -> GameSession:
        action, *data = callback.data.split(":")

        if action == "phonetics_select_lesson":
            lesson_index = int(data[0])
            session.game_state["current_lesson_index"] = lesson_index
            session.game_state["current_audio_index"] = 0
            session.current_question = 0
            await self._send_current_step(bot, session, is_new_step=True)
            await callback.answer()

        elif action == "phonetics_next_step":
            lesson_index = session.game_state["current_lesson_index"]
            audio_index = session.game_state["current_audio_index"]

            audio_index += 1
            session.game_state["current_audio_index"] = audio_index
            session.current_question = audio_index

            await self._send_current_step(bot, session, is_new_step=True)
            await callback.answer()

        elif action == "phonetics_finish_lesson":
            session.status = GameStatus.FINISHED
            await self.end_game(bot, session)
            await callback.answer()

        elif action == "phonetics_show_menu":
            await self._send_lesson_selection(bot, session)
            await callback.answer()



        elif action == "phonetics_next_lesson":
            current_lesson_index = session.game_state.get("current_lesson_index", 0)
            if current_lesson_index >= len(PHONETICS_LESSONS_DATA) - 1:
                await self._send_lesson_selection(bot, session)
                lang = await self._get_session_language(session)
                await callback.answer(translator.get_text("game_phonetics_it_was_last_lesson", lang))
            else:
                next_lesson_index = current_lesson_index + 1
                session.game_state["current_lesson_index"] = next_lesson_index
                session.game_state["current_audio_index"] = 0
                session.current_question = 0
                session.score = 0
                await self._send_current_step(bot, session, is_new_step=True)
                await callback.answer(f"Урок {next_lesson_index + 1}")

        return session

    async def end_game(self, bot: Bot, session: GameSession, send_message: bool = True):
        await self._cleanup_previous_voice(bot, session)

        if send_message:
            lang = await self._get_session_language(session)
            final_text = translator.get_text("game_phonetics_end_text", lang).format(score=session.score) + "\n\n" + random.choice(POSITIVE_FEEDBACKS_PHONETICS.get(lang, []))

            current_lesson_index = session.game_state.get("current_lesson_index")

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=translator.get_text("game_phonetics_button_repeat_lesson", lang),
                        callback_data=f"phonetics_select_lesson:{current_lesson_index}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=translator.get_text("game_phonetics_button_next_lesson", lang),
                        callback_data="phonetics_next_lesson"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=translator.get_text("game_phonetics_button_lesson_menu", lang),
                        callback_data="phonetics_show_menu"
                    )
                ]
            ])

            session.status = GameStatus.IN_PROGRESS

            try:
                await safe_edit_message(
                    bot=bot,
                    chat_id=session.chat_id,
                    message_id=session.message_id,
                    text=final_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            except Exception:
                sent_msg = await bot.send_message(
                    chat_id=session.chat_id,
                    text=final_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
                session.message_id = sent_msg.message_id

    async def _get_session_language(self, session: GameSession) -> str:
        lang = session.game_state.get("lang")
        if not lang:
            lang = await get_user_language(session.user_id)
            session.game_state["lang"] = lang
        return lang

    def _format_step_text(
        self,
        lesson_name: str,
        step_number: int,
        total_steps: int,
        lang: str,
        session: GameSession
    ) -> str:
        lesson_index = session.game_state["current_lesson_index"]
        lesson_label = translator.get_text(
            "game_phonetics_lesson_label" + str(lesson_index + 1), lang
        ).format(lesson_name=lesson_name)

        step_label = translator.get_text(
            "game_phonetics_step_label", lang
        ).format(current=step_number, total=total_steps) + " " + str(step_number) + "/" + str(total_steps)

        listen_prompt = translator.get_text(
            "game_phonetics_hint" + str(lesson_index + 1) + "_" + str(step_number), lang
        )
        confirm_hint = translator.get_text(
            "game_phonetics_listen_prompt" + str(lesson_index + 1) + "_" + str(step_number), lang
        )
        menu_hint = translator.get_text("menu_hint", lang)

        parts = [
            f"*{lesson_label}*",
            step_label,
            f"_{listen_prompt}_",
            confirm_hint,
            menu_hint,
        ]
        return "\n\n".join(parts)

    def _get_lesson_name(self, lesson_index: int, lang: str) -> str:
        lesson_key = PHONETICS_LESSONS_DATA[lesson_index]["lesson_name"]
        return translator.get_text(lesson_key, lang)


game_registry.register(PhoneticsGame())
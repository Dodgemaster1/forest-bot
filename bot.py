import asyncio
import io
import logging
import os
import secrets
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Document, Message
from aiogram.utils.chat_action import ChatActionMiddleware
from dotenv import load_dotenv

from db import DB
from dirs import FOREST_ARCHIVE_DIR
from rag import RAG

ARCHIVE_FILENAMES = {file.name for file in FOREST_ARCHIVE_DIR.iterdir()}

load_dotenv()

if not (TOKEN := os.getenv("BOT_TOKEN")):
    raise ValueError("BOT_TOKEN environment variable is not set")


class FSM(StatesGroup):
    waiting_for_name = State()


dp = Dispatcher(db=DB(), rag=RAG())

dp.message.outer_middleware(ChatActionMiddleware())


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привіт, лісовий друже! 🐾\n\n"
        "Я — спільна база знань для звірів. Базові документи з «Лісового архіву» я вже знаю!\n"
        "📄 *Хочеш поділитися порадою?* Просто надішли файл (PDF, DOCX або TXT).\n"
        "❓ *Маєш запитання?* Напиши його звичайним повідомленням!",
        parse_mode="Markdown",
    )


@dp.message(
    F.document.file_name.lower().endswith((".pdf", ".docx", ".txt")) & (F.document.file_size < 10 * 1024 * 1024)
)
async def handle_document(message: Message, state: FSMContext, db: DB, bot: Bot, rag: RAG) -> None:
    # pyrefly: ignore[missing-attribute]
    if db.get_user_by_id(message.from_user.id) is None:
        await state.set_state(FSM.waiting_for_name)
        await state.set_data({"document": message.document})
        await message.answer("Напиши своє імʼя:")
    else:
        # pyrefly: ignore[bad-argument-type, missing-attribute]
        await process_document(message.document, bot, db, message.from_user.id, rag)
        await message.answer("Файл збережено! 🐾")


@dp.message(F.text, FSM.waiting_for_name)
async def handle_name(message: Message, state: FSMContext, db: DB, bot: Bot, rag: RAG) -> None:
    # pyrefly: ignore[missing-attribute]
    name = message.text.strip()

    if len(name) < 2 or len(name) > 50:  # ruff: ignore[magic-value-comparison]
        await message.answer("Введи коректне ім'я (від 2 до 50 символів).")
        return

    data = await state.get_data()
    # pyrefly: ignore[missing-attribute]
    await process_document(data["document"], bot, db, message.from_user.id, rag)

    # pyrefly: ignore[missing-attribute]
    db.add_user(name, message.from_user.id)
    await state.clear()
    await message.answer(
        f"Приємно познайомитися, *{name}*! Запам'ятав. 🐾",
        parse_mode="Markdown",
    )


@dp.message(F.text)
async def ask_question_handler(message: Message, db: DB, rag: RAG) -> None:
    response, filename = await rag.generate_answer(str(message.text))
    if not filename:
        await message.answer("Не знайдено відповідь на ваше запитання.")
        return
    if filename in ARCHIVE_FILENAMES:
        answer = f"*Відповідь:* {response}\n\n*Джерело:* {filename} з «Лісового архіву»"
    else:
        author = db.get_user_by_document(filename)
        answer = f"*Відповідь:* {response}\n\n**Джерело:** {filename}\n*Автор:* {author.name if author else 'Невідомо'}"
    await message.answer(answer, parse_mode="Markdown")


async def process_document(document: Document, bot: Bot, db: DB, user_id: int, rag: RAG) -> None:
    # pyrefly: ignore[bad-assignment]
    document_buffer: io.BytesIO | None = await bot.download(document)
    if document_buffer is None:
        await bot.send_message(user_id, "Не вдалося завантажити файл. Спробуйте ще раз.")
        return
    # pyrefly: ignore[missing-attribute]
    original_path = Path(document.file_name or "document.txt")
    # Например, было "лісові_поради.pdf" -> станет "лісові_поради_4f8a2b1c.pdf"
    save_name = f"{original_path.stem}_{secrets.token_hex(4)}{original_path.suffix}"
    db.save_document(user_id, save_name)
    await rag.add_document(document_buffer, save_name)


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())

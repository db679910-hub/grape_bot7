import asyncio
import logging
import time
import os
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
GRAPE_REWARD = 5
COOLDOWN_SECONDS = 60

logging.basicConfig(level=logging.INFO)

# Глобальное подключение к БД
pool = None

async def init_db():
    """Создаёт таблицу пользователей"""
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_collect INTEGER DEFAULT 0
            )
        ''')
    logging.info("✅ База данных подключена!")

async def get_user(user_id):
    """Получает данные пользователя"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT balance, last_collect FROM users WHERE user_id = $1',
            user_id
        )
        if row:
            return (row['balance'], row['last_collect'])
        else:
            await add_user(user_id)
            return (0, 0)

async def add_user(user_id):
    """Регистрирует нового пользователя"""
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING',
            user_id
        )

async def update_balance(user_id, amount):
    """Обновляет баланс"""
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET balance = balance + $1 WHERE user_id = $2',
            amount, user_id
        )

async def update_time(user_id, timestamp):
    """Обновляет время сбора"""
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET last_collect = $1 WHERE user_id = $2',
            timestamp, user_id
        )

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.from_user.id)
    await message.answer(
        f"🍇 Привет, {message.from_user.first_name}!\n\n"
        f"Собирай виноград:\n"
        f"/сбор — собрать (+{GRAPE_REWARD}🍇)\n"
        f"/баланс — проверить"
    )

@dp.message(Command("сбор", "collect"))
async def cmd_collect(message: Message):
    user_id = message.from_user.id
    now = int(time.time())
    balance, last_time = await get_user(user_id)
    
    if now - last_time < COOLDOWN_SECONDS:
        wait = COOLDOWN_SECONDS - (now - last_time)
        await message.answer(f"⏳ Виноград ещё растёт! Подожди {wait} сек")
        return
    
    await update_balance(user_id, GRAPE_REWARD)
    await update_time(user_id, now)
    await message.answer(
        f"🍇 +{GRAPE_REWARD} винограда!\n"
        f"Всего собрано: {balance + GRAPE_REWARD}"
    )

@dp.message(Command("баланс", "balance"))
async def cmd_balance(message: Message):
    balance, _ = await get_user(message.from_user.id)
    await message.answer(f"🍇 **Ваш баланс**: {balance} 🍇")

async def main():
    await init_db()
    logging.info("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

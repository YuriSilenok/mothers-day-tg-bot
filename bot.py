import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import AiogramError

from models import Video

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv('TG_TOKEN'))
dp = Dispatcher()
ADMIN_ID = int(os.getenv('ADMIN_ID'))

def get_videos_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с подписями видео"""
    try:
        videos = Video.select()
        if not videos:
            return None
            
        builder = ReplyKeyboardBuilder()
        
        for video in videos:
            # Обрезаем длинные подписи для кнопок
            button_text = video.caption[:30] + "..." if len(video.caption) > 30 else video.caption
            builder.add(KeyboardButton(text=button_text))
        
        builder.adjust(3)
        return builder.as_markup(resize_keyboard=True)
        
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры: {e}")
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    try:
        keyboard = get_videos_keyboard()
        if keyboard:
            await message.answer(
                "🎬 Добро пожаловать! Выберите видео из меню ниже:",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                "📝 Пока нет доступных видео. Администратор может добавить видео."
            )
    except Exception as e:
        logger.error(f"Ошибка в команде start: {e}")
        await message.answer("❌ Произошла ошибка")

@dp.message(F.video, F.from_user.id == ADMIN_ID)
async def handle_admin_video(message: types.Message):
    """Обработчик видео от администратора"""
    try:
        video_file_id = message.video.file_id
        video_caption = message.caption.strip() if message.caption else "Без названия"
        
        # Проверяем длину подписи
        if len(video_caption) > 100:
            await message.answer("❌ Подпись слишком длинная (макс. 100 символов)")
            return
        
        # Сохраняем или обновляем видео
        video, created = Video.get_or_create(
            file_id=video_file_id,
            defaults={'caption': video_caption}
        )
        
        if not created:
            video.caption = video_caption
            video.save()
        
        logger.info(f"Видео {'создано' if created else 'обновлено'}: {video_caption}")
        
        keyboard = get_videos_keyboard()
        await message.answer(
            f"✅ Видео {'сохранено' if created else 'обновлено'}!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении видео: {e}")
        await message.answer("❌ Ошибка при сохранении видео")

@dp.message(F.text)
async def handle_video_selection(message: types.Message):
    """Обработчик выбора видео из меню"""
    try:
        # Ищем точное совпадение по подписи
        video = Video.get_or_none(Video.caption == message.text)
        
        if not video:
            # Если точного совпадения нет, ищем по началу строки
            videos = Video.select().where(Video.caption.startswith(message.text))
            if videos:
                video = videos.first()
        
        if video:
            await message.answer_video(
                video.file_id,
                caption=video.caption
            )
            logger.info(f"Отправлено видео: {video.caption}")
        else:
            keyboard = get_videos_keyboard()
            if keyboard:
                await message.answer(
                    "❌ Видео не найдено. Пожалуйста, выберите из меню:",
                    reply_markup=keyboard
                )
            else:
                await message.answer("❌ Видео не найдено.")
                
    except AiogramError as e:
        logger.error(f"Ошибка Telegram API при отправке видео: {e}")
        await message.answer("❌ Ошибка при отправке видео")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        await message.answer("❌ Произошла непредвиденная ошибка")

@dp.message(F.video)
async def handle_non_admin_video(message: types.Message):
    """Обработчик видео от не-администратора"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для загрузки видео. Обратитесь к администратору.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
🤖 **Команды бота:**

/start - Начать работу с ботом
/help - Показать эту справку

**Для администратора:**
- Отправьте видео с подписью чтобы добавить его в базу

**Для всех пользователей:**
- Используйте меню для выбора и просмотра видео
    """
    await message.answer(help_text)

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
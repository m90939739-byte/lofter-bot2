import re
import asyncio
from bs4 import BeautifulSoup
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InputMediaPhoto

BOT_TOKEN = "8798838686:AAGCfzd-XUiWnAuTamk473GdSSF0-oECZoE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_lofter_image_url(url: str) -> str:
    return url.split('?')[0]

async def extract_lofter_media(lofter_url: str):
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        response = await client.get(lofter_url)
        if response.status_code != 200:
            return [], []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        photos = []
        videos = []

        # Поиск фото оригинального качества
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('bigimgsrc')
            if src and ('nosdn' in src or 'imglf' in src or 'lofter' in src):
                clean_url = clean_lofter_image_url(src)
                if clean_url not in photos:
                    photos.append(clean_url)

        # Поиск видео
        for video in soup.find_all('video'):
            v_src = video.get('src')
            if v_src:
                videos.append(v_src)
        
        if not videos:
            video_matches = re.findall(r'https?://[^\s"\']+\.mp4', response.text)
            for v_url in video_matches:
                if v_url not in videos:
                    videos.append(v_url)

        return photos, videos

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Пришли мне ссылку на пост LOFTER, и я отправлю фото и видео в оригинальном качестве.")

@dp.message()
async def handle_message(message: types.Message):
    url_match = re.search(r'https?://[^\s]+lofter\.com[^\s]*', message.text)
    if not url_match:
        await message.answer("Отправь нормальную ссылку на LOFTER.")
        return

    lofter_url = url_match.group(0)
    status_msg = await message.answer("⏳ Качаю медиа...")

    try:
        photos, videos = await extract_lofter_media(lofter_url)

        if not photos and not videos:
            await status_msg.edit_text("Не смог найти медиа по этой ссылке.")
            return

        # Отправляем фото
        if photos:
            for i in range(0, len(photos), 10):
                chunk = photos[i:i + 10]
                media_group = [InputMediaPhoto(media=p_url) for p_url in chunk]
                await message.answer_media_group(media=media_group)

        # Отправляем видео
        for v_url in videos:
            await message.answer_video(video=v_url, caption="Видео в оригинальном качестве")

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import uvicorn
from bot import start_bot  # В вашем файле с ботом должна быть функция start_bot()
from config.settings import BASE_DIR

async def start_django():
    """Функция запуска сервера Django на фоне."""
    config = uvicorn.Config("config.asgi:application", host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Основная функция, которая запускает и бота, и сервер Django."""
    # Запускаем две задачи параллельно: Django и бота
    bot_task = asyncio.create_task(start_bot())
    django_task = asyncio.create_task(start_django())

    # Ожидаем завершения обоих процессов
    await asyncio.gather(bot_task, django_task)

if __name__ == "__main__":
    asyncio.run(main())

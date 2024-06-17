import json
import logging
from telegram import Update, ext
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext
from telegram.ext import JobQueue
import requests

# Инициализация логгирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Вставьте сюда токен вашего бота
TELEGRAM_BOT_TOKEN = ''
# Вставьте сюда ваш API ключ от OpenWeatherMap
OPENWEATHER_API_KEY = ''

# Файл для хранения данных пользователей
USER_DATA_FILE = 'user_data.json'

# Словарь для перевода описания погоды
weather_description_translation = {
    'overcast clouds': 'затянутые облаками',
    'clear sky': 'ясное небо',
    'broken clouds': 'разорванные облака',
    'light snow': 'легкий снег',
    'few clouds': 'облачно',
    'scattered clouds': 'рассеянные облака',
    'moderate rain': 'легкий дождь',
    'light rain': 'средний дождь'
}

async def send_weather_updates(context: CallbackContext):
    user_data = load_user_data()
    for user_id, city in user_data.items():
        try:
            weather_info = await get_weather(city)
            await context.bot.send_message(chat_id=int(user_id), text=weather_info)
        except Exception as e:
            logging.error(f"Error sending weather update to user {user_id}: {e}")

async def remind_set_city(context: CallbackContext):
    user_data = load_user_data()
    for user_id, city in user_data.items():
        if not city:  # Проверяем, есть ли установленный город
            try:
                await context.bot.send_message(chat_id=int(user_id), text="Не забудьте установить ваш город! Используйте команду /setcity <город>.")
            except Exception as e:
                logging.error(f"Error sending set city reminder to user {user_id}: {e}")


def load_user_data():
    """Загружает данные пользователей из файла."""
    try:
        with open(USER_DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_user_data(user_data):
    """Сохраняет данные пользователей в файл."""
    with open(USER_DATA_FILE, 'w') as file:
        json.dump(user_data, file)


async def get_weather(city):
    """Получает погоду для указанного города через OpenWeatherMap API."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    if data.get('main'):
        temperature = data['main']['temp']
        weather_description = data['weather'][0]['description']
        weather_description_ru = weather_description_translation.get(weather_description, weather_description)
        return f"RU: Погода в {city}: {temperature}°C, {weather_description_ru}.\nEN: Weather in {city}: {temperature}°C, {weather_description}."
    else:
        return "Извините, не удалось получить данные о погоде. \nПопробуйте /weather <город>"


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет погоду в ответ на команду /weather."""
    city = ' '.join(context.args)
    if city:
        weather_info = await get_weather(city)
        await update.message.reply_text(weather_info)
    else:
        await update.message.reply_text('Пожалуйста, укажите город после команды /weather. Например: /weather London')


async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text('Пожалуйста, укажите ваш город после команды /setcity. Например: /setcity Moscow')
        return

    city = ' '.join(context.args)
    user_id = str(update.message.from_user.id)

    user_data = load_user_data()
    user_data[user_id] = city  # Записываем город пользователя
    save_user_data(user_data)

    await update.message.reply_text(f'Ваш город теперь установлен как {city}.')


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков команд
    weather_handler = CommandHandler("weather", weather)
    set_city_handler = CommandHandler("setcity", set_city)
    application.add_handler(weather_handler)
    application.add_handler(set_city_handler)

    # Настройка JobQueue для автоматической отправки погодных обновлений и напоминаний о установке города
    jq = application.job_queue
    jq.run_repeating(send_weather_updates, interval=11800, first=10)  # Каждые 3 часа
    jq.run_repeating(remind_set_city, interval=43200, first=10)  # Каждые 12 часов

    application.run_polling()

if __name__ == '__main__':
    main()

from __future__ import annotations

# Общие текстовые константы и подсказки бота

PROMPT_CHOOSE_CURRENCY = "Выберите, в какой валюте будет указана цена автомобиля:"
PROMPT_ENTER_PRICE = "Введите стоимость автомобиля (например, 💰 1 200 000):"
PROMPT_CHOOSE_ROLE = "Кто ввозит автомобиль:"
PROMPT_CHOOSE_ENGINE_TYPE = "Выберите тип двигателя:"
PROMPT_ENTER_ENGINE_CC = "Введите объём двигателя в см³ (например, 1500):"
PROMPT_CHOOSE_AGE = "Выберите возраст автомобиля:"
PROMPT_CHOOSE_VEHICLE_TYPE = "Выберите тип автомобиля:"

CONTACT_LINE = "\nСвяжитесь с нами: @Slaford - Слафординка"

# Прочее
RESET_MESSAGE = "Сбросил состояние. Можем начать заново: нажмите 'Калькулятор' или введите /calc"
START_RATES_SOON = "Курсы валют скоро добавлю"
START_LEAD_SOON = "Форму заявки скоро добавлю"

# /calc команда — подсказки/ошибки
CALC_USAGE_EXAMPLE = "/calc 20000 EUR 1999 150 Бензин under_3 phys personal"
CALC_USAGE_HELP = (
        "Неверный формат. Пример: \n" + CALC_USAGE_EXAMPLE
)
CALC_PARSE_ERROR = (
        "Не удалось распарсить аргументы. Пример: \n" + CALC_USAGE_EXAMPLE
)
CALC_EMPTY_MESSAGE = (
        "Сообщение пустое. Пример: " + CALC_USAGE_EXAMPLE
)

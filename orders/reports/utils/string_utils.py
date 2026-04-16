# orders/reports/utils/string_utils.py

def capitalize_name(name):
    """
    Форматирует имя клиента или дебитора с заглавной буквы.
    
    Args:
        name (str): Исходное имя
    
    Returns:
        str: Имя с заглавной буквы в каждом слове
    """
    if not name or not isinstance(name, str):
        return "НЕ УКАЗАН"
    
    name = name.strip()
    
    if not name:
        return "НЕ УКАЗАН"
    
    # Разбиваем на слова и каждое слово делаем с заглавной буквы
    words = name.split()
    capitalized_words = []
    
    for word in words:
        if len(word) > 0:
            # Если слово содержит буквы
            if word.isalpha():
                capitalized_words.append(word.capitalize())
            else:
                # Если слово содержит цифры или спецсимволы, оставляем как есть, 
                # но первую букву делаем заглавной
                capitalized_words.append(word[0].upper() + word[1:] if word else word)
        else:
            capitalized_words.append(word)
    
    return " ".join(capitalized_words)


def format_client_name(client_name, max_length=35):
    """
    Форматирует имя клиента для отображения в таблице.
    
    Args:
        client_name (str): Исходное имя клиента
        max_length (int): Максимальная длина строки
    
    Returns:
        str: Отформатированное имя
    """
    if not client_name:
        return "НЕ УКАЗАН"
    
    formatted = capitalize_name(client_name)
    
    # Обрезаем до максимальной длины
    if len(formatted) > max_length:
        formatted = formatted[:max_length - 3] + "..."
    
    return formatted


def format_manager_name(manager_name):
    """
    Форматирует имя менеджера (Имя Фамилия -> И. Фамилия).
    
    Args:
        manager_name (str): Полное имя менеджера
    
    Returns:
        str: Отформатированное имя
    """
    if not manager_name or manager_name == "Не назначен":
        return "Не назначен"
    
    name = capitalize_name(manager_name)
    parts = name.split()
    
    if len(parts) >= 2:
        # Формат: И. Фамилия
        return f"{parts[0][0]}. {parts[1]}"
    elif len(parts) == 1:
        return parts[0]
    else:
        return "Не назначен"


def format_organization_name(org_name):
    """
    Форматирует название организации (ООО, ИП и т.д.).
    
    Args:
        org_name (str): Название организации
    
    Returns:
        str: Отформатированное название
    """
    if not org_name:
        return "НЕ УКАЗАНО"
    
    # Специальные случаи для распространённых аббревиатур
    special_cases = {
        "ооо": "ООО",
        "ooo": "ООО",
        "ип": "ИП",
        "ip": "ИП",
        "оао": "ОАО",
        "zao": "ЗАО",
        "пао": "ПАО",
        "ao": "АО"
    }
    
    words = org_name.split()
    formatted_words = []
    
    for word in words:
        word_lower = word.lower()
        if word_lower in special_cases:
            formatted_words.append(special_cases[word_lower])
        elif word.isalpha() and len(word) <= 3:
            # Короткие слова из букв делаем заглавными (аббревиатуры)
            formatted_words.append(word.upper())
        else:
            # Обычные слова - с заглавной буквы
            formatted_words.append(word.capitalize())
    
    return " ".join(formatted_words)
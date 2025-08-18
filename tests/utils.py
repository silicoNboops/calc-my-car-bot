from __future__ import annotations


def normalize_age_key_for_api(age_key: str, is_jur: bool) -> str:
    """
    Приводит возрастной ключ к тем, что принимает API-сериализатор.

    - Для юрлиц 'over_5' недопустим: заменяем на '5_to_7'.
    - Для физлиц '5_to_7'/'over_7' нормализуются к 'over_5'.
    - Остальные значения возвращаются без изменений.
    """
    if is_jur and age_key == "over_5":
        return "5_to_7"
    if not is_jur and age_key in {"5_to_7", "over_7"}:
        return "over_5"
    return age_key

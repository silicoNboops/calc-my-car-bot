from __future__ import annotations


def normalize_age_key_for_api(age_key: str, is_jur: bool) -> str:
    """
    Приводит возрастной ключ к тем, что принимает API-сериализатор.

    - Легаси 'over_5' заменяем на '5_to_7'.
    - Остальные значения возвращаются без изменений.
    """
    if age_key == "over_5":
        return "5_to_7"
    return age_key

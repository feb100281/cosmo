from decimal import Decimal

def build_insights(obj) -> list[str]:
    """
    obj: MV_Daily_Sales instance
    Верни список буллетов (строк) для блока 'Выводы' на обложке/в конце.
    """
    insights = []

    if obj.amount is not None and obj.dt is not None and obj.cr is not None:
        # пример простых выводов
        if obj.cr and obj.dt:
            # rtr ratio есть в MV, но если хочешь пересчитать:
            pass

    # TODO: сюда добавишь свои правила
    return insights

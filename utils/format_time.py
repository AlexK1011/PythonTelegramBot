def format_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    parts = []
    if hours > 0:
        hours_word = "час"
        if 2 <= hours <= 4:
            hours_word = "часа"
        elif hours >= 5:
            hours_word = "часов"
        parts.append(f"{hours} {hours_word}")

    if minutes > 0:
        minutes_word = "минут"
        if minutes == 1:
            minutes_word = "минута"
        elif 2 <= minutes <= 4:
            minutes_word = "минуты"
        parts.append(f"{minutes} {minutes_word}")

    return " ".join(parts)

from django import template

register = template.Library()

@register.filter
def div(value, arg):
    try:
        return int(float(value) / float(arg))
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def thousands_separator(value):
    try:
        value = int(float(value))
        return "{:,}".format(value)
    except (ValueError, TypeError):
        return value

@register.filter
def to_persian_words(value):
    try:
        value = int(float(value))
    except (ValueError, TypeError):
        return "صفر"

    if value == 0:
        return "صفر"

    units = ["", "هزار", "میلیون", "میلیارد", "تریلیون"]
    digits = [
        "", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه",
        "ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"
    ]
    tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
    hundreds = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]

    def convert_three_digits(num):
        if num == 0:
            return ""
        result = []
        if num >= 100:
            result.append(hundreds[num // 100])
            num %= 100
        if num >= 20:
            if result and num > 0:
                result.append("و")
            result.append(tens[num // 10])
            num %= 10
        if num > 0:
            if result:
                result.append("و")
            result.append(digits[num])
        return " ".join(result)

    parts = []
    unit_index = 0
    while value > 0:
        three_digits = value % 1000
        if three_digits > 0:
            text = convert_three_digits(three_digits)
            if unit_index > 0:
                text += " " + units[unit_index]
            parts.append(text)
        value //= 1000
        unit_index += 1

    parts.reverse()
    result = " و ".join(parts)
    return result.strip()
"""Resolve common calendar periods; unfamiliar requests remain for the agent's date tools."""
import re
from datetime import timedelta


def resolve_period(message, today):
    text = message.lower().translate(str.maketrans('أإآى٠١٢٣٤٥٦٧٨٩', 'اااي0123456789'))
    if re.search(r'الربع (?:السنوي )?(?:هذا|الحالي)|هذا الربع|this quarter', text):
        return today.replace(month=((today.month-1)//3)*3+1, day=1), today
    if re.search(r'الشهر الماضي|last month', text):
        end = today.replace(day=1)-timedelta(days=1)
        return end.replace(day=1), end
    if re.search(r'هذا الشهر|الشهر الحالي|this month', text):
        return today.replace(day=1), today
    if re.search(r'الاسبوع الماضي|last week', text):
        # ISO calendar week (Monday–Sunday), stated in the model's context.
        end = today-timedelta(days=today.weekday()+1)
        return end-timedelta(days=6), end
    if re.search(r'اليومين|يومين|last two days|past two days', text):
        return today-timedelta(days=1), today
    match = re.search(r'(?:اخر|خلال|last|past)\s+(\d+)\s*(?:ايام|يوم|days?)', text)
    if match and 1 <= int(match[1]) <= 36500:
        return today-timedelta(days=int(match[1])-1), today
    if re.search(r'اخر\s+(?:اخبار\s+)?شهر|past month', text):
        return today-timedelta(days=29), today
    if re.search(r'اخر\s+(?:اخبار\s+)?اسبوع|past week', text):
        return today-timedelta(days=6), today
    if re.search(r'امس|yesterday', text):
        day = today-timedelta(days=1)
        return day, day
    if re.search(r'اليوم|today', text):
        return today, today
    return None

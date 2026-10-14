from datetime import date
import pytest
from eis_engine.news_period import resolve_period

@pytest.mark.parametrize('message,start,end', [
    ('وش أخبار اليومين الماضية','2026-10-13','2026-10-14'),
    ('آخر أخبار الأسبوع الماضي','2026-10-05','2026-10-11'),
    ('أخبار الشهر الماضي','2026-09-01','2026-09-30'),
    ('أخبار الربع السنوي هذا','2026-10-01','2026-10-14'),
    ('آخر ٩٠ يوم','2026-07-17','2026-10-14'),
    ('this month','2026-10-01','2026-10-14'),
])
def test_requested_period(message,start,end):
    assert resolve_period(message,date(2026,10,14)) == (date.fromisoformat(start),date.fromisoformat(end))

def test_previous_month_across_year_and_leap_boundary():
    assert resolve_period('last month',date(2026,1,2)) == (date(2025,12,1),date(2025,12,31))
    assert resolve_period('last month',date(2024,3,2)) == (date(2024,2,1),date(2024,2,29))

def test_unrecognized_dates_are_left_to_agent_not_default_week():
    assert resolve_period('أخبار أنثروبيك في 5 أغسطس',date(2026,10,14)) is None

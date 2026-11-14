"""Автоматично публикуване в социалните мрежи.

Засега са заготовки: те само записват какво биха публикували. За реално публикуване:
- Facebook/Instagram: Meta Graph API (страница + Instagram Business акаунт)
- Telegram: Bot API (sendMessage в канал), най-лесният за пускане
- X: API v2
- TikTok/Reels: изисква видео, отделна стъпка (генериране на кратко видео от статията)
Всяка мрежа има собствени правила за автоматизация и обозначаване на AI съдържание.
"""
import os

from .. import config


def post_text(art):
    url = f"{config.SITE_URL}/{art.category}/{art.slug}"
    return f"{art.title}\n\n{art.summary}\n\n{url}"


def publish_telegram(art):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHANNEL")
    if not (token and chat):
        return "skipped: no telegram credentials"
    import httpx

    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": post_text(art)},
        timeout=20,
    )
    return f"telegram: {r.status_code}"


def publish_facebook(art):
    return "skipped: facebook not configured (TODO: Meta Graph API)"


def publish_x(art):
    return "skipped: x not configured (TODO: X API v2)"


def publish_all(art):
    results = []
    for fn in (publish_telegram, publish_facebook, publish_x):
        try:
            results.append(fn(art))
        except Exception as exc:  # социалната мрежа не бива да чупи публикуването
            results.append(f"{fn.__name__}: error {exc}")
    print(f"[social] {art.slug}: {results}")
    return results

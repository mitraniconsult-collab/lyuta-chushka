"""Засичане на сигнали: какво е горещо.

Чужди сайтове се ползват само като СИГНАЛ (заглавие + линк). Текстът им не се копира
и не се подава за преразказване. Ботът пише собствен материал по факти от първоизточници.
"""
import feedparser
from sqlalchemy.orm import Session

from ..models import Signal

# Добавете свои емисии. Предпочитайте първоизточници: институции, регистри, съдилища.
FEEDS = [
    # ("Име на източника", "https://адрес/на/rss"),
]


def fetch_signals(db: Session, feeds=None, limit_per_feed=30):
    feeds = feeds if feeds is not None else FEEDS
    added = 0
    for name, url in feeds:
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:  # мрежови грешки не трябва да спират цикъла
            print(f"[ingest] {name}: {exc}")
            continue
        for entry in parsed.entries[:limit_per_feed]:
            link = getattr(entry, "link", "")
            title = getattr(entry, "title", "").strip()
            if not link or not title:
                continue
            if db.query(Signal).filter_by(url=link).first():
                continue
            db.add(
                Signal(
                    url=link,
                    title=title[:400],
                    feed=name,
                    published=getattr(entry, "published", "")[:60],
                )
            )
            added += 1
    db.commit()
    return added

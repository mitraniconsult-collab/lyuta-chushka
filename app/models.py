import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text)  # прост HTML: <p>, <h2>, <blockquote>
    category: Mapped[str] = mapped_column(String(40), index=True)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    image_credit: Mapped[str] = mapped_column(String(200), default="")

    # Източници: по един на ред във формат "Заглавие | https://адрес"
    sources: Mapped[str] = mapped_column(Text, default="")

    # Правен слой
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String(10), default="low")  # low | high
    risk_reasons: Mapped[str] = mapped_column(Text, default="")

    # draft | pending | published | rejected
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    @property
    def source_list(self):
        out = []
        for line in (self.sources or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                title, url = [p.strip() for p in line.split("|", 1)]
            else:
                title, url = line, line
            out.append({"title": title, "url": url})
        return out


class Signal(Base):
    """Сигнал от външен сайт или регистър: какво е горещо. Не се публикува, само вдъхновява."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(600), unique=True)
    title: Mapped[str] = mapped_column(String(400))
    feed: Mapped[str] = mapped_column(String(200), default="")
    published: Mapped[str] = mapped_column(String(60), default="")
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

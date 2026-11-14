"""Превръща чернова в статия: оценка на риска -> автоматично публикуване или опашка."""
from sqlalchemy.orm import Session

from .. import config
from ..models import Article, utcnow
from . import risk, social
from .slugify import slugify


def unique_slug(db: Session, title: str):
    base = slugify(title)
    slug, n = base, 2
    while db.query(Article).filter_by(slug=slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def submit_draft(db: Session, data: dict, sources: str, image_url="", image_credit="", is_demo=False):
    """data: title, summary, body, category (както ги връща generate_article)."""
    sources_count = len([l for l in (sources or "").splitlines() if l.strip()])
    result = risk.assess(data["title"], data["body"], sources_count)

    art = Article(
        slug=unique_slug(db, data["title"]),
        title=data["title"].strip(),
        summary=data.get("summary", "").strip(),
        body=data["body"],
        category=data.get("category", "obshtestvo"),
        image_url=image_url,
        image_credit=image_credit,
        sources=sources,
        ai_generated=True,
        human_reviewed=False,
        risk_level=result.level,
        risk_reasons=result.reasons_text,
        is_demo=is_demo,
    )

    if result.level == "low" and config.AUTO_PUBLISH_LOW_RISK:
        art.status = "published"
        art.published_at = utcnow()
    else:
        art.status = "pending"

    db.add(art)
    db.commit()

    if art.status == "published":
        social.publish_all(art)
    return art


def approve(db: Session, art: Article):
    """Редакторът е прегледал: махаме AI етикета за липса на преглед и поемаме отговорност."""
    art.status = "published"
    art.human_reviewed = True
    art.published_at = utcnow()
    db.commit()
    social.publish_all(art)
    return art


def reject(db: Session, art: Article):
    art.status = "rejected"
    db.commit()
    return art

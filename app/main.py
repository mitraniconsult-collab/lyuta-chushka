import datetime as dt
import secrets
from contextlib import asynccontextmanager

import nh3
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from xml.sax.saxutils import escape

from . import config
from .db import Base, engine, get_db
from .models import Article, Signal
from .pipeline import generate, publisher, risk

ALLOWED_TAGS = {"p", "h2", "h3", "blockquote", "strong", "em", "ul", "ol", "li", "br"}
MONTHS = ["", "януари", "февруари", "март", "април", "май", "юни", "юли", "август",
          "септември", "октомври", "ноември", "декември"]


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title=config.SITE_NAME, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def bg_date(value):
    if not value:
        return ""
    return f"{value.day} {MONTHS[value.month]} {value.year}, {value:%H:%M}"


def clean_html(value):
    return nh3.clean(value or "", tags=ALLOWED_TAGS)


templates.env.filters["bg_date"] = bg_date
templates.env.filters["clean_html"] = clean_html
templates.env.globals.update(
    config=config, CATEGORIES=config.CATEGORIES, now=lambda: dt.datetime.now(),
)


def render(request, name, **ctx):
    return templates.TemplateResponse(request, name, ctx)


def published(db: Session):
    return db.query(Article).filter(Article.status == "published")


# ---------------------------------------------------------------- публична част
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    items = published(db).order_by(desc(Article.published_at)).limit(30).all()
    hero = items[0] if items else None
    side = items[1:4]
    rest = items[4:]
    popular = published(db).order_by(desc(Article.views)).limit(5).all()
    return render(request, "home.html", hero=hero, side=side, rest=rest, popular=popular)


@app.get("/redakciya", response_class=HTMLResponse)
def about(request: Request):
    return render(request, "about.html")


@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {config.SITE_URL}/sitemap.xml\n"


@app.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    urls = [f"<url><loc>{config.SITE_URL}/</loc></url>"]
    for slug in config.CATEGORIES:
        urls.append(f"<url><loc>{config.SITE_URL}/{slug}</loc></url>")
    for a in published(db).order_by(desc(Article.published_at)).limit(1000):
        urls.append(
            f"<url><loc>{config.SITE_URL}/{a.category}/{a.slug}</loc>"
            f"<lastmod>{a.published_at:%Y-%m-%d}</lastmod></url>"
        )
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' \
          + "".join(urls) + "</urlset>"
    return Response(xml, media_type="application/xml")


@app.get("/rss.xml")
def rss(db: Session = Depends(get_db)):
    items = []
    for a in published(db).order_by(desc(Article.published_at)).limit(30):
        items.append(
            f"<item><title>{escape(a.title)}</title>"
            f"<link>{config.SITE_URL}/{a.category}/{a.slug}</link>"
            f"<guid>{config.SITE_URL}/{a.category}/{a.slug}</guid>"
            f"<description>{escape(a.summary)}</description>"
            f"<pubDate>{a.published_at:%a, %d %b %Y %H:%M:%S} +0000</pubDate></item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>{escape(config.SITE_NAME)}</title><link>{config.SITE_URL}</link>"
        f"<description>{escape(config.SITE_TAGLINE)}</description>" + "".join(items) + "</channel></rss>"
    )
    return Response(xml, media_type="application/rss+xml")


# ---------------------------------------------------------------------- админ
def is_admin(request: Request):
    return request.session.get("admin") is True


def require_admin(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "admin_login.html", error=None)


@app.post("/admin/login")
def login(request: Request, password: str = Form(...)):
    if secrets.compare_digest(password, config.ADMIN_PASSWORD):
        request.session["admin"] = True
        return RedirectResponse("/admin", status_code=303)
    return render(request, "admin_login.html", error="Грешна парола")


@app.post("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def admin_home(request: Request, db: Session = Depends(get_db)):
    pending = db.query(Article).filter_by(status="pending").order_by(desc(Article.created_at)).all()
    recent = (
        db.query(Article).filter(Article.status.in_(["published", "rejected"]))
        .order_by(desc(Article.created_at)).limit(20).all()
    )
    signals = db.query(Signal).filter_by(processed=False).order_by(desc(Signal.created_at)).limit(15).all()
    return render(request, "admin.html", pending=pending, recent=recent, signals=signals, msg=request.query_params.get("msg"))


@app.get("/admin/article/{art_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def admin_edit(art_id: int, request: Request, db: Session = Depends(get_db)):
    art = db.get(Article, art_id)
    if not art:
        raise HTTPException(404)
    return render(request, "admin_edit.html", a=art)


@app.post("/admin/article/{art_id}", dependencies=[Depends(require_admin)])
def admin_save(
    art_id: int,
    action: str = Form(...),
    title: str = Form(...),
    summary: str = Form(""),
    body: str = Form(...),
    category: str = Form(...),
    sources: str = Form(""),
    image_url: str = Form(""),
    image_credit: str = Form(""),
    db: Session = Depends(get_db),
):
    art = db.get(Article, art_id)
    if not art:
        raise HTTPException(404)
    art.title, art.summary, art.body = title.strip(), summary.strip(), body
    art.category = category if category in config.CATEGORIES else art.category
    art.sources, art.image_url, art.image_credit = sources, image_url.strip(), image_credit.strip()
    db.commit()
    if action == "approve":
        publisher.approve(db, art)
        return RedirectResponse("/admin?msg=Публикувано", status_code=303)
    if action == "reject":
        publisher.reject(db, art)
        return RedirectResponse("/admin?msg=Отхвърлено", status_code=303)
    return RedirectResponse(f"/admin/article/{art.id}", status_code=303)


@app.post("/admin/generate", dependencies=[Depends(require_admin)])
def admin_generate(
    facts: str = Form(...),
    sources: str = Form(""),
    category: str = Form("obshtestvo"),
    db: Session = Depends(get_db),
):
    try:
        data = generate.generate_article(facts, category)
    except generate.GenerationError as exc:
        return RedirectResponse(f"/admin?msg=Грешка: {exc}", status_code=303)
    art = publisher.submit_draft(db, data, sources)
    return RedirectResponse(f"/admin?msg=Създадена чернова ({art.status}, риск: {art.risk_level})", status_code=303)


@app.post("/admin/signal/{sig_id}/dismiss", dependencies=[Depends(require_admin)])
def dismiss_signal(sig_id: int, db: Session = Depends(get_db)):
    s = db.get(Signal, sig_id)
    if s:
        s.processed = True
        db.commit()
    return RedirectResponse("/admin", status_code=303)


# -------------------------------------------- категории и статии (след останалото)
@app.get("/{category}", response_class=HTMLResponse)
def category_page(category: str, request: Request, db: Session = Depends(get_db)):
    if category not in config.CATEGORIES:
        raise HTTPException(404)
    items = published(db).filter(Article.category == category).order_by(desc(Article.published_at)).limit(60).all()
    return render(request, "category.html", category=category, items=items)


@app.get("/{category}/{slug}", response_class=HTMLResponse)
def article_page(category: str, slug: str, request: Request, db: Session = Depends(get_db)):
    art = published(db).filter(Article.slug == slug, Article.category == category).first()
    if not art:
        raise HTTPException(404)
    art.views += 1
    db.commit()
    more = (
        published(db).filter(Article.id != art.id, Article.category == art.category)
        .order_by(desc(Article.published_at)).limit(3).all()
    )
    return render(request, "article.html", a=art, more=more)


@app.exception_handler(404)
def not_found(request: Request, exc):
    return templates.TemplateResponse(request, "404.html", {}, status_code=404)

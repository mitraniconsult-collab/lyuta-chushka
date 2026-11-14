import os

SITE_NAME = os.getenv("SITE_NAME", "Люта Чушка")
SITE_TAGLINE = os.getenv("SITE_TAGLINE", "Новините с подправка")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
EDITOR_NAME = os.getenv("EDITOR_NAME", "Име на отговорния редактор")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "redakciq@example.bg")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./site.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# Само статии с нисък риск и поне един източник се публикуват автоматично.
AUTO_PUBLISH_LOW_RISK = os.getenv("AUTO_PUBLISH_LOW_RISK", "true").lower() == "true"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

CATEGORIES = {
    "politika": "Политика",
    "klyuki": "Клюки",
    "obshtestvo": "Общество",
    "po-dokumenti": "По документи",
    "sport": "Спорт",
}

AI_LABEL = "Този материал е създаден с помощта на изкуствен интелект и не е прегледан от редактор."
REVIEWED_LABEL = "Материалът е изготвен с помощта на AI и е редактиран от екипа. Отговорност носи редакцията."

"""Филтър за правен риск.

Принцип: всичко, което може да засегне конкретен човек, отива за ръчно одобрение.
Останалото (при поне един източник) може да се публикува автоматично.
Правилата са умишлено груби: по-добре фалшива тревога, отколкото пропуснат иск.
Прегледайте ги с медиен адвокат и допълвайте списъците с времето.
"""
import re
from dataclasses import dataclass, field

# Корени на думи, свързани с обвинения и престъпления
ACCUSATION_STEMS = [
    "корупц", "подкуп", "рушвет", "измам", "присвоя", "кражб", "краде", "ограб",
    "арест", "обвин", "прокуратур", "разследв", "престъп", "мафи", "пране на пари",
    "изнуд", "шантаж", "заплах", "убийств", "изнасил", "насил", "наркот", "дрог",
    "укрива", "данъчна измама", "схем", "далавер", "източ", "лъже", "лъжа",
    "плагиат", "фалшив", "шпионин", "агент на",
]

# Теми с повишена чувствителност
SENSITIVE_STEMS = [
    "непълнолетн", "малолетн", "дете", "деца", "ученичк", "ученик",
    "диагноз", "болен", "болест", "рак ", "психиатр", "самоубий", "наркоман",
    "интимн", "секс", "любовница", "любовник", "изневяр", "развод", "бременн",
    "сексуал", "ориентация",
]

# Две последователни думи с главна буква: вероятно име на човек
NAME_PATTERN = re.compile(r"\b[А-Я][а-я]{2,}\s+[А-Я][а-я]{2,}\b")


@dataclass
class RiskResult:
    level: str = "low"  # low | high
    reasons: list = field(default_factory=list)

    @property
    def reasons_text(self):
        return "; ".join(self.reasons)


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "")


def assess(title, body, sources_count, extra_text=""):
    text = f"{title} {_strip_html(body)} {extra_text}"
    low = text.lower()
    reasons = []

    accusations = sorted({s for s in ACCUSATION_STEMS if s in low})
    sensitive = sorted({s for s in SENSITIVE_STEMS if s in low})
    names = sorted(set(NAME_PATTERN.findall(text)))

    if sources_count == 0:
        reasons.append("няма посочен източник")

    if accusations and names:
        reasons.append(
            "обвинителна лексика (" + ", ".join(accusations[:4]) + ") край имена ("
            + ", ".join(names[:3]) + ")"
        )

    if sensitive:
        reasons.append("чувствителна тема (" + ", ".join(sensitive[:4]) + ")")

    if len(_strip_html(body).split()) < 60:
        reasons.append("твърде кратък текст, възможно е да няма добавена стойност")

    level = "high" if reasons else "low"
    return RiskResult(level=level, reasons=reasons)

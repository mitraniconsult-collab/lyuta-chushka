"""Генериране на собствен текст през Claude API.

Ботът получава САМО факти (от регистър, документ или сигнал) и пише оригинален материал
с остър тон, без да приписва неподкрепени твърдения на конкретни хора.
"""
import json
import re

from .. import config

SYSTEM_PROMPT = """Ти си редактор на българска новинарска медия с остър, закачлив тон.
Пишеш на български, на собствен език, по предоставените факти.

Правила, които не се нарушават:
1. Използвай само фактите от входа. Нищо не измисляй: имена, цитати, суми, дати.
2. Не копирай и не преразказвай изречение по изречение чужд текст. Пиши нова структура.
3. Не приписвай престъпления, корупция, болести или личен живот на конкретен човек,
   освен ако е изрично документирано във входа. Тогава го формулирай като „според ...“.
4. Разграничавай факт от коментар. Мнението е означено като мнение.
5. Заглавието е ярко, но не лъже и не обещава повече от съдържанието.
6. Дължина: 150-300 думи. HTML само с <p>, <h2>, <blockquote>.

Върни САМО валиден JSON: {"title": "...", "summary": "...", "body": "<p>...</p>", "category": "politika|klyuki|obshtestvo|po-dokumenti|sport"}"""


class GenerationError(RuntimeError):
    pass


def generate_article(facts: str, hint_category: str = "obshtestvo"):
    """facts: свободен текст с фактите и линковете към източниците."""
    if not config.ANTHROPIC_API_KEY:
        raise GenerationError("Липсва ANTHROPIC_API_KEY")

    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Предложена категория: {hint_category}\n\nФакти:\n{facts}",
            }
        ],
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GenerationError(f"Невалиден JSON от модела: {exc}") from exc

    for key in ("title", "summary", "body"):
        if not data.get(key):
            raise GenerationError(f"Липсва поле {key}")
    if data.get("category") not in config.CATEGORIES:
        data["category"] = hint_category
    return data

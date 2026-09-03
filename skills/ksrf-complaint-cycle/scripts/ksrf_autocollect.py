#!/usr/bin/env python3
"""Собрать первичный CaseFile из материалов дела для скиллов КС РФ."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


TOOL_DIRS = [
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/opt/anaconda3/bin"),
    Path("/usr/bin"),
    Path("/bin"),
]
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
    r"\s+\d{4}\s*г(?:ода|\.)?)\b",
    re.IGNORECASE,
)
CASE_RE = re.compile(
    r"(?<!\w)(?:дел[аоуе]\s*)?(?:№|(?-i:N))\s*[А-ЯA-Z0-9Ёа-яa-z./-]{2,}(?:\s*/\s*\d{2,4})?",
    re.IGNORECASE,
)
LEGAL_REF_RE = re.compile(
    r"\b(?:(?:п\.|пункт(?:а|ом|е|у)?|ч\.|част(?:ь|и|ью|ей|е)|абз\.|абзац(?:а|ем|е)?|ст\.|стать(?:я|и|е|ю|ей|ёй))\s*"
    r"[\d.]+(?:\s*[-–]\s*[\d.]+)?\s*){1,4}",
    re.IGNORECASE,
)
NORMATIVE_INSTRUMENT_TAIL_RE = re.compile(
    r"^\s*(?P<instrument>"
    r"Конституци[ияи]\s+(?:РФ|Российской Федерации)"
    r"|(?:ГК|ГПК|АПК|КАС|УПК|КоАП|НК|ТК|УК|ЖК|ЗК|СК|БК|ЛК|УИК|ГрК|ВК|КТМ)\s+РФ"
    r"|(?:[А-ЯЁа-яё-]+\s+){1,5}кодекс(?:а|ом|у|е)?\s+(?:РФ|Российской Федерации)"
    r"|кодекс(?:а|ом|у|е)?(?:\s+[А-ЯЁа-яё-]+){1,5}\s+(?:РФ|Российской Федерации)"
    r"|(?:ФКЗ|[Фф]едеральн\w*\s+конституционн\w*\s+закон\w*)"
    r"(?:\s+от\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4})?"
    r"(?:\s*(?:№|N)\s*[0-9А-ЯA-ZЁа-яa-z./-]+)?"
    r"|[Фф]едеральн\w*\s+закон\w*"
    r"(?:\s+от\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4})?"
    r"(?:\s*(?:№|N)\s*[0-9А-ЯA-ZЁа-яa-z./-]+)?"
    r"|[Зз]акон\w*\s+(?:РФ|Российской Федерации)"
    r"(?:\s+от\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4})?"
    r"(?:\s*(?:№|N)\s*[0-9А-ЯA-ZЁа-яa-z./-]+)?"
    r")",
    re.IGNORECASE,
)
CONSTITUTION_RE = re.compile(r"(?:ст\.|стать(?:я|и|е|ю|ей|ёй))\s*\d+(?:\.\d+)?\s+Конституци[ияи]\s+(?:РФ|Российской Федерации)", re.IGNORECASE)
CONSTITUTION_LIST_RE = re.compile(
    r"Конституци[ияи]\s+Российской\s+Федерации,?\s*(?:е[её]\s+)?"
    r"стать[ьяеиюм]+\s+([0-9,\s().частией-]{1,120})",
    re.IGNORECASE,
)
KSRF_RE = re.compile(
    r"(?:Постановлени[ея]|Определени[ея])\s+Конституционного\s+Суда\s+(?:РФ|Российской Федерации)"
    r".{0,80}?(?:N|№)\s*[\d-]+-?[ПО]?",
    re.IGNORECASE | re.DOTALL,
)
COURT_RE = re.compile(
    r"\b(?:Конституционный Суд РФ|Конституционный Суд Российской Федерации|Верховный Суд РФ|Верховный Суд Российской Федерации|"
    r"[А-ЯЁ][А-Яа-яЁё -]{2,80}?(?:районный|городской|областной|краевой|республиканский|арбитражный|кассационный|апелляционный)\s+суд[А-Яа-яЁё -]*)\b"
)
STAGE_WORDS = {
    "первая инстанция": re.compile(r"перв\w+\s+инстанц", re.IGNORECASE),
    "апелляция": re.compile(r"апелляц", re.IGNORECASE),
    "кассация": re.compile(r"кассац", re.IGNORECASE),
    "верховный суд": re.compile(r"Верховн\w+\s+Суд", re.IGNORECASE),
    "надзор": re.compile(r"надзор", re.IGNORECASE),
    "конституционный суд": re.compile(r"Конституционн\w+\s+Суд", re.IGNORECASE),
}
APPLIED_WORDS_RE = re.compile(
    r"примен\w+|руководств\w+|истолков\w+|толкован\w+|отказ\w+|не\s+предусмотр\w+|"
    r"не\s+допуска\w+|исключа\w+|запреща\w+|обязыва\w+|позволя\w+",
    re.IGNORECASE,
)
TEST_PATTERNS = {
    "proportionality": {
        "pattern": re.compile(r"соразмер|пропорцион|необходим\w+|чрезмерн|санкц|ограничени", re.IGNORECASE),
        "missing": ["цель ограничения", "менее обременительные альтернативы", "тяжесть последствий", "индивидуальная оценка"],
    },
    "balance": {
        "pattern": re.compile(r"баланс|сбалансирован|конкурирующ|интересы других лиц|слабая сторона", re.IGNORECASE),
        "missing": ["конкурирующие интересы", "распределение бремени", "процедурные гарантии"],
    },
    "equality": {
        "pattern": re.compile(r"равенств|дискримин|одинаков|различи[ея]|категори[ия]", re.IGNORECASE),
        "missing": ["сравнимая категория", "различие в правах", "цель различия", "объективное оправдание"],
    },
    "legal_certainty": {
        "pattern": re.compile(r"неопредел|неясн|недвусмыслен|произвол|единообраз|противоречив|судебн\w+\s+хаос", re.IGNORECASE),
        "missing": ["текстовая неясность", "расходящаяся практика", "почему разъяснения не устраняют дефект"],
    },
    "retroactivity": {
        "pattern": re.compile(r"обратн\w+\s+сил|ретроактив|прошл\w+\s+период|ухудша\w+\s+положени", re.IGNORECASE),
        "missing": ["дата юридического факта", "дата изменения закона", "ухудшение положения", "переходные правила"],
    },
    "legitimate_expectations": {
        "pattern": re.compile(r"правомерн\w+\s+ожидан|доверие|приобрет[её]нн\w+\s+прав|адаптац|компенсац", re.IGNORECASE),
        "missing": ["прежнее регулирование", "факты доверия", "переходный период", "компенсация"],
    },
    "gap_or_procedural_omission": {
        "pattern": re.compile(r"пробел|не\s+предусмотр|отсутств\w+\s+(?:механизм|процедур|порядок)|не\s+позволя", re.IGNORECASE),
        "missing": ["какой механизм отсутствует", "почему право без него нереализуемо", "соседнее регулирование"],
    },
    "effective_remedy": {
        "pattern": re.compile(r"эффективн\w+\s+средств|судебн\w+\s+защит|обжалован|приостанов", re.IGNORECASE),
        "missing": ["какое средство требуется", "почему существующее средство неэффективно", "необратимые последствия"],
    },
    "notification_and_right_to_be_heard": {
        "pattern": re.compile(r"уведом|известить|ознаком|выразить\s+мнен|быть\s+услышан|позици[яю]", re.IGNORECASE),
        "missing": ["кто должен уведомить", "срок для позиции", "последствие отсутствия уведомления"],
    },
}
EVENT_PATTERNS = [
    ("filing", re.compile(r"(?:подал[аи]?|подан[аоы]?|направил[аи]?|направлен[аоы]?|поступил[аи]?).{0,90}(?:жалоб|заявлени|ходатайств|представлени)|(?:жалоб|заявлени|ходатайств).{0,90}(?:подал[аи]?|подан[аоы]?|направил[аи]?|направлен[аоы]?|поступил[аи]?)", re.IGNORECASE | re.DOTALL)),
    ("court_decision", re.compile(r"(?:суд|судья|коллеги|президиум).{0,100}(?:решил|определил|постановил|отказал|отказано|удовлетворил|удовлетворено|оставил|оставлено|взыскал|взыскано)|(?:решени[ея]|решением|определени[ея]|определением|постановлени[ея]|постановлением|приговор).{0,100}(?:вынесен|принят|изготовлен|отказано|удовлетворено|оставлено|взыскано)", re.IGNORECASE | re.DOTALL)),
    ("hearing", re.compile(r"(?:судебн\w+\s+заседани|рассмотрени[ея]\s+дела|слушани[ея]\s+дела)", re.IGNORECASE)),
    ("entry_into_force", re.compile(r"вступил[оа]?\s+в\s+законн\w+\s+сил", re.IGNORECASE)),
    ("service_or_receipt", re.compile(r"(?:получил[аи]?|вручен[ао]?|направлен[ао]?).{0,70}(?:копи|уведомлени|решени|определени)|(?:копи|уведомлени).{0,70}(?:получил[аи]?|вручен[ао]?)", re.IGNORECASE | re.DOTALL)),
    ("enforcement", re.compile(r"(?:исполнительн\w+\s+производств|исполнительн\w+\s+лист|пристав|исполнени[ея]\s+(?:решени|судебн))", re.IGNORECASE)),
]
ACT_TITLE_DATE_PREFIX_RE = re.compile(
    r"(?:апелляционн\w+\s+|кассационн\w+\s+)?"
    r"(?:решени(?:е|я|ем)|определени(?:е|я|ем)|постановлени(?:е|я|ем)|приговор)"
    r"\s*(?:суда\s*)?(?:от\s*)?$",
    re.IGNORECASE,
)
RIGHT_HARM_PATTERNS = [
    {
        "code": "effective_judicial_protection",
        "right": "право на государственную и судебную защиту",
        "constitutional_articles": ["статья 45 Конституции РФ", "статья 46 Конституции РФ"],
        "pattern": re.compile(r"неисполн\w+.{0,100}(?:решени|судебн)|(?:отказ|невозможн|лишен).{0,100}(?:судебн\w+\s+защит|обжалован|исполнени)|эффективн\w+\s+(?:судебн\w+\s+защит|средств)|судебн\w+\s+защит\w+.{0,50}неэффектив", re.IGNORECASE | re.DOTALL),
        "consequence": "судебная защита или исполнение судебного акта могут оказаться недоступными либо неэффективными",
    },
    {
        "code": "equality",
        "right": "равенство и запрет необоснованной дифференциации",
        "constitutional_articles": ["статья 19 Конституции РФ"],
        "pattern": re.compile(r"равенств|дискримин|неравн|различи[ея].{0,90}(?:прав|положени|гаранти)|одинаков\w+.{0,70}(?:ситуац|положени)", re.IGNORECASE | re.DOTALL),
        "consequence": "сопоставимые лица могут получать различный объём прав или гарантий без достаточного основания",
    },
    {
        "code": "dignity",
        "right": "достоинство личности",
        "constitutional_articles": ["статья 21 Конституции РФ"],
        "pattern": re.compile(r"достоинств|унижающ|бесчеловечн|объективац", re.IGNORECASE),
        "consequence": "лицо может быть поставлено в положение, несовместимое с уважением достоинства",
    },
    {
        "code": "property",
        "right": "право собственности",
        "constitutional_articles": ["статья 35 Конституции РФ"],
        "pattern": re.compile(r"лишени[ея]\s+(?:имуществ|собственност)|изъят|взыскани[ея].{0,80}(?:имуществ|денежн)|право\s+собственност", re.IGNORECASE | re.DOTALL),
        "consequence": "имущество может быть изъято, обременено или утрачено вследствие спорного нормативного механизма",
    },
    {
        "code": "housing",
        "right": "право на жилище",
        "constitutional_articles": ["статья 40 Конституции РФ"],
        "pattern": re.compile(r"единственн\w+\s+жиль|выселен|лишени[ея]\s+жилищ|право\s+на\s+жилищ|жилое\s+помещени", re.IGNORECASE),
        "consequence": "лицо может утратить жилище или возможность пользоваться им",
    },
    {
        "code": "labor",
        "right": "право на труд и связанные с ним гарантии",
        "constitutional_articles": ["статья 37 Конституции РФ"],
        "pattern": re.compile(r"трудов\w+\s+(?:прав|отношени|договор|спор)|работник|работодател|увольнен|заработн\w+\s+плат", re.IGNORECASE),
        "consequence": "трудовая гарантия может остаться нереализованной либо получить меньшую защиту",
    },
    {
        "code": "privacy_and_personal_data",
        "right": "неприкосновенность частной жизни и защита персональной информации",
        "constitutional_articles": ["статья 23 Конституции РФ", "статья 24 Конституции РФ"],
        "pattern": re.compile(r"частн\w+\s+жизн|персональн\w+\s+данн|тайн\w+\s+(?:переписк|сообщени)|конфиденциальн", re.IGNORECASE),
        "consequence": "сведения о частной жизни или персональные данные могут стать доступными либо использоваться без достаточной гарантии",
    },
    {
        "code": "freedom_of_expression",
        "right": "свобода мысли и слова",
        "constitutional_articles": ["статья 29 Конституции РФ"],
        "pattern": re.compile(r"свобод\w+\s+(?:слов|выражени)|распространени[ея]\s+информац|критик\w+\s+(?:власт|должност)|цензур", re.IGNORECASE),
        "consequence": "сообщение информации или критика могут повлечь запрет либо ответственность",
    },
    {
        "code": "petition",
        "right": "право на обращение в государственные органы",
        "constitutional_articles": ["статья 33 Конституции РФ"],
        "pattern": re.compile(r"обращени[ея]\s+(?:граждан|в\s+(?:орган|администрац))|ответ\w+\s+на\s+обращени|59-ФЗ", re.IGNORECASE),
        "consequence": "адресное обращение может не получить предусмотренного законом рассмотрения или повлечь неблагоприятный эффект",
    },
    {
        "code": "social_security",
        "right": "право на социальное обеспечение",
        "constitutional_articles": ["статья 39 Конституции РФ"],
        "pattern": re.compile(r"пенси|пособи|социальн\w+\s+(?:обеспечени|выплат|поддержк)|инвалидност", re.IGNORECASE),
        "consequence": "социальная выплата или гарантия может быть недоступна либо уменьшена",
    },
    {
        "code": "health_protection",
        "right": "право на охрану здоровья и медицинскую помощь",
        "constitutional_articles": ["статья 41 Конституции РФ"],
        "pattern": re.compile(r"охран\w+\s+здоров|медицинск\w+\s+помощ|лечени|заболевани", re.IGNORECASE),
        "consequence": "медицинская помощь или иная гарантия охраны здоровья может оказаться недоступной",
    },
]
RIGHT_HARM_ADVERSE_PATTERNS = {
    "effective_judicial_protection": re.compile(
        r"не\s*исполн|отказ.{0,80}(?:защит|обжал|исполн)|невозмож.{0,80}(?:защит|обжал|исполн)|"
        r"неэффектив.{0,80}(?:защит|средств|исполн)|(?:защит|средств|исполн).{0,80}неэффектив|"
        r"лишен.{0,80}(?:защит|обжал)|недоступ.{0,80}(?:суд|защит|обжал)",
        re.IGNORECASE | re.DOTALL,
    ),
    "equality": re.compile(
        r"дискримин|неравн|необоснован.{0,60}(?:различ|дифференц)|(?:различ|дифференц).{0,60}(?:меньш|хуже|лишен|исключ)",
        re.IGNORECASE | re.DOTALL,
    ),
    "dignity": re.compile(r"унижающ|бесчеловеч|объективац|умален.{0,40}достоинств", re.IGNORECASE | re.DOTALL),
    "property": re.compile(
        r"лишен.{0,60}(?:имуществ|собствен)|изъят|взыскан.{0,60}(?:имуществ|денежн)|"
        r"утрат.{0,60}(?:имуществ|собствен)|обремен.{0,60}(?:имуществ|собствен)",
        re.IGNORECASE | re.DOTALL,
    ),
    "housing": re.compile(
        r"выселен|лишен.{0,50}жилищ|утрат.{0,50}(?:жиль|жилое)|обращен.{0,80}взыскан.{0,80}(?:жиль|жилое)",
        re.IGNORECASE | re.DOTALL,
    ),
    "labor": re.compile(
        r"увольнен|невыплат|задержк.{0,50}(?:зарплат|заработ)|отказ.{0,60}(?:работ|труд)|"
        r"не\s*исполн.{0,60}(?:труд|работодател)|наруш.{0,60}труд|(?:трудов|работник|гарант).{0,60}(?:лишен|меньш.{0,20}гарант|нереализ)",
        re.IGNORECASE | re.DOTALL,
    ),
    "privacy_and_personal_data": re.compile(
        r"разглаш|распростран.{0,60}(?:персональн|частн|тайн)|доступ.{0,60}(?:неопредел|посторон)|"
        r"без\s+(?:соглас|разрешен).{0,60}(?:данн|сведен)|наруш.{0,60}(?:частн|конфиденц|тайн)",
        re.IGNORECASE | re.DOTALL,
    ),
    "freedom_of_expression": re.compile(
        r"запрет.{0,60}(?:слов|выраж|информац|публи)|ответствен.{0,60}(?:слов|выраж|информац|публи|критик)|"
        r"санкц.{0,60}(?:слов|выраж|информац|публи|критик)|преслед.{0,60}(?:слов|критик|публи)|"
        r"блокир|удален.{0,60}(?:публикац|информац|сообщен)",
        re.IGNORECASE | re.DOTALL,
    ),
    "petition": re.compile(
        r"не\s+рассмотр.{0,60}обращ|не\s+ответ.{0,60}обращ|отказ.{0,60}(?:приня|рассмотр).{0,60}обращ|"
        r"обращ.{0,60}(?:не\s+рассмотр|без\s+ответ|ответ\s+не\s+дан)|"
        r"ответствен.{0,60}(?:за|из-за).{0,40}обращ|разглаш.{0,60}обращ",
        re.IGNORECASE | re.DOTALL,
    ),
    "social_security": re.compile(
        r"отказ.{0,60}(?:пенси|пособ|выплат)|лишен.{0,60}(?:пенси|пособ|выплат)|"
        r"уменьш.{0,60}(?:пенси|пособ|выплат)|не\s+назнач.{0,60}(?:пенси|пособ|выплат)",
        re.IGNORECASE | re.DOTALL,
    ),
    "health_protection": re.compile(
        r"отказ.{0,60}(?:медицин|лечен)|неоказ.{0,60}(?:помощ|лечен)|недоступ.{0,60}(?:помощ|лечен)|"
        r"вред.{0,60}здоров|ухудш.{0,60}здоров",
        re.IGNORECASE | re.DOTALL,
    ),
}
ATTACHMENT_PATTERNS = {
    "судебный акт": re.compile(r"решени[ея]|определени[ея]|постановлени[ея]|приговор", re.IGNORECASE),
    "жалоба или ходатайство": re.compile(r"жалоб|ходатайств|заявлени", re.IGNORECASE),
    "доверенность": re.compile(r"доверенн", re.IGNORECASE),
    "госпошлина": re.compile(r"госпошлин|пошлин|квитанц|плат[её]ж", re.IGNORECASE),
    "паспорт": re.compile(r"паспорт", re.IGNORECASE),
    "перевод": re.compile(r"перевод", re.IGNORECASE),
    "экспертные материалы": re.compile(r"эксперт|заключени", re.IGNORECASE),
    "нормативный акт": re.compile(r"закон|кодекс|фкз|норматив", re.IGNORECASE),
}
DOCUMENT_TYPE_PATTERNS = [
    ("case_study_or_benchmark", re.compile(r"(?:input[- ]?only|held[- ]?out\s+outcome|ретроспективн\w+.{0,100}benchmark|research\s+replay|input/outcome\s+benchmark)", re.IGNORECASE | re.DOTALL)),
    ("formal_ksrf_guide", re.compile(r"(?:как\s+избежать\s+ошибок\s+при\s+обращении\s+в\s+КС|схема\s+прохождения\s+жалоб[ыи]\s+в\s+КС|типичн\w+\s+ошибк\w+\s+.*КС|примерн\w+\s+структур\w+\s+жалоб)", re.IGNORECASE | re.DOTALL)),
    ("legal_writing_methodology", re.compile(r"(?:Основы\s+письма\s+для\s+юристов|юридическ\w+\s+письм|legal\s+writing|legal\s+drafting|структур[аы]\s+текста)", re.IGNORECASE | re.DOTALL)),
    ("research_report", re.compile(r"(?:Исполнительное\s+резюме|deliverable|deep\s+research|автоматизаци[яи].{0,80}(?:жалоб|КС|практик)|таксономи[яи].{0,80}автоматизац)", re.IGNORECASE | re.DOTALL)),
    ("service_or_tool_spec", re.compile(r"(?:ТЗ|техническ\w+\s+задан|сервис[ыа]?|архитектур\w+\s+сервис|MVP|roadmap|product|pipeline).{0,160}(?:жалоб|КС|практик|автоматизац|бот|канал)", re.IGNORECASE | re.DOTALL)),
    ("echr_or_un_material", re.compile(r"(?:ЕСПЧ|Европейск\w+\s+Суд|Конвенци[яи]|Article\s+\d+|CASE\s+OF|United\s+Nations|ООН|Организаци[яи]\s+Объедин[её]нных\s+Наций|Комитет\s+по\s+правам\s+человека|Комитет\s+ООН|Международн\w+\s+пакт|правозащитн\w+\s+механизм)", re.IGNORECASE | re.DOTALL)),
    ("practice_retrieval_skill_material", re.compile(r"(?:Тезис:|PRO-формула|CONTRA-формула|подтверждающ\w+\s+практик|опровергающ\w+\s+практик|встречн\w+\s+поиск)", re.IGNORECASE | re.DOTALL)),
    ("telegram_or_channel_research", re.compile(r"(?:Telegram|https://t\.me|t\.me/|permalink|пермалинк|скрейпинг)", re.IGNORECASE | re.DOTALL)),
    ("post_decision_review_motion", re.compile(r"пересмотр.*(?:дела|решени|судебн)", re.IGNORECASE | re.DOTALL)),
    ("request_supplement", re.compile(r"дополнени[ея].{0,180}(?:запрос|Конституционн\w+\s+Суд)", re.IGNORECASE | re.DOTALL)),
    ("court_request_motion", re.compile(r"ходатайств.*(?:запрос|Конституционн\w+\s+Суд)", re.IGNORECASE | re.DOTALL)),
    ("deputy_or_authorized_body_request", re.compile(r"(?:запрос.{0,1200}(?:депутат|Государственн\w+\s+Дум|Совет\w+\s+Федераци|Президент|Правительств|законодательн\w+\s+орган)|(?:депутат|Государственн\w+\s+Дум|Совет\w+\s+Федераци|Президент|Правительств).{0,1200}запрос|ч\.\s*2\s+ст\.\s*125.{0,1200}запрос)", re.IGNORECASE | re.DOTALL)),
    ("court_request_by_court", re.compile(r"(?:запросом|запрос)\s+.*Конституционн\w+\s+Суд|Запрос_ВС", re.IGNORECASE | re.DOTALL)),
    ("institutional_position_or_amicus", re.compile(r"(?:позици[яи]|мнение|заключени[ея]).{0,160}(?:ТПП|торгово-промышленн|международн\w+\s+коммерческ|amicus|инициативн\w+\s+научн)", re.IGNORECASE | re.DOTALL)),
    ("amicus_or_expert_conclusion", re.compile(r"amicus|заключени[ея].{0,120}(?:Конституционн\w+\s+Суд|стандарт|сравнительн)", re.IGNORECASE | re.DOTALL)),
    ("ksrf_complaint", re.compile(r"(?:жалоб[аы].{0,240}(?:Конституционн\w+\s+Суд|конституционн\w+\s+прав)|(?:^|\n)\s*(?:В\s+)?Конституционн\w+\s+Суд\s+(?:РФ|Российской Федерации)|(?:^|\n)\s*ЖАЛОБА\b.{0,600}(?:нарушени|Конституционн|стать[ьи]))", re.IGNORECASE | re.DOTALL)),
    ("science_or_methodology", re.compile(r"(?:теория\s+и\s+практика|конституционн\w+\s+правосуди|право\s+быть\s+услышанным|автор\s+использует\s+эмпирическ|научн\w+\s+заключени)", re.IGNORECASE | re.DOTALL)),
    ("judicial_act", re.compile(
        r"(?:^|\n)\s*(?:апелляционн\w+\s+|кассационн\w+\s+)?"
        r"(?:РЕШЕНИЕ|ОПРЕДЕЛЕНИЕ|ПОСТАНОВЛЕНИЕ|ПРИГОВОР)\s*(?:суда\s*)?"
        r"(?:от\s*)?(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}|\n.{0,900}(?:ИМЕНЕМ\s+РОССИЙСКОЙ\s+ФЕДЕРАЦИИ|дело\s*(?:№|N)|суд.{0,120}в\s+составе|УСТАНОВИЛ|ОПРЕДЕЛИЛ|ПОСТАНОВИЛ))",
        re.IGNORECASE | re.DOTALL,
    )),
    ("power_of_attorney", re.compile(r"доверенн", re.IGNORECASE)),
    ("state_fee_or_payment", re.compile(r"госпошлин|пошлин|квитанц|плат[её]ж", re.IGNORECASE)),
    ("translation", re.compile(r"перевод|translated|translation", re.IGNORECASE)),
    ("normative_act_excerpt", re.compile(r"выдержк[аи].{0,80}(?:нпа|закона|кодекса)|текст\s+обжалуем", re.IGNORECASE | re.DOTALL)),
]
FILENAME_TYPE_PATTERNS = [
    ("telegram_or_channel_research", re.compile(r"(deep-research-report_тг|тг[ _-]*канал|telegram)", re.IGNORECASE)),
    ("formal_ksrf_guide", re.compile(r"(как\s+избежать\s+ошибок|ошибок\s+при\s+обращении|примерная_структура|образец_страница|образец_жалобы)", re.IGNORECASE)),
    ("legal_writing_methodology", re.compile(r"(по\s+письму|osnovy.*pisma|legal[_ -]?writing)", re.IGNORECASE)),
    ("research_report", re.compile(r"(deep-research-report)", re.IGNORECASE)),
    ("practice_retrieval_skill_material", re.compile(r"(судебная_практика|praktika|tezis|тезис)", re.IGNORECASE)),
    ("service_or_tool_spec", re.compile(r"(^тз|/тз|сервисы|services|service)", re.IGNORECASE)),
    ("echr_or_un_material", re.compile(r"(case_of|echr|eспч|espch|оон|oon|un|pravozashchit|burkov|против_россии|protection_internationale)", re.IGNORECASE)),
    ("science_or_methodology", re.compile(r"(kryazhkova|muranov|pravovaja-sila|zhkp|жкп|sko-)", re.IGNORECASE)),
    ("institutional_position_or_amicus", re.compile(r"(pozic|pozits|mchp|tpp|amicus)", re.IGNORECASE)),
    ("request_supplement", re.compile(r"(dopolnenie|pervoe-dopolnenie|vtoroe-dopolnenie|дополнени).*(zapros|vto|кс|ks)", re.IGNORECASE)),
    ("deputy_or_authorized_body_request", re.compile(r"(zapros|запрос).*(deputat|gosdum|fsb|vto|vas|госдум|депутат|фсб|вас)", re.IGNORECASE)),
    ("ksrf_complaint", re.compile(r"(zhaloba|zhalob|жалоб)", re.IGNORECASE)),
]
PRAYER_RE = re.compile(r"\b(?:ПРОШУ|ПРОСИМ|просим|просит|прошу суд|Требование,\s+обращ)", re.IGNORECASE)
APPLICANT_RE = re.compile(r"(?:Заявител[ьиь]|Административн\w+\s+истец|Истец)\s*:?\s*([^\n]{3,180})", re.IGNORECASE)
ADDRESSEE_RE = re.compile(r"(Конституционный\s+Суд\s+Российской\s+Федерации|Конституционный\s+Суд\s+РФ|[А-ЯЁ][^\n]{3,120}суд[^\n]{0,80})")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def which_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for directory in TOOL_DIRS:
        candidate = directory / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def extract_pdf(path: Path) -> str:
    pdftotext = which_tool("pdftotext")
    if not pdftotext:
        return ""
    proc = subprocess.run(
        [pdftotext, "-layout", str(path), "-"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return repair_cyrillic_mojibake(proc.stdout.decode("utf-8", "replace"))


def text_quality_signals(text: str) -> dict[str, Any]:
    sample = text[:12000]
    letters = [ch for ch in sample if ch.isalpha()]
    cyrillic = [ch for ch in letters if "а" <= ch.lower() <= "я" or ch.lower() == "ё"]
    cyrillic_ratio = len(cyrillic) / len(letters) if letters else 0.0
    mojibake_hits = len(re.findall(r"\b(?:KOH|KONCT|CYA|CYD|Tocy|HCT|YIM|Npeg|BTO|VTO)\w*", sample, re.IGNORECASE))
    return {
        "letters": len(letters),
        "cyrillic_ratio": round(cyrillic_ratio, 3),
        "mojibake_hits": mojibake_hits,
    }


def repair_cyrillic_mojibake(text: str) -> str:
    signals = text_quality_signals(text)
    latin1_cyrillic_noise = len(re.findall(r"[À-ÿ]{4,}", text))
    if signals["cyrillic_ratio"] > 0.15 or latin1_cyrillic_noise < 10:
        return text
    try:
        repaired = text.encode("latin1", "ignore").decode("cp1251", "ignore")
    except UnicodeError:
        return text
    repaired_signals = text_quality_signals(repaired)
    if repaired_signals["cyrillic_ratio"] > max(0.5, signals["cyrillic_ratio"] + 0.4):
        return repaired
    return text


def expects_cyrillic(path: Path) -> bool:
    name = path.name.lower()
    if any("а" <= ch <= "я" or ch == "ё" for ch in name):
        return True
    return bool(re.search(r"(zhalob|zapros|dopolnenie|ksrf|ks_|_ks|tilda|pravo|zakon|sud|rossii|russia.*translation)", name))


def should_try_ocr(text: str, path: Path) -> bool:
    if len(text.strip()) < 500:
        return True
    if path.suffix.lower() != ".pdf":
        return False
    signals = text_quality_signals(text)
    name = path.name.lower()
    russian_legal_name = expects_cyrillic(path)
    return russian_legal_name and signals["letters"] > 200 and (
        signals["cyrillic_ratio"] < 0.35 or signals["mojibake_hits"] >= 3
    )


def text_score(text: str) -> float:
    signals = text_quality_signals(text)
    return len(text.strip()) * (0.25 + signals["cyrillic_ratio"]) - signals["mojibake_hits"] * 200


def tesseract_language_args(tesseract: str, tessdata_dir: str | None) -> tuple[list[str], list[str]]:
    list_cmd = [tesseract, "--list-langs"]
    if tessdata_dir:
        list_cmd.extend(["--tessdata-dir", tessdata_dir])
    proc = subprocess.run(list_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    langs = set(proc.stdout.decode("utf-8", "replace").splitlines())
    flags: list[str] = []
    if "rus" in langs and "eng" in langs:
        lang = "rus+eng"
    elif "rus" in langs:
        lang = "rus"
    elif "eng" in langs:
        lang = "eng"
        flags.append("tesseract_rus_unavailable")
    else:
        lang = "eng"
        flags.append("tesseract_language_unavailable")
    args: list[str] = []
    if tessdata_dir:
        args.extend(["--tessdata-dir", tessdata_dir])
    args.extend(["-l", lang])
    flags.append(f"tesseract_lang_{lang}")
    return args, flags


def extract_pdf_ocr(path: Path, max_pages: int, tessdata_dir: str | None = None) -> tuple[str, list[str]]:
    pdftoppm = which_tool("pdftoppm")
    tesseract = which_tool("tesseract")
    if not pdftoppm or not tesseract:
        return "", ["ocr_unavailable"]
    lang_args, lang_flags = tesseract_language_args(tesseract, tessdata_dir)
    with tempfile.TemporaryDirectory(prefix="ksrf_ocr_") as tmp:
        prefix = str(Path(tmp) / "page")
        proc = subprocess.run(
            [pdftoppm, "-r", "200", "-f", "1", "-l", str(max_pages), "-png", str(path), prefix],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            return "", ["ocr_render_failed"]
        parts: list[str] = []
        for image in sorted(Path(tmp).glob("page-*.png")):
            ocr = subprocess.run(
                [tesseract, str(image), "stdout", *lang_args, "--psm", "6"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if ocr.stdout:
                parts.append(ocr.stdout.decode("utf-8", "replace"))
        return "\n".join(parts), ["ocr_attempted", *lang_flags]


def extract_docx(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if name.startswith("word/") and name.endswith(".xml"):
                try:
                    root = ElementTree.fromstring(zf.read(name))
                except ElementTree.ParseError:
                    continue
                for node in root.iter():
                    if node.text:
                        parts.append(node.text)
    return "\n".join(parts)


def extract_legacy_doc(path: Path) -> tuple[str, str]:
    textutil = which_tool("textutil")
    if textutil:
        proc = subprocess.run(
            [textutil, "-convert", "txt", "-stdout", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        text = proc.stdout.decode("utf-8", "replace")
        if len(text.strip()) > 500:
            return text, "textutil"
    proc = subprocess.run(["strings", str(path)], check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return proc.stdout.decode("utf-8", "replace"), "strings"


def extract_image_ocr(path: Path, tessdata_dir: str | None = None) -> tuple[str, dict[str, Any]]:
    tesseract = which_tool("tesseract")
    details: dict[str, Any] = {"method": "image_ocr", "fallbacks": [], "ocr_pages": 1}
    if not tesseract:
        details["fallbacks"].append("ocr_unavailable")
        return "", details
    lang_args, lang_flags = tesseract_language_args(tesseract, tessdata_dir)
    details["fallbacks"].extend(["ocr_attempted", *lang_flags])
    proc = subprocess.run(
        [tesseract, str(path), "stdout", *lang_args, "--psm", "6"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return proc.stdout.decode("utf-8", "replace"), details


def extract_text(path: Path, enable_ocr: bool = True, ocr_pages: int = 8, tessdata_dir: str | None = None) -> tuple[str, dict[str, Any]]:
    suffix = path.suffix.lower()
    details: dict[str, Any] = {"method": "none", "fallbacks": [], "ocr_pages": 0}
    if suffix == ".pdf":
        text = extract_pdf(path)
        details["method"] = "pdftotext"
        if enable_ocr and should_try_ocr(text, path):
            if len(text.strip()) >= 500:
                details["fallbacks"].append("pdftotext_low_cyrillic_or_mojibake")
            ocr_text, flags = extract_pdf_ocr(path, ocr_pages, tessdata_dir=tessdata_dir)
            details["fallbacks"].extend(flags)
            details["ocr_pages"] = ocr_pages if ocr_text else 0
            if text_score(ocr_text) > text_score(text):
                text = ocr_text
                details["method"] = "ocr"
        return text, details
    if suffix == ".docx":
        details["method"] = "docx_xml"
        return extract_docx(path), details
    if suffix in {".txt", ".md", ".rtf", ".html", ".htm", ".mhtml"}:
        details["method"] = "plain_text"
        return path.read_text("utf-8", errors="replace"), details
    if suffix == ".doc":
        text, method = extract_legacy_doc(path)
        details["method"] = method
        if method == "textutil":
            details["fallbacks"].append("legacy_doc_textutil")
        return text, details
    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return extract_image_ocr(path, tessdata_dir=tessdata_dir)
    return "", details


def unique(items: list[str], limit: int = 80) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = re.sub(r"\s+", " ", item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def context(text: str, start: int, end: int, width: int = 180) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]


def extract_title(text: str, name: str) -> str:
    for line in lines(text)[:40]:
        if line.startswith("=====") or re.fullmatch(r"(?:PAGE|СТРАНИЦА)\s*\d+", line, re.IGNORECASE):
            continue
        if 8 <= len(line) <= 180 and any(ch.isalpha() for ch in line):
            return line
    return name


def extract_constitutional_refs(text: str) -> list[str]:
    refs = [m.group(0) for m in CONSTITUTION_RE.finditer(text)]
    for match in CONSTITUTION_LIST_RE.finditer(text):
        numbers = re.findall(r"\d+(?:\.\d+)?", match.group(1))
        refs.extend([f"статья {num} Конституции Российской Федерации" for num in numbers])
    return unique(refs, 80)


def classify_document(text: str, name: str) -> str:
    for doc_type, pattern in FILENAME_TYPE_PATTERNS:
        if pattern.search(name):
            return doc_type
    haystack = f"{name}\n{text[:6000]}"
    for doc_type, pattern in DOCUMENT_TYPE_PATTERNS:
        if pattern.search(haystack):
            return doc_type
    return "other"


def extract_prayer_block(text: str) -> str:
    text_lines = lines(text)
    for index, line in enumerate(text_lines):
        if PRAYER_RE.search(line):
            block = [item for item in text_lines[index:index + 16] if item]
            return "\n".join(block)[:2500]
    return ""


def extract_labeled_candidates(pattern: re.Pattern[str], text: str, limit: int = 12) -> list[str]:
    return unique([match.group(1) if match.lastindex else match.group(0) for match in pattern.finditer(text[:12000])], limit)


def extraction_quality(text: str, path: Path, details: dict[str, Any]) -> dict[str, Any]:
    low_text = len(text.strip()) < 500 and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    signals = text_quality_signals(text)
    quality = "ok"
    if low_text:
        quality = "low_text"
    elif details.get("method") == "ocr":
        quality = "ocr_review_needed"
    elif path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"} and (
        signals["mojibake_hits"] >= 3 or (expects_cyrillic(path) and signals["cyrillic_ratio"] < 0.35)
    ):
        quality = "encoding_or_ocr_review_needed"
    return {
        "method": details.get("method", "none"),
        "quality": quality,
        "fallbacks": details.get("fallbacks", []),
        "ocr_pages": details.get("ocr_pages", 0),
        "text_quality": signals,
    }


def infer_application_effect(window: str) -> str:
    lowered = window.lower()
    if "не предусмотр" in lowered or "не позволяет" in lowered:
        return "не предусматривает или не позволяет реализовать необходимый механизм"
    if "не допуска" in lowered or "запрещ" in lowered:
        return "запрещает или исключает реализацию права"
    if "отказ" in lowered:
        return "служит основанием отказа"
    if "обязыва" in lowered:
        return "возлагает обязанность или запускает неблагоприятное последствие"
    if "ответствен" in lowered or "санкц" in lowered:
        return "допускает ответственность или санкцию"
    if "истолков" in lowered or "толкован" in lowered:
        return "истолковано в потенциально спорном конституционно-правовом смысле"
    return "могло быть применено как основание спорного правового эффекта"


def normalize_legal_ref(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip().rstrip(".,;:").lower().replace("ё", "е")
    substitutions = [
        (r"(?:\bпункт(?:а|ом|е|у)?\b|\bп\.)\s*", "п "),
        (r"(?:\bчаст(?:ь|и|ью|ей|е)\b|\bч\.)\s*", "ч "),
        (r"(?:\bабзац(?:а|ем|е)?\b|\bабз\.)\s*", "абз "),
        (r"(?:\bстать(?:я|и|е|ю|ей|ёй)\b|\bст\.)\s*", "ст "),
        (r"\bроссийской федерации\b", "рф"),
    ]
    for pattern, replacement in substitutions:
        normalized = re.sub(pattern, replacement, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def canonicalize_legal_ref(value: str) -> str:
    canonical = re.sub(r"\s+", " ", value).strip().rstrip(".,;:")
    replacements = [
        (r"(?:\bпункт(?:а|ом|е|у)?\b|\bп\.)\s*(?=\d)", "п. "),
        (r"(?:\bчаст(?:ь|и|ью|ей|е)\b|\bч\.)\s*(?=\d)", "ч. "),
        (r"(?:\bабзац(?:а|ем|е)?\b|\bабз\.)\s*(?=\d)", "абз. "),
        (r"(?:\bстать(?:я|и|е|ю|ей|ёй)\b|\bст\.)\s*(?=\d)", "ст. "),
    ]
    for pattern, replacement in replacements:
        canonical = re.sub(pattern, replacement, canonical, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", canonical).strip()


def extract_legal_ref_occurrences(text: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for match in LEGAL_REF_RE.finditer(text):
        end = match.end()
        tail_match = NORMATIVE_INSTRUMENT_TAIL_RE.match(text[end:end + 320])
        instrument = ""
        if tail_match:
            instrument = re.sub(r"\s+", " ", tail_match.group("instrument")).strip().rstrip(".,;:")
            end += tail_match.end("instrument")
        value = canonicalize_legal_ref(text[match.start():end])
        occurrences.append({
            "value": value,
            "start": match.start(),
            "end": end,
            "instrument_candidate": instrument,
            "requisites_status": normative_requisites_status(value),
        })
    return occurrences


def instrument_candidate_from_norm(norm: str) -> str:
    locator = LEGAL_REF_RE.match(norm)
    if not locator:
        return ""
    return norm[locator.end():].strip()


def is_constitution_reference(norm: str) -> bool:
    instrument = instrument_candidate_from_norm(norm)
    return bool(re.fullmatch(
        r"Конституци[ияи]\s+(?:РФ|Российской Федерации)",
        instrument,
        re.IGNORECASE,
    ))


def normative_requisites_status(norm: str) -> str:
    instrument = instrument_candidate_from_norm(norm)
    if not instrument:
        return "instrument_missing"
    if is_constitution_reference(norm) or re.search(
        r"(?:(?:ГК|ГПК|АПК|КАС|УПК|КоАП|НК|ТК|УК|ЖК|ЗК|СК|БК|ЛК|УИК|ГрК|ВК|КТМ)\s+РФ|кодекс(?:а|ом|у|е)?\s+(?:РФ|Российской Федерации)|кодекс(?:а|ом|у|е)?.{1,100}(?:РФ|Российской Федерации))",
        instrument,
        re.IGNORECASE,
    ):
        return "complete_instrument_candidate"
    if re.search(r"(?:ФКЗ|закон)", instrument, re.IGNORECASE):
        return "complete_instrument_candidate" if re.search(r"(?:№|\bN)\s*[0-9]", instrument) else "date_or_number_missing"
    return "instrument_identified_requires_official_verification"


def has_named_normative_instrument(norm: str) -> bool:
    return normative_requisites_status(norm) != "instrument_missing"


def is_interpretive_source_locator(norm: str, source_context: str) -> bool:
    return not has_named_normative_instrument(norm) and bool(re.search(
        r"(?:Постановлени|Определени|Обзор).{0,100}(?:Пленум|Верховн|Конституционн)|(?:Пленум|Верховн|Конституционн).{0,100}(?:Постановлени|Определени|Обзор)",
        source_context,
        re.IGNORECASE | re.DOTALL,
    ))


def relative_name(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def clause_context(text: str, start: int, end: int, max_width: int = 360) -> str:
    left_candidates = [text.rfind(separator, max(0, start - max_width), start) for separator in ("\n", ";", ".", "!", "?")]
    left_boundary = max(left_candidates) + 1
    right_candidates = [
        position
        for separator in ("\n", ";", ".", "!", "?")
        if (position := text.find(separator, end, min(len(text), end + max_width))) != -1
    ]
    right_boundary = min(right_candidates) + 1 if right_candidates else min(len(text), end + max_width)
    return re.sub(r"\s+", " ", text[left_boundary:right_boundary]).strip()


def build_timeline_candidates(text: str, document: str, limit: int = 80) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for match in DATE_RE.finditer(text):
        source_context = clause_context(text, match.start(), match.end())
        event_types = [code for code, pattern in EVENT_PATTERNS if pattern.search(source_context)]
        date_prefix = text[max(0, match.start() - 140):match.start()]
        if ACT_TITLE_DATE_PREFIX_RE.search(date_prefix) and "court_decision" not in event_types:
            event_types.insert(0, "court_decision")
        if not event_types:
            event_types = ["unclassified_date"]
        stages = [stage for stage, pattern in STAGE_WORDS.items() if pattern.search(source_context)]
        for event_type in event_types[:2]:
            key = (match.group(0), event_type, source_context)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "date": re.sub(r"\s+", " ", match.group(0)).strip(),
                "event_type": event_type,
                "stage_candidates": stages,
                "document": document,
                "source_context": source_context,
                "confidence": "medium" if event_type != "unclassified_date" else "low",
                "status": "candidate_from_case_document",
            })
            if len(candidates) >= limit:
                return candidates
    return candidates


def build_right_harm_hypotheses(
    text: str,
    document: str,
    constitutional_refs: list[str],
    bridge_candidates: list[dict[str, str]],
    limit: int = 16,
) -> list[dict[str, Any]]:
    explicit_article_numbers = {
        number
        for ref in constitutional_refs
        for number in re.findall(r"\d+(?:\.\d+)?", ref)
    }
    hypotheses: list[dict[str, Any]] = []
    for cfg in RIGHT_HARM_PATTERNS:
        matches = list(cfg["pattern"].finditer(text))
        suggested_articles = cfg["constitutional_articles"]
        suggested_article_numbers = {
            number
            for article in suggested_articles
            for number in re.findall(r"\d+(?:\.\d+)?", article)
        }
        explicit_matches = [
            match
            for match in CONSTITUTION_RE.finditer(text)
            if set(re.findall(r"\d+(?:\.\d+)?", match.group(0))) & suggested_article_numbers
        ]
        positive_explicit_matches = [
            match
            for match in explicit_matches
            if not re.search(
                r"не\s+(?:формулир|заявл|содерж|привод|ссыл)|(?:довод|ссылк|аргумент).{0,45}(?:не\s+заявл|отсутств)",
                context(text, match.start(), match.end(), 90),
                re.IGNORECASE | re.DOTALL,
            )
        ]
        negated_explicit_matches = [match for match in explicit_matches if match not in positive_explicit_matches]
        if not matches and not positive_explicit_matches:
            continue
        explicitly_mentioned = bool(positive_explicit_matches)
        evidence = unique(
            [context(text, match.start(), match.end(), 170) for match in [*matches, *positive_explicit_matches]],
            4,
        )
        linked_bridges = sorted(
            (
                (
                    max((context_overlap(bridge["source_context"], source) for source in evidence), default=0.0),
                    bridge,
                )
                for bridge in bridge_candidates
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        mechanism = (
            linked_bridges[0][1]["bridge"]
            if linked_bridges and linked_bridges[0][0] >= 0.2
            else "Нормативный механизм нужно синтезировать из мотивировки и резолютивной части судебных актов."
        )
        harm_pattern = RIGHT_HARM_ADVERSE_PATTERNS[cfg["code"]]
        has_harm_evidence = any(harm_pattern.search(source) for source in evidence)
        score = min(
            0.95,
            0.35 + min(len(matches), 3) * 0.1 + (0.15 if explicitly_mentioned else 0.0) + (0.15 if has_harm_evidence else 0.0),
        )
        hypotheses.append({
            "hypothesis_code": cfg["code"],
            "constitutional_right_candidate": cfg["right"],
            "constitutional_article_candidates": suggested_articles,
            "legal_consequence_candidate": cfg["consequence"] if has_harm_evidence else "",
            "normative_mechanism_candidate": mechanism,
            "document": document,
            "source_contexts": evidence,
            "negated_explicit_contexts": unique(
                [context(text, match.start(), match.end(), 120) for match in negated_explicit_matches],
                3,
            ),
            "origin": (
                "explicit_and_inferred"
                if explicitly_mentioned and has_harm_evidence
                else "explicit_right_only"
                if explicitly_mentioned
                else "inferred_from_case_materials"
            ),
            "confidence": round(score, 2),
            "status": "right_and_harm_hypothesis" if has_harm_evidence else "right_candidate_without_harm",
        })
        if len(hypotheses) >= limit:
            break
    return hypotheses


def build_application_bridge_candidates(applied_contexts: list[dict[str, str]], limit: int = 8) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for item in applied_contexts:
        norm = item["norm"]
        effect = infer_application_effect(item["context"])
        candidates.append({
            "norm": norm,
            "effect": effect,
            "bridge": f"Кандидат связки: положение «{norm}» упомянуто в контексте, указывающем, что оно {effect}. Проверить, применил ли его суд с таким эффектом, и связать с конкретным конституционным вредом заявителя.",
            "source_context": item["context"],
            "evidence_role": item.get("evidence_role", "unclassified_context"),
        })
        if len(candidates) >= limit:
            break
    return candidates


def suggest_constitutional_tests(text: str, limit: int = 8) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for code, cfg in TEST_PATTERNS.items():
        matches = [context(text, m.start(), m.end(), 120) for m in cfg["pattern"].finditer(text)]
        if matches:
            suggestions.append({
                "test_code": code,
                "confidence": min(0.95, 0.45 + len(matches) * 0.1),
                "signals": unique(matches, 3),
                "missing_evidence": cfg["missing"],
            })
        if len(suggestions) >= limit:
            break
    return suggestions


def build_request_formula_candidates(passport: dict[str, Any], bridge_candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    norms = passport.get("challenged_norm_candidates") or []
    constitutional_refs = passport.get("constitutional_refs") or []
    if not norms:
        return []
    norm = norms[0]
    articles = ", ".join(constitutional_refs[:5]) if constitutional_refs else "[статьи Конституции РФ]"
    effect = bridge_candidates[0]["effect"] if bridge_candidates else "[оспариваемый конституционно-правовой эффект]"
    formulas = [{
        "formula_type": "individual_complaint",
        "text": f"Признать положение «{norm}» не соответствующим Конституции РФ ({articles}) в той мере, в какой оно {effect} в деле заявителя.",
        "review_flags": "Проверить точность нормы, статьи Конституции, фактический крючок и чрезмерную широту формулы.",
    }]
    if passport.get("document_type") == "court_request_motion":
        formulas.append({
            "formula_type": "court_request_motion",
            "text": f"Направить запрос в Конституционный Суд РФ о проверке соответствия положения «{norm}» Конституции РФ ({articles}) в той мере, в какой оно {effect}.",
            "review_flags": "Проверить, что норма подлежит применению текущим судом и вопрос необходим для разрешения дела.",
        })
    return formulas


def context_overlap(left: str, right: str) -> float:
    left_words = {word for word in re.findall(r"[а-яёa-z]{5,}", left.lower())}
    right_words = {word for word in re.findall(r"[а-яёa-z]{5,}", right.lower())}
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / min(len(left_words), len(right_words))


def build_practice_matrix_candidates(
    doc: dict[str, Any],
    applied_contexts: list[dict[str, str]],
    timeline_candidates: list[dict[str, Any]],
    right_harm_hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_numbers = doc.get("case_numbers", [])
    rows: list[dict[str, Any]] = []
    for item in applied_contexts[:10]:
        linked_timeline = sorted(
            (
                (context_overlap(item["context"], candidate["source_context"]), candidate)
                for candidate in timeline_candidates
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        timeline = linked_timeline[0][1] if linked_timeline and linked_timeline[0][0] >= 0.35 else None
        courts = unique([match.group(0) for match in COURT_RE.finditer(item["context"])], 5)
        linked_harm = sorted(
            (
                (
                    max((context_overlap(item["context"], source) for source in hypothesis["source_contexts"]), default=0.0),
                    hypothesis,
                )
                for hypothesis in right_harm_hypotheses
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        harm = linked_harm[0][1] if linked_harm and linked_harm[0][0] >= 0.25 else None
        rows.append({
            "case": case_numbers[0] if case_numbers else "[номер дела не извлечен]",
            "court": courts[0] if courts else "[суд не связан с этим контекстом]",
            "date": timeline["date"] if timeline else "[дата не связана с этим контекстом]",
            "timeline_evidence": timeline or {},
            "norm": item["norm"],
            "interpretive_move": infer_application_effect(item["context"]),
            "proof_source": item["context"],
            "harmful_effect_candidate": harm["legal_consequence_candidate"] if harm else "[гипотеза вреда не связана с этим контекстом]",
            "right_candidate": harm["constitutional_right_candidate"] if harm else "[гипотеза права не связана с этим контекстом]",
            "relevance": "Кандидат для проверки: единичное применение, устойчивая практика или неопределенность.",
        })
    return rows


def build_repeatability_detector(passport: dict[str, Any]) -> dict[str, Any]:
    ksrf_refs = passport.get("ksrf_refs", [])
    norms = passport.get("challenged_norm_candidates", [])
    if not ksrf_refs:
        return {
            "has_prior_ksrf_refs": False,
            "risk": "unknown",
            "review_note": "В документе не найдены ссылки на прежние акты КС РФ; нужен отдельный поиск по норме.",
        }
    return {
        "has_prior_ksrf_refs": True,
        "risk": "review_needed",
        "same_norm_candidates": norms[:10],
        "prior_ksrf_refs": ksrf_refs[:10],
        "new_argument_questions": [
            "Это тот же аспект нормы или новый аспект применения?",
            "Есть ли новое конкретное дело или новая категория заявителя?",
            "Появились ли новые доводы, практика, международный или социальный контекст?",
            "Нужно ли формулировать обращение как новый аспект, а не обжалование прежнего акта КС РФ?",
        ],
    }


def build_execution_packet(passport: dict[str, Any], text: str) -> dict[str, Any]:
    if not passport.get("ksrf_refs") and not re.search(r"пересмотр|вновь открывш|новые обстоятельства", text, re.IGNORECASE):
        return {}
    operative_match = re.search(r"\b(?:ПОСТАНОВИЛ|ОПРЕДЕЛИЛ|РЕШИЛ)\b", text, re.IGNORECASE)
    operative_candidate = context(text, operative_match.start(), operative_match.end(), 1200) if operative_match else ""
    return {
        "ksrf_act_candidates": passport.get("ksrf_refs", [])[:10],
        "possible_post_decision_route": bool(re.search(r"пересмотр|вновь открывш|новые обстоятельства", text, re.IGNORECASE)),
        "operative_meaning_candidate": operative_candidate,
        "operative_meaning_status": "candidate_from_operative_section" if operative_candidate else "operative_section_not_found",
        "affected_persons_candidate": "заявитель и, если это следует из резолютивной части, лица в аналогичном положении",
        "competent_court_task": "Определить по виду судопроизводства, последнему акту и официальной процессуальной норме.",
        "attachment_requirements_to_check": [
            "акт КС РФ",
            "судебные акты по делу заявителя",
            "доказательство вступления акта в силу",
            "доверенность/полномочия",
        ],
    }


def build_qa_matrix(doc: dict[str, Any]) -> list[dict[str, str]]:
    passport = doc["document_passport"]
    doc_type = passport.get("document_type")
    checks = [
        ("document_type", bool(doc_type and doc_type != "other"), "Тип документа определен.", "Тип документа не определен."),
        ("extraction_quality", doc["extraction"]["quality"] == "ok", "Извлечение текста не требует ручной проверки.", "Извлечение текста требует ручной проверки."),
    ]
    core_procedural_docs = {
        "ksrf_complaint",
        "court_request_motion",
        "court_request_by_court",
        "deputy_or_authorized_body_request",
        "post_decision_review_motion",
    }
    if doc_type in core_procedural_docs:
        checks.extend([
            ("challenged_norm", bool(passport.get("challenged_norm_candidates")), "Есть кандидат оспариваемой нормы.", "Не найден кандидат оспариваемой нормы."),
            ("constitutional_refs", bool(passport.get("constitutional_refs")), "Есть ссылки на Конституцию РФ.", "Не найдены ссылки на Конституцию РФ."),
            ("application_context", bool(doc.get("applied_norm_contexts")), "Есть контекст применения или толкования нормы.", "Не найден контекст применения или толкования нормы."),
            ("prayer_block", bool(passport.get("prayer_block")), "Есть просительная часть или просьба.", "Не найдена просительная часть или просьба."),
        ])
    elif doc_type == "request_supplement":
        checks.extend([
            ("supplement_delta", bool(passport.get("case_numbers") or passport.get("ksrf_refs") or passport.get("challenged_norm_candidates")), "Есть зацепка для связи с базовым запросом.", "Не найдена явная связь с базовым запросом; нужна ручная delta map."),
            ("extraction_quality_for_delta", doc["extraction"]["quality"] == "ok", "Текст дополнения можно сопоставлять с базовым обращением.", "Текст дополнения нельзя надежно сопоставить с базовым обращением без ручной проверки."),
        ])
    elif doc_type in {"institutional_position_or_amicus", "amicus_or_expert_conclusion"}:
        checks.extend([
            ("support_function", bool(passport.get("constitutional_refs") or passport.get("ksrf_refs") or doc.get("applied_norm_contexts")), "Материал имеет признаки функциональной связи с конституционным вопросом.", "Нужно вручную определить, какой элемент теста поддерживает материал."),
        ])
    elif doc_type == "science_or_methodology":
        checks.extend([
            ("supporting_source", True, "Научный или методологический материал не требует просительной части; используй его только как supporting source.", "Научный материал требует ручной функции в жалобе."),
        ])
    elif doc_type in {"research_report", "service_or_tool_spec", "telegram_or_channel_research", "practice_retrieval_skill_material", "formal_ksrf_guide", "legal_writing_methodology"}:
        checks.extend([
            ("methodology_source", True, "Материал используется для донасыщения скиллов или продуктовой методологии, а не как самостоятельная жалоба.", "Нужно вручную определить, какой скилл он усиливает."),
        ])
    elif doc_type == "echr_or_un_material":
        checks.extend([
            ("international_support_function", True, "Международный/ООН/ЕСПЧ материал используется только как функциональный supporting source.", "Нужно вручную привязать международный материал к конкретному тесту."),
        ])
    return [
        {"check_code": code, "result": "pass" if ok else "review", "message": pass_message if ok else review_message}
        for code, ok, pass_message, review_message in checks
    ]


def collect_from_document(path: Path, root: Path, enable_ocr: bool, ocr_pages: int, tessdata_dir: str | None = None) -> dict[str, Any]:
    text, extraction_details = extract_text(path, enable_ocr=enable_ocr, ocr_pages=ocr_pages, tessdata_dir=tessdata_dir)
    relative_path = relative_name(path, root)
    lower_name = path.name.lower()
    stages = [stage for stage, rx in STAGE_WORDS.items() if rx.search(text) or rx.search(lower_name)]
    legal_occurrences = extract_legal_ref_occurrences(text)
    legal_refs = unique([item["value"] for item in legal_occurrences])
    constitutional_refs = extract_constitutional_refs(text)
    ksrf_refs = unique([m.group(0) for m in KSRF_RE.finditer(text)])
    doc_type = classify_document(text, path.name)
    applied_contexts: list[dict[str, str]] = []
    if doc_type == "judicial_act":
        evidence_role = "judicial_application_candidate"
    elif doc_type in {"ksrf_complaint", "court_request_motion", "court_request_by_court", "request_supplement"}:
        evidence_role = "party_or_request_reported_application_candidate"
    else:
        evidence_role = "contextual_mention_candidate"
    for occurrence in legal_occurrences:
        window = context(text, occurrence["start"], occurrence["end"])
        norm = occurrence["value"]
        if APPLIED_WORDS_RE.search(window) and not is_constitution_reference(norm):
            item_evidence_role = (
                "interpretive_source_locator"
                if is_interpretive_source_locator(norm, window)
                else evidence_role
            )
            applied_contexts.append({
                "norm": norm,
                "context": window,
                "evidence_role": item_evidence_role,
                "source_document_type": doc_type,
                "instrument_candidate": occurrence["instrument_candidate"],
                "requisites_status": occurrence["requisites_status"],
            })
        if len(applied_contexts) >= 20:
            break
    attachment_signals = [name for name, rx in ATTACHMENT_PATTERNS.items() if rx.search(path.name) or rx.search(text[:5000])]
    prayer_block = extract_prayer_block(text)
    passport = {
        "document_type": doc_type,
        "title": extract_title(text, path.name),
        "applicant_candidates": extract_labeled_candidates(APPLICANT_RE, text),
        "addressee_candidates": unique([m.group(0) for m in ADDRESSEE_RE.finditer(text[:12000])], 12),
        "case_numbers": unique([m.group(0) for m in CASE_RE.finditer(text)], 30),
        "challenged_norm_candidates": [ref for ref in legal_refs if not is_constitution_reference(ref)][:50],
        "challenged_norm_occurrences": [
            item for item in legal_occurrences if not is_constitution_reference(item["value"])
        ][:50],
        "constitutional_refs": constitutional_refs,
        "ksrf_refs": ksrf_refs,
        "prayer_block": prayer_block,
        "attachment_signals": attachment_signals,
    }
    bridge_candidates = build_application_bridge_candidates(applied_contexts)
    timeline_candidates = build_timeline_candidates(text, relative_path)
    right_harm_hypotheses = build_right_harm_hypotheses(
        text,
        relative_path,
        constitutional_refs,
        bridge_candidates,
    )
    test_suggestions = suggest_constitutional_tests(text)
    request_formula_candidates = build_request_formula_candidates(passport, bridge_candidates)
    doc_stub = {
        "courts": unique([m.group(0) for m in COURT_RE.finditer(text)]),
        "dates": unique([m.group(0) for m in DATE_RE.finditer(text)], 120),
        "case_numbers": unique([m.group(0) for m in CASE_RE.finditer(text)]),
    }
    analysis = {
        "application_bridge_candidates": bridge_candidates,
        "constitutional_test_suggestions": test_suggestions,
        "request_formula_candidates": request_formula_candidates,
        "practice_matrix_candidates": build_practice_matrix_candidates(
            doc_stub,
            applied_contexts,
            timeline_candidates,
            right_harm_hypotheses,
        ),
        "repeatability_detector": build_repeatability_detector(passport),
        "ksrf_execution_packet": build_execution_packet(passport, text),
    }
    qa_matrix = build_qa_matrix({
        "document_passport": passport,
        "applied_norm_contexts": applied_contexts,
        "extraction": extraction_quality(text, path, extraction_details),
    })
    return {
        "path": str(path),
        "relative_path": relative_path,
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "text_chars": len(text),
        "extraction": extraction_quality(text, path, extraction_details),
        "extraction_quality": extraction_quality(text, path, extraction_details),
        "low_text_risk": len(text.strip()) < 500 and path.suffix.lower() in {".pdf", ".doc", ".docx"},
        "document_passport": passport,
        "case_numbers": unique([m.group(0) for m in CASE_RE.finditer(text)]),
        "dates": unique([m.group(0) for m in DATE_RE.finditer(text)], 120),
        "timeline_candidates": timeline_candidates,
        "courts": unique([m.group(0) for m in COURT_RE.finditer(text)]),
        "stages": stages,
        "legal_refs": legal_refs,
        "constitutional_refs": constitutional_refs,
        "ksrf_refs": ksrf_refs,
        "applied_norm_contexts": applied_contexts,
        "right_harm_hypotheses": right_harm_hypotheses,
        "automation_analysis": analysis,
        "qa_matrix": qa_matrix,
        "attachment_signals": attachment_signals,
    }


def rank_challenged_norm_candidates(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    complaint_types = {"ksrf_complaint", "court_request_motion", "request_supplement"}
    for doc in documents:
        passport = doc["document_passport"]
        prayer = passport.get("prayer_block", "")
        for ref in passport.get("challenged_norm_candidates", []):
            key = normalize_legal_ref(ref)
            if not has_named_normative_instrument(ref) and (not prayer or key not in normalize_legal_ref(prayer)):
                continue
            entry = registry.setdefault(key, {
                "norm": ref,
                "instrument_candidate": instrument_candidate_from_norm(ref),
                "requisites_status": normative_requisites_status(ref),
                "score": 0,
                "document_mentions": [],
                "applied_evidence": [],
                "effect_candidates": [],
            })
            entry["score"] += 1
            entry["document_mentions"].append(doc["relative_path"])
            if passport.get("document_type") in complaint_types:
                entry["score"] += 1
            if prayer and key in normalize_legal_ref(prayer):
                entry["score"] += 3
        for item in doc.get("applied_norm_contexts", []):
            if is_interpretive_source_locator(item["norm"], item["context"]):
                continue
            key = normalize_legal_ref(item["norm"])
            entry = registry.setdefault(key, {
                "norm": item["norm"],
                "instrument_candidate": item.get("instrument_candidate", instrument_candidate_from_norm(item["norm"])),
                "requisites_status": item.get("requisites_status", normative_requisites_status(item["norm"])),
                "score": 0,
                "document_mentions": [],
                "applied_evidence": [],
                "effect_candidates": [],
            })
            evidence_role = item.get("evidence_role", "unclassified_context")
            evidence_weight = {
                "judicial_application_candidate": 6,
                "party_or_request_reported_application_candidate": 3,
                "contextual_mention_candidate": 1,
            }.get(evidence_role, 1)
            entry["score"] += evidence_weight
            entry["document_mentions"].append(doc["relative_path"])
            entry["applied_evidence"].append({
                "document": doc["relative_path"],
                "source_context": item["context"],
                "evidence_role": evidence_role,
            })
            entry["effect_candidates"].append(infer_application_effect(item["context"]))

    ranked: list[dict[str, Any]] = []
    for entry in registry.values():
        applied = entry["applied_evidence"]
        evidence_roles = {item.get("evidence_role") for item in applied}
        exact_instrument = entry["requisites_status"] == "complete_instrument_candidate"
        if "judicial_application_candidate" in evidence_roles and exact_instrument:
            candidate_role = "application_anchor_candidate"
        elif "judicial_application_candidate" in evidence_roles:
            candidate_role = "application_locator_candidate"
        elif "party_or_request_reported_application_candidate" in evidence_roles:
            candidate_role = "reported_application_candidate" if exact_instrument else "reported_application_locator_candidate"
        elif applied:
            candidate_role = "contextual_mention_candidate"
        else:
            candidate_role = "mentioned_norm_candidate"
        ranked.append({
            "norm": entry["norm"],
            "instrument_candidate": entry["instrument_candidate"],
            "requisites_status": entry["requisites_status"],
            "score": entry["score"],
            "document_mentions": unique(entry["document_mentions"], 30),
            "applied_evidence": applied[:12],
            "effect_candidates": unique(entry["effect_candidates"], 8),
            "candidate_role": candidate_role,
            "status": (
                "candidate_requires_official_text_and_case_verification"
                if exact_instrument
                else "candidate_requires_normative_instrument_recovery"
            ),
        })
    return sorted(ranked, key=lambda item: (-item["score"], item["norm"]))[:40]


def merge_right_harm_hypotheses(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for doc in documents:
        for item in doc.get("right_harm_hypotheses", []):
            code = item["hypothesis_code"]
            entry = registry.setdefault(code, {
                "hypothesis_code": code,
                "constitutional_right_candidate": item["constitutional_right_candidate"],
                "constitutional_article_candidates": [],
                "legal_consequence_candidates": [],
                "normative_mechanism_candidates": [],
                "documents": [],
                "source_contexts": [],
                "confidence": 0.0,
                "origins": [],
                "statuses": [],
            })
            entry["constitutional_article_candidates"].extend(item["constitutional_article_candidates"])
            if item["legal_consequence_candidate"]:
                entry["legal_consequence_candidates"].append(item["legal_consequence_candidate"])
            entry["normative_mechanism_candidates"].append(item["normative_mechanism_candidate"])
            entry["documents"].append(item["document"])
            entry["source_contexts"].extend(item["source_contexts"])
            entry["confidence"] = max(entry["confidence"], item["confidence"])
            entry["origins"].append(item["origin"])
            entry["statuses"].append(item["status"])

    merged: list[dict[str, Any]] = []
    for entry in registry.values():
        merged.append({
            "hypothesis_code": entry["hypothesis_code"],
            "constitutional_right_candidate": entry["constitutional_right_candidate"],
            "constitutional_article_candidates": unique(entry["constitutional_article_candidates"], 8),
            "legal_consequence_candidates": unique(entry["legal_consequence_candidates"], 6),
            "normative_mechanism_candidates": unique(entry["normative_mechanism_candidates"], 6),
            "documents": unique(entry["documents"], 30),
            "source_contexts": unique(entry["source_contexts"], 8),
            "origin": (
                "explicit_and_inferred"
                if "explicit_and_inferred" in entry["origins"]
                else "inferred_from_case_materials"
                if "inferred_from_case_materials" in entry["origins"]
                else "explicit_right_only"
            ),
            "confidence": entry["confidence"],
            "status": (
                "right_and_harm_hypothesis"
                if "right_and_harm_hypothesis" in entry["statuses"]
                else "right_candidate_without_harm"
            ),
        })
    return sorted(merged, key=lambda item: (-item["confidence"], item["hypothesis_code"]))


def merge(documents: list[dict[str, Any]]) -> dict[str, Any]:
    missing: list[str] = []
    if not any(doc["applied_norm_contexts"] for doc in documents):
        missing.append("Не извлечён явный контекст применения нормы: повторно проанализировать мотивировку и резолютивную часть актов, затем найти недостающий акт по номеру дела.")
    if not any("кассация" in doc["stages"] or "верховный суд" in doc["stages"] for doc in documents):
        missing.append("Не найдены очевидные признаки кассации или Верховного Суда: реконструировать путь по актам и официальным карточкам дела.")
    if not any("госпошлина" in doc["attachment_signals"] for doc in documents):
        missing.append("Не найден документ госпошлины или ходатайство о льготе/отсрочке.")
    if not any("доверенность" in doc["attachment_signals"] for doc in documents):
        missing.append("Не найдена доверенность; это нормально только если заявитель подает лично без представителя.")
    if any(doc["low_text_risk"] for doc in documents):
        missing.append("Есть PDF/DOC/DOCX с малым извлечённым текстом: применить OCR и визуальное чтение средствами среды выполнения до вывода о пробеле.")

    autonomous_followups = []
    if any("официальным карточкам" in item for item in missing):
        autonomous_followups.append("Найти завершающий акт и даты обжалования в переданном пакете, затем в официальной карточке дела по номеру производства.")
    if any("применения нормы" in item for item in missing):
        autonomous_followups.append("Перечитать мотивировочную и резолютивную части всех актов; ранжировать нормы по их причинной роли и проверить текст нормы в официальном источнике.")
    if not any(doc["constitutional_refs"] for doc in documents):
        autonomous_followups.append("Самостоятельно построить гипотезы затронутого права из нормативного эффекта и последствий; отдельно проверить, сохранялся ли конституционный довод в поданных жалобах.")

    norm_candidates = rank_challenged_norm_candidates(documents)
    timeline_candidates = [item for doc in documents for item in doc.get("timeline_candidates", [])][:240]
    right_harm_hypotheses = merge_right_harm_hypotheses(documents)
    case_number_candidates = unique([item for doc in documents for item in doc["case_numbers"]], 20)
    meaningful_timeline = [item for item in timeline_candidates if item["event_type"] != "unclassified_date"]
    judicial_application_candidates = [
        item for item in norm_candidates if item["candidate_role"] == "application_anchor_candidate"
    ]
    exact_norm_candidates = [
        item for item in norm_candidates if item["requisites_status"] == "complete_instrument_candidate"
    ]
    complete_right_harm_hypotheses = [
        item for item in right_harm_hypotheses if item["status"] == "right_and_harm_hypothesis"
    ]
    unresolved_candidates_before_verification: list[dict[str, str]] = []
    if not case_number_candidates:
        unresolved_candidates_before_verification.append({
            "gap_code": "case_identity_not_extracted",
            "autonomous_action": "Идентифицировать дело по суду, сторонам, датам и нормам в полных актах и официальных карточках.",
            "conditional_question": "Если дело не идентифицировано после официального поиска, запросить любой полный судебный акт с номером дела.",
        })
    if not meaningful_timeline:
        unresolved_candidates_before_verification.append({
            "gap_code": "procedural_timeline_not_reconstructed",
            "autonomous_action": "Отделить даты источников и документов от процессуальных событий; найти акты и подачи по официальной карточке дела.",
            "conditional_question": "Если процессуальные события не восстановлены, запросить конкретные отсутствующие акты, а не перечень дат вручную.",
        })
    if not judicial_application_candidates:
        unresolved_candidates_before_verification.append({
            "gap_code": "judicial_application_not_confirmed",
            "autonomous_action": "Найти полный судебный акт и цитатное окно, подтверждающее причинную роль лидирующего кандидата нормы.",
            "conditional_question": "Если акт применения не найден официально, запросить копию решения или определения, на котором основан неблагоприятный результат.",
        })
    if norm_candidates and not exact_norm_candidates:
        unresolved_candidates_before_verification.append({
            "gap_code": "normative_instrument_not_identified",
            "autonomous_action": "Восстановить полное наименование, дату и номер нормативного акта по цитатному окну, полному судебному акту и официальному источнику; bare locator не считать точной оспариваемой нормой.",
            "conditional_question": "Если реквизиты не восстановлены после OCR полного акта и официального поиска, запросить конкретную отсутствующую страницу или судебный акт, а не просить пользователя назвать норму.",
        })
    if not complete_right_harm_hypotheses:
        unresolved_candidates_before_verification.append({
            "gap_code": "right_harm_chain_not_inferred",
            "autonomous_action": "Вывести цепочку права и последствия из резолютивной части, фактического результата и механизма нормы.",
            "conditional_question": "Если фактическое последствие не видно из документов и официальных актов, запросить только конкретный недостающий факт или документ.",
        })
    if not norm_candidates:
        unresolved_candidates_before_verification.append({
            "gap_code": "challenged_norm_not_extracted",
            "autonomous_action": "Повторить анализ мотивировки и резолютивной части и найти акт применения по реквизитам дела.",
            "conditional_question": "Если после OCR, анализа всех актов и официального поиска норма не установлена, запросить только отсутствующий судебный акт, а не просить пользователя сформулировать норму.",
        })
    official_verification_tasks: list[dict[str, Any]] = [
        {
            "task_type": "verify_norm",
            "norm": item["norm"],
            "instrument_candidate": item["instrument_candidate"],
            "requisites_status": item["requisites_status"],
            "task": (
                "Получить из официального источника точный текст, редакцию на дату применения и историю изменений; сверить с цитатным окном судебного акта."
                if item["requisites_status"] == "complete_instrument_candidate"
                else "Сначала восстановить точное наименование, дату и номер нормативного акта по полному судебному акту и официальным источникам; затем проверить текст и редакцию нормы."
            ),
        }
        for item in norm_candidates[:8]
    ]
    official_verification_tasks.extend({
        "task_type": "resolve_intake_gap",
        "gap_code": item["gap_code"],
        "task": item["autonomous_action"],
    } for item in unresolved_candidates_before_verification)
    if timeline_candidates or any(doc["case_numbers"] for doc in documents):
        official_verification_tasks.append({
            "task_type": "verify_procedural_timeline",
            "case_number_candidates": case_number_candidates,
            "event_candidates": timeline_candidates[:30],
            "task": "Сверить даты актов, подач, получения и вступления в силу по полным актам и официальным карточкам дел; устранить даты нормативных источников и иные ложные события.",
        })
    question_candidates_after_verification = unique(
        [item["conditional_question"] for item in unresolved_candidates_before_verification],
        12,
    )

    return {
        "case_numbers": unique([item for doc in documents for item in doc["case_numbers"]], 120),
        "dates": unique([item for doc in documents for item in doc["dates"]], 200),
        "timeline_candidates": timeline_candidates,
        "courts": unique([item for doc in documents for item in doc["courts"]], 120),
        "stages": unique([item for doc in documents for item in doc["stages"]], 40),
        "legal_refs": unique([item for doc in documents for item in doc["legal_refs"]], 200),
        "constitutional_refs": unique([item for doc in documents for item in doc["constitutional_refs"]], 80),
        "ksrf_refs": unique([item for doc in documents for item in doc["ksrf_refs"]], 80),
        "applied_norm_contexts": [ctx for doc in documents for ctx in doc["applied_norm_contexts"]][:80],
        "challenged_norm_candidates_ranked": norm_candidates,
        "right_harm_hypotheses": right_harm_hypotheses,
        "autonomous_intake": {
            "challenged_norm_candidates": norm_candidates,
            "procedural_timeline_candidates": timeline_candidates,
            "right_harm_hypotheses": right_harm_hypotheses,
            "official_verification_tasks": official_verification_tasks,
            "verification": {
                "status": "pending_official_pass",
                "norms": "pending",
                "procedural_timeline": "pending",
                "right_harm_chain": "pending",
            },
            "official_lookup_status": "not_performed_by_offline_collector",
            "autonomous_followups": unique(autonomous_followups, 12),
            "unresolved_candidates_before_verification": unresolved_candidates_before_verification,
            "unresolved_after_exhaustion": None,
            "question_candidates_after_verification": question_candidates_after_verification,
        },
        "document_passports": [doc["document_passport"] for doc in documents],
        "application_bridge_candidates": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("application_bridge_candidates", [])
        ][:80],
        "constitutional_test_suggestions": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("constitutional_test_suggestions", [])
        ][:80],
        "request_formula_candidates": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("request_formula_candidates", [])
        ][:30],
        "practice_matrix_candidates": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("practice_matrix_candidates", [])
        ][:80],
        "repeatability_review_items": [
            {"document": doc["relative_path"], **doc.get("automation_analysis", {}).get("repeatability_detector", {})}
            for doc in documents
            if doc.get("automation_analysis", {}).get("repeatability_detector", {}).get("has_prior_ksrf_refs")
        ][:40],
        "ksrf_execution_packets": [
            {"document": doc["relative_path"], **doc.get("automation_analysis", {}).get("ksrf_execution_packet", {})}
            for doc in documents
            if doc.get("automation_analysis", {}).get("ksrf_execution_packet")
        ][:40],
        "qa_review_items": [
            {"document": doc["relative_path"], **item}
            for doc in documents
            for item in doc.get("qa_matrix", [])
            if item["result"] != "pass"
        ][:120],
        "attachment_signals": {
            signal: [doc["relative_path"] for doc in documents if signal in doc["attachment_signals"]]
            for signal in ATTACHMENT_PATTERNS
        },
        "missing_or_risky": missing,
        "next_questions": [],
        "question_candidates_after_verification": question_candidates_after_verification,
    }


def is_excluded(path: Path, root: Path, patterns: list[str]) -> bool:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = path.name
    return any(
        fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(relative, pattern)
        for pattern in patterns
    )


def iter_files(paths: list[Path], exclude_patterns: list[str] | None = None) -> list[Path]:
    allowed = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".html", ".htm", ".mhtml", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    excluded = exclude_patterns or []
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            for current, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
                current_path = Path(current)
                dirnames[:] = [
                    name
                    for name in dirnames
                    if not is_excluded(current_path / name, path, excluded)
                ]
                files.extend(
                    current_path / name
                    for name in filenames
                    if not is_excluded(current_path / name, path, excluded)
                    and (current_path / name).suffix.lower() in allowed
                )
        elif path.is_file() and path.suffix.lower() in allowed and not is_excluded(path, path.parent, excluded):
            files.append(path)
    return sorted(files)


class _RussianArgumentParser(argparse.ArgumentParser):
    """Показывать русскую справку и требовать точные имена параметров."""

    _HELP_METAVARS = {
        "paths": "ПУТЬ",
        "out": "ФАЙЛ",
        "ocr_pages": "ЧИСЛО",
        "tessdata_dir": "ПАПКА",
        "exclude": "ШАБЛОН",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def format_help(self) -> str:
        localized = [
            (action, action.metavar)
            for action in self._actions
            if action.dest in self._HELP_METAVARS
        ]
        for action, _metavar in localized:
            action.metavar = self._HELP_METAVARS[action.dest]
        try:
            rendered = super().format_help()
        finally:
            for action, metavar in localized:
                action.metavar = metavar
        return (
            rendered
            .replace("usage:", "Использование:", 1)
            .replace("positional arguments:", "позиционные аргументы:", 1)
            .replace("optional arguments:", "параметры:", 1)
            .replace("options:", "параметры:", 1)
            .replace(
                "show this help message and exit",
                "показать эту справку и выйти",
            )
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = _RussianArgumentParser(
        description=(
            "Собрать первичную карточку дела из сохранённых документов для "
            "подготовки жалобы в КС РФ."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Один или несколько файлов либо папок с материалами дела.",
    )
    parser.add_argument(
        "--out",
        help=(
            "Файл для результата в формате JSON; если не указан, результат "
            "выводится на экран."
        ),
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help=(
            "Не использовать резервное распознавание текста (OCR) для "
            "PDF-файлов, из которых извлечено мало текста."
        ),
    )
    parser.add_argument(
        "--ocr-pages",
        type=int,
        default=8,
        help="Сколько первых страниц каждого PDF-файла распознавать; по умолчанию 8.",
    )
    parser.add_argument(
        "--tessdata-dir",
        help=(
            "Папка с языковыми данными Tesseract; если не указана, используются "
            "системные данные."
        ),
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help=(
            "Не обрабатывать файл или папку, имя которых совпадает с шаблоном; "
            "параметр можно повторить (например, --exclude 'private-*')."
        ),
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    input_paths = [Path(p).expanduser().resolve() for p in args.paths]
    files = iter_files(input_paths, args.exclude)
    if not files:
        print("Не найдено поддерживаемых файлов.", file=sys.stderr)
        return 2
    root = input_paths[0] if input_paths[0].is_dir() else input_paths[0].parent
    documents = [collect_from_document(path, root, enable_ocr=not args.no_ocr, ocr_pages=args.ocr_pages, tessdata_dir=args.tessdata_dir) for path in files]
    report = {
        "schema": "ksrf.casefile.v3",
        "inputs": [str(p) for p in input_paths],
        "exclusions": args.exclude,
        "document_count": len(documents),
        "documents": documents,
        "summary": merge(documents),
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).expanduser().resolve().write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

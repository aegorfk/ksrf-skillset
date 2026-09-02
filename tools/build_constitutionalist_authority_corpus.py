#!/usr/bin/env python3
"""Build the broad constitutionalist authority corpus used by KSRF skills.

The script intentionally separates a scholar's presence in a source from the
readiness of that scholar's method for drafting.  It combines:

* P. D. Blokhin's dissertation bibliography;
* official article indexes of SKO and International Justice;
* the local Zakon.ru discovery corpus;
* a small, manually verified set of full-text method cards.

Only the last set receives ``method_integrated`` status automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "2.0"

STATUS_ORDER = {
    "method_integrated": 0,
    "full_text_available": 1,
    "triangulated_academic": 2,
    "academic_indexed": 3,
    "bibliographic_lead": 4,
    "discovery_only": 5,
}

STATUS_LABELS = {
    "method_integrated": "метод извлечён и встроен",
    "full_text_available": "полный текст доступен; метод ожидает извлечения",
    "triangulated_academic": "автор подтверждён несколькими академическими слоями",
    "academic_indexed": "автор найден в официальном академическом указателе",
    "bibliographic_lead": "библиографический след у Блохина",
    "discovery_only": "разведочный кандидат; авторитетность не подтверждена",
}

SOURCE_LABELS = {
    "curated_method": "проверенная методическая карточка",
    "local_full_text": "локальный полный текст",
    "blokhin_bibliography": "библиография диссертации П. Д. Блохина",
    "sko_index": "официальный указатель СКО 1992–2026",
    "mp_index": "официальный указатель «Международного правосудия» 2011–2026",
    "zakon_discovery": "локальный разведочный корпус Zakon.ru",
}

ROUTE_RULES = {
    "admissibility_and_route": (
        r"жалоб|допустим|приемлем|секретариат|доступ к конституцион|"
        r"constitutional complaint|standing|admissib",
        "допустимость, доступ к КС РФ и граница сверхинстанционности",
    ),
    "interpretation_and_positions": (
        r"толкован|правов.{0,5} позиц|прецедент|stare decisis|jurisprudence constante|"
        r"precedent|interpretation|legal reasoning|аналог",
        "толкование, правовые позиции, прецедент и перенос правила",
    ),
    "proportionality_equality_dignity": (
        r"пропорц|соразмер|баланс|равенств|достоинств|proportional|balanc|equality|dignity",
        "соразмерность, равенство, достоинство и интенсивность контроля",
    ),
    "evidence_empirics_consequences": (
        r"доказ|факт|статист|эмпир|последств|экономическ.{0,8} анализ|evidence|empiric|consequence|econom",
        "доказывание, законодательные факты, эмпирика и последствия",
    ),
    "remedy_execution_review": (
        r"исполнен|пересмотр|средств.{0,8} защит|последств.{0,8} решени|remed|execution|enforc|retroactiv",
        "средство защиты, исполнение, пересмотр и действие решения",
    ),
    "institutional_design_and_legitimacy": (
        r"судей|судебн.{0,8} актив|аппарат|секретариат|разделен.{0,5} власт|"
        r"constitutional court|judicial review|judicial activ|legitima|юрисдикц",
        "институциональный дизайн, компетенция и легитимность контроля",
    ),
    "comparative_and_international": (
        r"сравнител|зарубеж|германи|сша|европейск|еспч|международ|comparative|foreign|echr|human rights|german",
        "сравнительное право и международные стандарты прав человека",
    ),
    "certainty_communication_writing": (
        r"определенн|ясност|коммуникац|юридическ.{0,5} письм|аргументац|методолог|"
        r"certainty|communication|argumentation|methodolog|writing",
        "правовая определённость, аргументация, коммуникация и письмо",
    ),
    "identity_sovereignty_systems": (
        r"идентичност|суверен|верховенств|правов.{0,5} систем|identity|sovereign|supremacy|legal system",
        "конституционная идентичность, суверенитет и взаимодействие систем",
    ),
    "social_economic_and_property_rights": (
        r"социальн|трудов|налог|собственност|бюджет|имуществен|social right|labour|labor|tax|property|budget",
        "социальные, трудовые, налоговые и имущественные права",
    ),
    "democracy_federalism_public_power": (
        r"демократ|федерал|выбор|парламент|местн.{0,5} самоуправ|публичн.{0,5} власт|"
        r"democra|federal|election|parliament|local government",
        "демократия, федерализм и организация публичной власти",
    ),
    "bioethics_privacy_technology": (
        r"биоэтик|репродуктив|генетич|частн.{0,5} жизн|персональн.{0,5} дан|технолог|"
        r"bioethic|reproduct|genetic|privacy|personal data|technolog",
        "биоэтика, частная жизнь, данные и технологии",
    ),
}


CURATED = [
    {
        "canonical_name": "Павел Дмитриевич Блохин",
        "role": "российская методология конституционного нормоконтроля",
        "aliases": ["Блохин П. Д.", "Блохин П.Д.", "Павел Блохин"],
        "routes": [
            "admissibility_and_route",
            "interpretation_and_positions",
            "proportionality_equality_dignity",
            "remedy_execution_review",
            "certainty_communication_writing",
        ],
        "full_text_sources": [
            "Блохин П. Д. Методы осуществления судебного конституционного нормоконтроля (диссертация)",
        ],
        "method_cards": [
            {
                "method": "лестница выбора метода контроля",
                "usable_for": "выбор между буквальным/системным толкованием, переносом позиции, конституционной корректировкой и соразмерностью",
                "guardrail": "метод не заменяет допустимость и точную проверку официальной позиции КС РФ",
                "skill_reference": "constitutional-review-methods.md",
            },
            {
                "method": "карточка и перенос правовой позиции",
                "usable_for": "сопоставление вопроса, правила, сферы, ограничителей и последствия",
                "guardrail": "не переносить общий тезис без совпадения нормативного механизма и remedy",
                "skill_reference": "constitutional-review-methods.md",
            },
        ],
    },
    {
        "canonical_name": "Алексей Вячеславович Должиков",
        "role": "соразмерность в конституционном правосудии",
        "aliases": ["Должиков А. В.", "Должиков А.В.", "Алексей Должиков"],
        "routes": ["proportionality_equality_dignity", "evidence_empirics_consequences", "social_economic_and_property_rights"],
        "full_text_sources": [
            "Должиков А. В. Соразмерность как общеправовой принцип в конституционном правосудии России",
            "Должиков А. В., Васильева А. Ф. «Почему? По кочану!»: принцип обоснованности в административном праве",
        ],
        "method_cards": [
            {
                "method": "структурированный тест соразмерности",
                "usable_for": "цель, пригодность, необходимость, баланс и интенсивность контроля",
                "guardrail": "каждая ступень требует фактического или нормативного крючка; баланс не является арифметикой",
                "skill_reference": "constitutional-review-methods.md; science-support-pack.md",
            },
            {
                "method": "трёхуровневый тест обоснованности публичного решения",
                "usable_for": "разделение письменной мотивировки, права быть услышанным и материальной проверки цели, доказательств и релевантных факторов",
                "guardrail": "не подменять законность целесообразностью и не превращать единично слабую мотивировку в нормативный дефект без носителя",
                "skill_reference": "sko-complaint-methods-2017-2026.md; workflow-reference.md",
            },
        ],
    },
    {
        "canonical_name": "Алдар Мункожаргалович Чирнинов",
        "role": "конституционное доказывание и аргументация",
        "aliases": ["Чирнинов А. М.", "Чирнинов А.М.", "Алдар Чирнинов"],
        "routes": [
            "admissibility_and_route",
            "evidence_empirics_consequences",
            "certainty_communication_writing",
            "comparative_and_international",
            "institutional_design_and_legitimacy",
            "remedy_execution_review",
        ],
        "full_text_sources": [
            "Чирнинов А. М. Доказывание и доказательства в конституционном судебном процессе РФ и США",
            "Чирнинов А. М. Нельзя объять необъятное: предмет доказывания в конституционном судебном процессе (на примере России и США)",
            "Чирнинов А. М. Убедить нельзя принудить: цель и функции конституционно-судебной аргументации",
            "Чирнинов А. М. Янус оказался одноликим: аргументационный анализ Постановления КС РФ № 33-П",
            "Чирнинов А. М. «Процессуальный небожитель?»: дело о возможности оспаривания бездействия председателя суда в порядке административного судопроизводства",
        ],
        "method_cards": [
            {
                "method": "паспорт конституционного доказательства",
                "usable_for": "предмет, бремя, сбор, исследование и оценка законодательных/обобщённых фактов",
                "guardrail": "не подменять нормативный дефект повторной оценкой индивидуальных фактов дела",
                "skill_reference": "evidence-impact-method.md; science-support-pack.md",
            },
            {
                "method": "аргумент к последствиям",
                "usable_for": "проверка практического эффекта нормы, альтернатив и переходного режима",
                "guardrail": "отделять доказанные последствия от гипотез и избегать недоказанного скользкого склона",
                "skill_reference": "science-support-pack.md",
            },
            {
                "method": "три поля и четыре функции конституционной аргументации",
                "usable_for": "разделение конституционно должного, нормативно существующего и фактического с проверкой корректирующей, прогностической, познавательной и легитимирующей функции",
                "guardrail": "убедительность не компенсирует недостоверность, отсутствие нормативного носителя или пустое причинное звено",
                "skill_reference": "sko-complaint-methods-2017-2026.md; constitutional-review-methods.md",
            },
            {
                "method": "состязательная карта и тест названия на функцию",
                "usable_for": "сопоставление официальных позиций и проверка, устранён ли механизм дефекта, а не только изменён термин",
                "guardrail": "расхождение позиций поддерживает неопределённость, но не заменяет текст, применение и влияние на исход",
                "skill_reference": "sko-complaint-methods-2017-2026.md; strategic-complaint-design.md",
            },
            {
                "method": "таксономия фактов и срок конституционной годности",
                "usable_for": "разделение содержательных законодательных, процедурных и процессуальных фактов, проверка их относимости, опровержимости и временной актуальности",
                "guardrail": "эмпирика оценивает фактическую основу нормативного решения и не превращает КС РФ в суд повторного установления индивидуальных фактов",
                "skill_reference": "sko-complaint-methods-2017-2026.md; evidence-impact-method.md; science-support-pack.md",
            },
            {
                "method": "функциональный тест статуса и реальности альтернативного средства",
                "usable_for": "отделение защищённой функции правосудия от судебного администрирования и проверка, существует ли иной судебный путь для того же нарушения",
                "guardrail": "не использовать административный контроль или обжалование другого акта как эквивалентное средство без совпадения предмета и восстановительного эффекта",
                "skill_reference": "sko-complaint-methods-2017-2026.md; strategic-complaint-design.md",
            },
        ],
    },
    {
        "canonical_name": "Елена Александровна Сорокина",
        "role": "диалоговые и структурные средства защиты социально-экономических прав",
        "aliases": ["Сорокина Е. А.", "Сорокина Е.А.", "Елена Сорокина"],
        "routes": [
            "remedy_execution_review",
            "institutional_design_and_legitimacy",
            "comparative_and_international",
            "social_economic_and_property_rights",
        ],
        "full_text_sources": [
            "Сорокина Е. А. Конструктивное взаимодействие как средство защиты социально-экономических прав в Южно-Африканской Республике",
        ],
        "method_cards": [
            {
                "method": "карточка конструктивного взаимодействия",
                "usable_for": "проектирование участия затронутых лиц, раскрытия альтернатив, временной защиты, срока, отчётности, надзора и эскалации при сложной позитивной обязанности",
                "guardrail": "южноафриканская модель не создаёт полномочий КС РФ; каждый элемент требует российского нормативного якоря и компетентного адресата",
                "skill_reference": "sko-complaint-methods-2017-2026.md; strategic-complaint-design.md; workflow-reference.md",
            },
            {
                "method": "тест институциональных слепых пятен",
                "usable_for": "проверка непредвиденных последствий применения, исключённой перспективы уязвимой группы и инерции публичного органа",
                "guardrail": "участие не заменяет материальный стандарт права и не считается реальным по одному факту консультации",
                "skill_reference": "sko-complaint-methods-2017-2026.md; strategic-complaint-design.md",
            },
        ],
    },
    {
        "canonical_name": "Дмитрий Дедов",
        "role": "структурная целостность правовых позиций высших судов",
        "aliases": ["Дедов Д. И.", "Дедов Д.И.", "Дмитрий Иванович Дедов"],
        "routes": [
            "interpretation_and_positions",
            "certainty_communication_writing",
            "evidence_empirics_consequences",
            "institutional_design_and_legitimacy",
            "proportionality_equality_dignity",
        ],
        "full_text_sources": [
            "Дедов Д. И. Структурные дефекты правовых позиций высших судов",
        ],
        "method_cards": [
            {
                "method": "аудит структурной целостности правовой позиции",
                "usable_for": "проверка доктринальной памяти, системных связей, квалификации права, соотношения общего и специального правила и процессуальной защиты",
                "guardrail": "критиковать объективные пропуски и несовместимые правила, а не приписывать суду скрытую цель без доказательств",
                "skill_reference": "constitutional-review-methods.md; workflow-reference.md; sko-complaint-methods-2017-2026.md",
            },
            {
                "method": "разделение усмотрения и доказываемого фактического основания",
                "usable_for": "выявление специального факта, который запускает полномочие и должен быть доказан и оспорим до дискреционного решения",
                "guardrail": "не просить КС РФ установить факт; нужен нормативный носитель смешения факта, бремени и исключения контроля",
                "skill_reference": "evidence-impact-method.md; constitutional-review-methods.md",
            },
        ],
    },
    {
        "canonical_name": "Гадис Абдуллаевич Гаджиев",
        "role": "конституционная онтология и правовая определённость",
        "aliases": ["Гаджиев Г. А.", "Гаджиев Г.А.", "Гадис Гаджиев"],
        "routes": ["interpretation_and_positions", "certainty_communication_writing", "evidence_empirics_consequences"],
        "full_text_sources": ["Гаджиев Г. А. Онтология права"],
        "method_cards": [
            {
                "method": "различение текста, правового концепта и правовой реальности",
                "usable_for": "объяснение, почему конституционный смысл не исчерпывается буквами отраслевой нормы",
                "guardrail": "не смешивать юридический, эмпирический и экономический уровни без явного перехода",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Арина Викторовна Дмитриева",
        "role": "эмпирика отбора дел и юридическое письмо",
        "aliases": ["Дмитриева А. В.", "Арина Дмитриева"],
        "routes": ["admissibility_and_route", "institutional_design_and_legitimacy", "certainty_communication_writing"],
        "full_text_sources": [
            "Дмитриева А. В. Отбор дел в Конституционном Суде РФ: роль Секретариата",
            "Дмитриева А. В. Искусство юридического письма: количественный анализ решений КС РФ",
        ],
        "method_cards": [
            {
                "method": "модель секретариатского фильтра",
                "usable_for": "ясное предъявление нормативной проблемы с учётом rule-following, усмотрения и организационной рутины",
                "guardrail": "эмпирическое наблюдение не является процессуальной нормой и не гарантирует принятие жалобы",
                "skill_reference": "science-support-pack.md",
            },
            {
                "method": "проверка читаемости формулы",
                "usable_for": "ясность просимого конституционного смысла для гражданина и обычного суда",
                "guardrail": "простота письма не лечит отсутствие допустимости или нормативного якоря",
                "skill_reference": "science-support-pack.md",
            },
        ],
    },
    {
        "canonical_name": "Ольга Николаевна Кряжкова",
        "role": "правовые позиции и amicus curiae",
        "aliases": ["Кряжкова О. Н.", "Кряжкова О.Н.", "Ольга Кряжкова"],
        "routes": ["interpretation_and_positions", "evidence_empirics_consequences", "institutional_design_and_legitimacy"],
        "full_text_sources": [
            "Кряжкова О. Н. Право быть услышанным: меморандумы amici curiae в российском КС РФ",
            "Дудко И. А., Кряжкова О. Н. Косвенный доступ граждан к конституционному правосудию в России",
        ],
        "method_cards": [
            {
                "method": "тест полезности amicus/expert material",
                "usable_for": "связь с предметом дела, научная добросовестность, уникальные факты или конструкции",
                "guardrail": "amicus не нейтрален по умолчанию, не гарантирует влияние и не заменяет первичный источник",
                "skill_reference": "strategic-complaint-design.md; science-support-pack.md",
            },
            {
                "method": "карта косвенного доступа через запрос суда",
                "usable_for": "проверка живого дела, надлежащего состава, применимости нормы, собственного вывода суда и роли ходатайства стороны",
                "guardrail": "ходатайство стороны не создаёт безусловного права на запрос; актуальные условия подтверждать по официальному праву",
                "skill_reference": "sko-complaint-methods-2017-2026.md; ksrf-court-request-motion",
            },
        ],
    },
    {
        "canonical_name": "Сергей Анатольевич Манжосов",
        "role": "конституционный прецедент",
        "aliases": ["Манжосов С. А.", "Манжосов С.А.", "Сергей Манжосов"],
        "routes": ["interpretation_and_positions", "institutional_design_and_legitimacy"],
        "full_text_sources": ["Манжосов С. А. Прецедент в конституционном праве: stare decisis и jurisprudence constante"],
        "method_cards": [
            {
                "method": "трёхосевой анализ прецедента",
                "usable_for": "разделение единичного/множественного субстрата, правила/результата и обязательной/убеждающей силы",
                "guardrail": "повторяемость исхода ещё не доказывает устойчивость юридического правила",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Сергей Сергеевич Заикин",
        "role": "граница КС РФ и сверхинстанционности",
        "aliases": ["Заикин С. С.", "Сергей Заикин"],
        "routes": ["admissibility_and_route", "institutional_design_and_legitimacy", "interpretation_and_positions"],
        "full_text_sources": ["Заикин С. С. Трансформация Конституционного Суда России в сверхинстанцию"],
        "method_cards": [
            {
                "method": "анти-сверхинстанционный фильтр",
                "usable_for": "проверка, нельзя ли разрешить вопрос обычным толкованием или межотраслевой связью",
                "guardrail": "жалоба должна показывать устойчивый нормативный смысл, а не ошибку применения в одном деле",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Дмитрий Геннадьевич Шустров",
        "role": "принципы конституционного толкования",
        "aliases": ["Шустров Д. Г.", "Шустров Д.Г.", "Дмитрий Шустров"],
        "routes": ["interpretation_and_positions", "certainty_communication_writing"],
        "full_text_sources": ["Шустров Д. Г. Принципы конституционного толкования"],
        "method_cards": [
            {
                "method": "чек-лист результата толкования",
                "usable_for": "пределы, порядок методов, конфликт результатов, определённость и практическая согласованность",
                "guardrail": "предлагаемый смысл должен оставаться в допустимых пределах текста и институциональной роли суда",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Mark van Hoecke",
        "role": "коммуникативная теория права",
        "aliases": ["Марк ван Хукке", "van Hoecke, Mark"],
        "routes": ["certainty_communication_writing", "interpretation_and_positions"],
        "full_text_sources": ["Mark van Hoecke. Law as Communication"],
        "method_cards": [
            {
                "method": "право как коммуникация",
                "usable_for": "анализ разрыва между текстом, адресатами, практикой и легитимным пониманием нормы",
                "guardrail": "теория объясняет механизм, но не заменяет российский нормативный якорь",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Светлана Юрьевна Филиппова",
        "role": "коммуникативный и инструментальный подход",
        "aliases": ["Филиппова С. Ю.", "Филиппова С.Ю."],
        "routes": ["certainty_communication_writing", "evidence_empirics_consequences"],
        "full_text_sources": ["Филиппова С. Ю. Коммуникативная теория права и инструментальный подход"],
        "method_cards": [
            {
                "method": "проверка поведенческого эффекта нормы",
                "usable_for": "связь правового текста с поведением адресатов и фактической реализацией гарантии",
                "guardrail": "инструментальный эффект должен подтверждаться, а не предполагаться",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Алексей Владимирович Асосков",
        "role": "логика нормативных коллизий",
        "aliases": ["Асосков А. В.", "Асосков А.В."],
        "routes": ["interpretation_and_positions", "identity_sovereignty_systems"],
        "full_text_sources": ["Асосков А. В. Коллизионное регулирование"],
        "method_cards": [
            {
                "method": "карта нормативной коллизии",
                "usable_for": "разделение конкурирующих привязок, императивных норм и публичного порядка",
                "guardrail": "использовать узко; частноправовая коллизионная доктрина не является конституционным тестом",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Дмитрий Дмитриевич Коновалов",
        "role": "конституционная ответственность государства",
        "aliases": ["Коновалов Д. Д.", "Коновалов Д.Д."],
        "routes": ["remedy_execution_review", "institutional_design_and_legitimacy"],
        "full_text_sources": ["Коновалов Д. Д. Конституционно-правовая ответственность в отношениях государства и личности"],
        "method_cards": [
            {
                "method": "ответственность как обязанность и accountability",
                "usable_for": "позитивная/негативная ответственность, доверие, статус и последствия нарушения",
                "guardrail": "до цитирования сверять точный тезис с авторефератом",
                "skill_reference": "science-support-pack.md",
            }
        ],
    },
    {
        "canonical_name": "Виктор Балакаев",
        "role": "конфигурация конституционно-судебных предписаний законодателю",
        "aliases": ["Балакаев В.", "В. Балакаев"],
        "routes": ["remedy_execution_review", "institutional_design_and_legitimacy", "interpretation_and_positions"],
        "full_text_sources": ["Балакаев В. Конституционно-судебные предписания законодателю: вопросы типологии"],
        "method_cards": [
            {
                "method": "матрица конфигурации предписания и срока",
                "usable_for": "выбор обязательности, объекта, степени определённости, альтернатив, временного правила, срока и переходного режима remedy",
                "guardrail": "не предлагать точный текст при нескольких допустимых решениях и не подменять законодателя",
                "skill_reference": "sko-complaint-methods-2017-2026.md; workflow-reference.md",
            }
        ],
    },
    {
        "canonical_name": "Елена Владимировна Гриценко",
        "role": "доступ к конституционному правосудию и институциональный фильтр",
        "aliases": ["Гриценко Е. В.", "Елена Гриценко"],
        "routes": ["admissibility_and_route", "comparative_and_international", "institutional_design_and_legitimacy"],
        "full_text_sources": ["Гриценко Е. В., Вилл Р. Доступ к конституционному правосудию в России и Германии"],
        "method_cards": [
            {
                "method": "разделение допустимости, отбора и устранимости дефекта",
                "usable_for": "red-team проверки hard gates, материальности недостатка, возможности исправления и единообразия фильтрации",
                "guardrail": "немецкие критерии не являются российским правом; действующие условия проверять официально",
                "skill_reference": "sko-complaint-methods-2017-2026.md; ksrf-case-triage",
            }
        ],
    },
    {
        "canonical_name": "Ирина Дудко",
        "role": "косвенный доступ и исполнение решений КС РФ",
        "aliases": ["Дудко И. А.", "Ирина Анатольевна Дудко"],
        "routes": ["admissibility_and_route", "remedy_execution_review", "institutional_design_and_legitimacy"],
        "full_text_sources": [
            "Дудко И. А., Кряжкова О. Н. Косвенный доступ граждан к конституционному правосудию в России",
            "Дудко И. А. «Нет ничего важнее мелочей», или Проблемы исполнения решений Конституционного Суда РФ",
        ],
        "method_cards": [
            {
                "method": "карта косвенного доступа через запрос суда",
                "usable_for": "живое дело, надлежащий состав, применимость нормы, собственный вывод суда и сохранение отказа",
                "guardrail": "не смешивать ходатайство стороны, запрос суда и прямую жалобу",
                "skill_reference": "sko-complaint-methods-2017-2026.md; ksrf-court-request-motion",
            },
            {
                "method": "многослойный аудит исполнения",
                "usable_for": "текст, аналогичные нормы, переходный режим, практику, индивидуальное восстановление и специальную компенсацию",
                "guardrail": "не обещать автоматический пересмотр и не превращать специальную компенсацию в обычный деликт",
                "skill_reference": "sko-complaint-methods-2017-2026.md; ksrf-decision-execution",
            },
        ],
    },
    {
        "canonical_name": "Алексей Нечаев",
        "role": "граница истолкования и скрытого правотворчества",
        "aliases": ["Нечаев А. Д.", "Алексей Дмитриевич Нечаев"],
        "routes": ["interpretation_and_positions", "certainty_communication_writing", "remedy_execution_review"],
        "full_text_sources": ["Нечаев А. Д. Конституционность положений нормативного акта в истолковании Конституционного Суда России"],
        "method_cards": [
            {
                "method": "downstream simulation конституционного истолкования",
                "usable_for": "проверка добавленных признаков, внутренних противоречий, конкуренции норм и предсказуемости нового смысла",
                "guardrail": "отраслевая критика одного решения является stress-test, а не самостоятельным доказательством неконституционности",
                "skill_reference": "sko-complaint-methods-2017-2026.md; constitutional-review-methods.md",
            }
        ],
    },
    {
        "canonical_name": "Анна Васильева",
        "role": "обоснованность публичных решений",
        "aliases": ["Васильева А. Ф.", "Анна Федотовна Васильева"],
        "routes": ["evidence_empirics_consequences", "certainty_communication_writing", "proportionality_equality_dignity"],
        "full_text_sources": ["Должиков А. В., Васильева А. Ф. «Почему? По кочану!»: принцип обоснованности в административном праве"],
        "method_cards": [
            {
                "method": "трёхуровневый тест обоснованности публичного решения",
                "usable_for": "письменные основания, право быть услышанным, законная цель, доказательства и релевантные факторы",
                "guardrail": "не подменять орган управления и не превращать проверку обоснованности в проверку целесообразности",
                "skill_reference": "sko-complaint-methods-2017-2026.md; workflow-reference.md",
            }
        ],
    },
]


BLOKHIN_EXTRA_AUTHORS = {
    403: ["Сурен Адибекович Авакьян"],
    476: ["Борис Николаевич Топорнин"],
    479: ["Елена Владимировна Гриценко", "Р. Вилл"],
    480: ["Рене Давид"],
    498: ["Анатолий Иванович Ковлер"],
    512: ["Рудольф фон Иеринг"],
    541: ["Гадис Абдуллаевич Гаджиев"],
    542: ["Андрей Владимирович Ильин"],
    543: ["Николай Васильевич Витрук"],
    544: ["Андраш Шайо"],
    545: ["Владимир Васильевич Маклаков"],
    547: ["Моше Коэн-Элия", "Иддо Порат"],
    570: ["Александр Иванович Мигунов", "Илья Борисович Микиртумов", "Борис Иванович Федоров"],
    583: ["Кай Мёллер"],
    584: ["Джон Стюарт Милль"],
    588: ["Джон Монтгомери"],
    602: ["Владимир Павлович Кохановский"],
    634: ["Елена Владимировна Тимошина"],
    635: ["Николай Семёнович Бондарь"],
    636: ["Валерий Васильевич Лазарев", "Ханлар Иршадович Гаджиев"],
    649: ["Виктор Осипович Лучин"],
    653: ["Александр Гамильтон", "Джеймс Мэдисон", "Джон Джей"],
    663: ["Ян Хельгесен"],
    673: ["Гадис Абдуллаевич Гаджиев"],
    678: ["Raimo Siltala"],
    692: ["Tom Ginsburg", "Rosalind Dixon"],
    699: ["Lourens du Plessis"],
    714: ["Wolfgang Heyde"],
    720: ["R. Bakker", "A. W. Heringa", "F. Stroink"],
    758: ["Donald P. Kommers", "Russell A. Miller"],
    759: ["Michel Rosenfeld", "András Sajó"],
    762: ["Anne van Aaken"],
    773: ["Mathias Hong"],
    774: ["Mathias Hong"],
    775: ["Hans D. Jarass", "Bodo Pieroth"],
}


STOPWORDS = {
    "press", "university", "publishing", "publishers", "институт", "издательство",
    "юристъ", "наука", "росспэн", "клувер", "формула", "центр", "правовой", "обзор",
    "редактор", "редакторы", "администрация", "репортаж", "перераб", "доп", "учебное",
    "пособие", "application", "judgment", "edition", "edited", "by", "cambridge", "harvard",
    "yale", "random", "house", "times", "book", "basic", "wolters", "конституционный", "международный", "суде", "суда",
    "право", "россии", "европе", "constitution", "constitutionalism", "volume",
    "австралия", "австрия", "армения", "бразилия", "германия", "израиль", "индия",
    "россия", "румыния", "сша", "турция", "испания", "колумбия", "польша", "швейцария",
    "япония", "белоруссия", "таиланд", "туркменистан", "украина", "болгария", "греция",
    "египет", "италия", "словакия", "словения", "хорватия", "иран", "ирландия", "мальта",
    "франция", "юар", "корея", "албания", "чехия", "македония", "норвегия", "эквадор",
    "великобритания", "кипр", "канада", "казахстан", "кыргызстан", "netherlands", "academic",
}

PARTICLES = {"van", "von", "de", "den", "del", "der", "la", "le", "da", "di", "du", "дель", "де", "ван", "фон", "аль"}
PATRONYMIC_RE = re.compile(r"(?:ович|евич|ич|овна|евна|ична|инична)$", re.I)

# High-value cross-script aliases that cannot be joined by Cyrillic/Latin
# surname keys alone.  This is deliberately short and reviewable; the JSON
# still flags the remaining transliteration candidates for manual identity QA.
IDENTITY_OVERRIDE_GROUPS = [
    ("алекси|р", {"Алекси Р.", "Роберт Алекси", "Alexy, Robert", "Robert Alexy"}),
    ("меллер|к", {"Мёллер К.", "Кай Мёллер", "Möller, Kai", "Kai Möller"}),
    ("кумм|м", {"Маттиас Кумм", "Kumm, Mattias", "Mattias Kumm"}),
    ("санстейн|к", {"Касс Санстейн", "Sunstein, Cass R.", "Cass R. Sunstein"}),
    ("джексон|в", {"Вики С. Джексон", "Jackson, Vicky C.", "Vicky C. Jackson"}),
    ("дворкин|р", {"Дворкин Р.", "Рональд Дворкин", "Dworkin, Ronald", "Ronald Dworkin"}),
    ("люббевольф|г", {"Гертруда Люббе-Вольф", "Гертруда Люббе-Вольфф", "Lübbe-Wolff, Gertrude", "Gertrude Lübbe-Wolff"}),
    ("шайо|а", {"Андраш Шайо", "Sajó, András", "András Sajó"}),
]

IDENTITY_CANONICAL_NAMES = {
    "алекси|р": "Роберт Алекси",
    "меллер|к": "Кай Мёллер",
    "кумм|м": "Маттиас Кумм",
    "санстейн|к": "Касс Санстейн",
    "джексон|в": "Вики С. Джексон",
    "дворкин|р": "Рональд Дворкин",
    "люббевольф|г": "Гертруда Люббе-Вольф",
    "шайо|а": "Андраш Шайо",
    "хабриева|т": "Талия Ярулловна Хабриева",
    "тарибо|е": "Евгений Всеволодович Тарибо",
    "кельзен|г": "Ганс Кельзен",
    "barak|a": "Аарон Барак",
}

MANUAL_ACADEMIC_LEADS = [
    {
        "name": "Aharon Barak",
        "source_kind": "sko_index",
        "source_order": "given_family",
        "title": "Aharon Barak. The Judge in a Democracy (рецензируемая книга в указателе СКО)",
        "confidence": 0.9,
    }
]

@dataclass
class Occurrence:
    raw_name: str
    source_kind: str
    source_order: str
    work: dict | None = None
    confidence: float = 1.0


@dataclass
class Authority:
    key: str
    canonical_name: str
    display_score: int = 0
    aliases: set[str] = field(default_factory=set)
    source_counts: Counter = field(default_factory=Counter)
    works: dict[str, dict] = field(default_factory=dict)
    routes: set[str] = field(default_factory=set)
    method_cards: list[dict] = field(default_factory=list)
    full_text_sources: list[str] = field(default_factory=list)
    roles: set[str] = field(default_factory=set)
    confidence_values: list[float] = field(default_factory=list)


def fold(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("ё", "е").replace("Ё", "Е")
    value = re.sub(r"[^0-9A-Za-zА-Яа-я]+", "", value.lower())
    return value


def clean_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("C т", "Ст")
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\b(Дж|[A-ZА-ЯЁ])\s*\.\s*", r"\1. ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.replace(" ,", ",").strip(" ,;.\n\t")
    return value


def clean_author_line(value: str) -> str:
    """Normalize an index author line while preserving a trailing comma.

    The official indexes use a trailing comma when a multi-author line wraps.
    Removing it would merge the last author on the first baseline with the
    first author on the continuation baseline.
    """
    value = unicodedata.normalize("NFKC", value).replace("C т", "Ст")
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\b(Дж|[A-ZА-ЯЁ])\s*\.\s*", r"\1. ", value)
    value = re.sub(r"\s+", " ", value)
    return value.replace(" ,", ",").strip(" ;\n\t")


def personish(value: str) -> str | None:
    value = clean_name(value)
    if len(value) < 3 or len(value) > 100 or re.search(r"[\d():\"«»/]", value):
        return None
    tokens = [token.strip(",.") for token in value.split() if token.strip(",.")]
    if not 2 <= len(tokens) <= 6:
        return None
    if {token.lower() for token in tokens} & STOPWORDS:
        return None
    word = re.compile(r"^[A-ZА-ЯЁ][A-Za-zА-Яа-яЁёÀ-ÖØ-öø-ÿŚśńŃ'’\-]+$")
    initial = re.compile(r"^[A-ZА-ЯЁ]\.?$")
    for token in tokens:
        if token.lower() in PARTICLES:
            continue
        if not (word.match(token) or initial.match(token)):
            return None
    return value


def name_parts(value: str, source_order: str) -> tuple[str, str, list[str]]:
    value = clean_name(value)
    if "," in value and source_order == "family_comma_given":
        family, rest = value.split(",", 1)
        given_tokens = rest.strip().split()
        return family.strip(), given_tokens[0] if given_tokens else "", given_tokens[1:]

    tokens = value.replace(",", " ").split()
    if not tokens:
        return value, "", []
    if (
        source_order == "given_family"
        and len(tokens) == 3
        and PATRONYMIC_RE.search(tokens[-1])
        and not PATRONYMIC_RE.search(tokens[1])
    ):
        # Some later Russian indexes use ``Family Given Patronymic`` even
        # though most SKO/Zakon records use ``Given Family``.
        return tokens[0], tokens[1], tokens[2:]
    if source_order in {"family_given", "family_initials"}:
        if tokens[0].lower() in PARTICLES and len(tokens) >= 3:
            family = " ".join(tokens[:2])
            rest = tokens[2:]
        else:
            family, rest = tokens[0], tokens[1:]
        return family, rest[0] if rest else "", rest[1:]

    # SKO, Zakon and curated names are normally given-name first.
    if len(tokens) >= 3 and tokens[-2].lower() in PARTICLES:
        family = " ".join(tokens[-2:])
        rest = tokens[:-2]
    else:
        family, rest = tokens[-1], tokens[:-1]
    return family, rest[0] if rest else "", rest[1:]


def identity_key(value: str, source_order: str) -> str:
    normalized = fold(value)
    for target, aliases in IDENTITY_OVERRIDE_GROUPS:
        if normalized in {fold(alias) for alias in aliases}:
            return target
    family, given, _ = name_parts(value, source_order)
    initial = fold(given)[:1] or "_"
    return f"{fold(family)}|{initial}"


def display_name(value: str, source_order: str) -> str:
    family, given, rest = name_parts(value, source_order)
    if source_order in {"family_given", "family_initials", "family_comma_given"} and given:
        return clean_name(" ".join([given, *rest, family]))
    return clean_name(value.replace(",", ""))


def display_score(value: str, source_kind: str) -> int:
    score = {"curated_method": 100, "mp_index": 70, "local_full_text": 90, "sko_index": 60, "zakon_discovery": 50, "blokhin_bibliography": 40}.get(source_kind, 0)
    if not re.search(r"[A-ZА-ЯЁ]\.", value):
        score += min(len(value.split()), 4) * 3
    if len(value.split()) == 3:
        score += 20
    return score


def resolve_source_order(authorities: dict[str, Authority], occurrence: Occurrence) -> str:
    order = occurrence.source_order
    if order != "given_family":
        return order
    tokens = clean_name(occurrence.raw_name).replace(",", " ").split()
    if len(tokens) == 3 and PATRONYMIC_RE.search(tokens[-1]) and not PATRONYMIC_RE.search(tokens[1]):
        return "family_given"
    if len(tokens) == 2:
        known_families = {key.split("|", 1)[0] for key in authorities}
        first, second = fold(tokens[0]), fold(tokens[1])
        if first in known_families and second not in known_families:
            return "family_given"
    return order


def infer_routes(text: str) -> set[str]:
    normalized = text.lower().replace("ё", "е")
    return {route for route, (pattern, _) in ROUTE_RULES.items() if re.search(pattern, normalized, re.I)}


def parse_numbered_bibliography(path: Path) -> dict[int, str]:
    if path.suffix.lower() == ".pdf":
        if not shutil.which("pdftotext"):
            raise RuntimeError("pdftotext is required to parse Blokhin's dissertation PDF")
        completed = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True)
        source_text = completed.stdout.decode("utf-8", errors="ignore")
    else:
        source_text = path.read_text(encoding="utf-8", errors="ignore")
    entries: dict[int, str] = {}
    current: int | None = None
    for raw in source_text.splitlines():
        line = raw.strip()
        if not line or line.isdigit():
            continue
        match = re.match(r"^(\d{1,3})\.\s+(.*)$", line)
        if match:
            current = int(match.group(1))
            entries[current] = match.group(2)
        elif current is not None:
            entries[current] += " " + line
    return {number: re.sub(r"\s+", " ", value) for number, value in entries.items() if 386 <= number <= 777}


def blokhin_leading_authors(entry: str, number: int) -> list[tuple[str, str]]:
    authors: list[tuple[str, str]] = []
    ru = r"[А-ЯЁ][А-Яа-яЁёѐA-Za-z\-]+(?:,)?\s+[А-ЯЁ]\.(?:\s*[А-ЯЁ]\.)?"
    ru_list = re.compile(rf"^({ru}(?:(?:\s*,\s*|\s+и\s+){ru})*)")
    ru_inverse = r"[А-ЯЁ][А-Яа-яЁёѐ\-]+,\s*[А-ЯЁ]\.(?:\s*[А-ЯЁ]\.)?"
    ru_inverse_list = re.compile(rf"^({ru_inverse}(?:\s*,\s*{ru_inverse})*)")
    en = r"(?:van\s+|du\s+|de\s+)?[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+,\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+[A-Z]\.)?"
    en_list = re.compile(rf"^({en}(?:(?:\s*,?\s+and\s+|\s*&\s*){en})*)")

    match = ru_list.match(entry)
    if match:
        for candidate in re.findall(ru, match.group(1)):
            authors.append((clean_name(candidate.replace(",", "")), "family_initials"))
    else:
        match = ru_inverse_list.match(entry)
        if match:
            for candidate in re.findall(ru_inverse, match.group(1)):
                authors.append((clean_name(candidate.replace(",", "")), "family_initials"))
        else:
            match = en_list.match(entry)
            if match:
                for candidate in re.findall(en, match.group(1)):
                    authors.append((clean_name(candidate), "family_comma_given"))

    for candidate in BLOKHIN_EXTRA_AUTHORS.get(number, []):
        authors.append((candidate, "given_family"))
    # Stable de-duplication within one bibliography item.
    unique = {}
    for name, order in authors:
        unique[(fold(name), order)] = (name, order)
    return list(unique.values())


def xml_article_records(path: Path, source_kind: str) -> list[tuple[list[str], str, float]]:
    if not shutil.which("pdftohtml"):
        raise RuntimeError("pdftohtml is required to parse official journal indexes")
    completed = subprocess.run(["pdftohtml", "-xml", "-stdout", str(path)], check=True, capture_output=True)
    root = ET.fromstring(completed.stdout)
    column_limit = 420 if source_kind == "sko_index" else 480
    max_gap = 75 if source_kind == "sko_index" else 65
    confidence = 0.78 if source_kind == "sko_index" else 0.9
    records: list[tuple[list[str], str, float]] = []

    for page in root.findall("page"):
        rows: dict[int, list[tuple[int, str, bool, bool, str]]] = defaultdict(list)
        for element in page.findall("text"):
            left = int(element.get("left", "9999"))
            if left >= column_limit:
                continue
            top = int(element.get("top", "0"))
            text = "".join(element.itertext()).replace("\xa0", " ")
            rows[top].append((left, text, element.find(".//i") is not None, element.find(".//b") is not None, element.get("font", "")))

        pending_title: list[str] = []
        last_bold_top: int | None = None
        last_record: int | None = None
        last_author_top: int | None = None

        for top, nodes in sorted(rows.items()):
            nodes.sort()
            has_author_font = any(italic and not bold and font in {"1", "2"} for _, _, italic, bold, font in nodes)
            if has_author_font:
                pieces = [
                    text
                    for _, text, italic, bold, font in nodes
                    if (italic and not bold and font in {"1", "2"}) or (not bold and re.fullmatch(r"[\s,;]+", text or ""))
                ]
                author_line = clean_author_line(" ".join(pieces).replace(" ,", ","))
                if pending_title and last_bold_top is not None and top - last_bold_top <= max_gap:
                    records.append(([], " ".join(pending_title), confidence))
                    last_record = len(records) - 1
                    last_author_top = top
                    pending_title = []
                    last_bold_top = None
                    records[last_record][0].append(author_line)  # type: ignore[index]
                elif (
                    last_record is not None
                    and last_author_top is not None
                    and top - last_author_top <= 20
                    and (records[last_record][0][-1].endswith(",") or personish(author_line))
                ):
                    records[last_record][0][-1] = clean_author_line(records[last_record][0][-1] + " " + author_line)  # type: ignore[index]
                    last_author_top = top
                continue

            bold_text = " ".join(
                text for _, text, italic, bold, font in nodes if bold and not italic and font in {"0", "4"}
            )
            bold_text = re.sub(r"\s+", " ", bold_text).strip()
            if bold_text and not re.search(
                r"Название и автор|Номер выпуска|Страница|Перечень статей|с №|^(?:КПВО|СКО|МП|Международное правосудие)\s*№",
                bold_text,
                re.I,
            ):
                if last_bold_top is None or top - last_bold_top <= 24:
                    pending_title.append(bold_text)
                else:
                    pending_title = [bold_text]
                pending_title = pending_title[-6:]
                last_bold_top = top
                last_record = None
                last_author_top = None

    # Older SKO index pages occasionally lose a comma between two authors on
    # a wrapped line.  Infer only the conservative ``Given Family`` pairs for
    # which every prospective given name is also seen in a clean two-token
    # author record.  Four-token Spanish/Portuguese names therefore stay whole.
    clear_sko_given = {
        clean_name(segment).split()[0]
        for raw_lines, _, _ in records
        for raw_line in raw_lines
        for segment in re.split(r"\s*[,;]\s*", raw_line)
        if source_kind == "sko_index"
        and personish(segment)
        and len(clean_name(segment).split()) == 2
    }
    clear_sko_given.update({"Рути", "Роже", "Димитр", "Елена", "Ирина", "Михаил", "Ольга", "Татьяна", "Жанна", "Анаит", "Алим", "Шломо", "Джордж", "Ульрих"})

    parsed: list[tuple[list[str], str, float]] = []
    for raw_lines, title, record_confidence in records:
        names: list[str] = []
        for raw_line in raw_lines:
            for segment in re.split(r"\s*[,;]\s*", raw_line):
                candidate = personish(segment)
                if candidate:
                    tokens = candidate.split()
                    if (
                        source_kind == "sko_index"
                        and len(tokens) in {4, 6}
                        and not any("." in token for token in tokens)
                        and all(tokens[index] in clear_sko_given for index in range(0, len(tokens), 2))
                    ):
                        names.extend(" ".join(tokens[index:index + 2]) for index in range(0, len(tokens), 2))
                    elif (
                        source_kind == "mp_index"
                        and len(tokens) in {6, 9}
                        and all(re.search(r"(?:вич|вна|ична|ич)$", tokens[index], re.I) for index in range(2, len(tokens), 3))
                    ):
                        names.extend(" ".join(tokens[index:index + 3]) for index in range(0, len(tokens), 3))
                    else:
                        names.append(candidate)
        if names:
            parsed.append((names, clean_name(title), record_confidence))
    return parsed


def load_zakon(path: Path) -> list[Occurrence]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    occurrences = []
    for item in payload:
        author = personish(str(item.get("author") or ""))
        if not author:
            continue
        work = {
            "title": clean_name(str(item.get("title") or "Без названия")),
            "source": "zakon_discovery",
            "url": item.get("url"),
            "publication_type": item.get("type"),
            "date": item.get("date"),
            "discovery_score": item.get("score"),
        }
        occurrences.append(Occurrence(author, "zakon_discovery", "given_family", work, 0.55))
    return occurrences


def occurrence_stream(args: argparse.Namespace) -> Iterable[Occurrence]:
    for item in CURATED:
        work = {
            "title": item["full_text_sources"][0],
            "source": "curated_method",
            "method_integrated": True,
        }
        yield Occurrence(item["canonical_name"], "curated_method", "given_family", work, 1.0)

    for item in MANUAL_ACADEMIC_LEADS:
        yield Occurrence(
            item["name"],
            item["source_kind"],
            item["source_order"],
            {"title": item["title"], "source": item["source_kind"], "manually_recovered_from_index": True},
            item["confidence"],
        )

    for number, entry in parse_numbered_bibliography(args.blokhin_source).items():
        for author, order in blokhin_leading_authors(entry, number):
            yield Occurrence(
                author,
                "blokhin_bibliography",
                order,
                {"title": entry, "source": "blokhin_bibliography", "bibliography_entry": number},
                0.92,
            )

    for source_kind, path in (("sko_index", args.sko_index_pdf), ("mp_index", args.mp_index_pdf)):
        order = "given_family" if source_kind == "sko_index" else "family_given"
        for authors, title, confidence in xml_article_records(path, source_kind):
            for author in authors:
                yield Occurrence(
                    author,
                    source_kind,
                    order,
                    {"title": title, "source": source_kind},
                    confidence,
                )

    yield from load_zakon(args.zakon_json)


def add_occurrence(authorities: dict[str, Authority], occurrence: Occurrence) -> None:
    source_order = resolve_source_order(authorities, occurrence)
    key = identity_key(occurrence.raw_name, source_order)
    shown = display_name(occurrence.raw_name, source_order)
    score = display_score(shown, occurrence.source_kind)
    authority = authorities.get(key)
    if authority is None:
        authority = Authority(key=key, canonical_name=shown, display_score=score)
        authorities[key] = authority
    elif score > authority.display_score:
        authority.canonical_name = shown
        authority.display_score = score

    authority.aliases.add(clean_name(occurrence.raw_name))
    authority.source_counts[occurrence.source_kind] += 1
    authority.confidence_values.append(occurrence.confidence)
    if occurrence.work:
        work = {key: value for key, value in occurrence.work.items() if value not in (None, "")}
        work_key = hashlib.sha1(f"{work.get('source')}|{fold(str(work.get('title')))}".encode("utf-8")).hexdigest()[:16]
        authority.works[work_key] = work
        authority.routes.update(infer_routes(str(work.get("title", ""))))


def merge_authority(target: Authority, source: Authority) -> None:
    if source.display_score > target.display_score:
        target.canonical_name = source.canonical_name
        target.display_score = source.display_score
    target.aliases.update(source.aliases)
    target.source_counts.update(source.source_counts)
    target.works.update(source.works)
    target.routes.update(source.routes)
    target.method_cards.extend(source.method_cards)
    target.full_text_sources.extend(source.full_text_sources)
    target.roles.update(source.roles)
    target.confidence_values.extend(source.confidence_values)


def merge_reverse_two_token_names(authorities: dict[str, Authority]) -> None:
    """Merge exact ``Given Family`` / ``Family Given`` reversals."""
    by_tokens: dict[tuple[str, str], str] = {}
    for key, authority in list(authorities.items()):
        tokens = clean_name(authority.canonical_name).split()
        if len(tokens) != 2 or any("." in token for token in tokens):
            continue
        pair = (fold(tokens[0]), fold(tokens[1]))
        reverse_key = by_tokens.get((pair[1], pair[0]))
        if reverse_key and reverse_key in authorities and reverse_key != key:
            target = authorities[reverse_key]
            merge_authority(target, authority)
            del authorities[key]
        else:
            by_tokens[pair] = key


def apply_identity_canonical_names(authorities: dict[str, Authority]) -> None:
    for key, canonical_name in IDENTITY_CANONICAL_NAMES.items():
        if key in authorities:
            authorities[key].aliases.add(authorities[key].canonical_name)
            authorities[key].canonical_name = canonical_name
            authorities[key].display_score = max(authorities[key].display_score, 500)


def apply_curated(authorities: dict[str, Authority]) -> None:
    for item in CURATED:
        key = identity_key(item["canonical_name"], "given_family")
        authority = authorities[key]
        authority.canonical_name = item["canonical_name"]
        authority.display_score = 1000
        authority.aliases.update(item.get("aliases", []))
        authority.routes.update(item.get("routes", []))
        authority.method_cards.extend(item.get("method_cards", []))
        authority.full_text_sources.extend(item.get("full_text_sources", []))
        authority.roles.add(item["role"])
        authority.source_counts["local_full_text"] += len(item.get("full_text_sources", []))


def authority_status(authority: Authority) -> str:
    if authority.method_cards:
        return "method_integrated"
    if authority.full_text_sources:
        return "full_text_available"
    academic = {source for source in authority.source_counts if source in {"blokhin_bibliography", "sko_index", "mp_index"}}
    if len(academic) >= 2:
        return "triangulated_academic"
    if academic & {"sko_index", "mp_index"}:
        return "academic_indexed"
    if "blokhin_bibliography" in academic:
        return "bibliographic_lead"
    return "discovery_only"


def serialize(authorities: dict[str, Authority], as_of: str) -> dict:
    rows = []
    for authority in authorities.values():
        status = authority_status(authority)
        authoritative_sources = [
            source for source in authority.source_counts if source not in {"zakon_discovery", "curated_method", "local_full_text"}
        ]
        average_confidence = sum(authority.confidence_values) / max(len(authority.confidence_values), 1)
        needs_review = status in {"academic_indexed", "discovery_only"} and len(authoritative_sources) < 2
        row_id = "authority-" + hashlib.sha1(authority.key.encode("utf-8")).hexdigest()[:12]
        rows.append(
            {
                "id": row_id,
                "identity_key": authority.key,
                "canonical_name": authority.canonical_name,
                "aliases": sorted({alias for alias in authority.aliases if fold(alias) != fold(authority.canonical_name)}),
                "roles": sorted(authority.roles),
                "status": status,
                "status_label": STATUS_LABELS[status],
                "method_integrated": bool(authority.method_cards),
                "needs_identity_or_method_review": needs_review,
                "parser_confidence": round(average_confidence, 3),
                "routes": sorted(authority.routes),
                "source_counts": dict(sorted(authority.source_counts.items())),
                "full_text_sources": authority.full_text_sources,
                "method_cards": authority.method_cards,
                "works": sorted(authority.works.values(), key=lambda item: (str(item.get("source")), str(item.get("title")))),
            }
        )

    rows.sort(key=lambda item: (STATUS_ORDER[item["status"]], fold(item["canonical_name"])))
    status_counts = Counter(row["status"] for row in rows)
    route_counts = Counter(route for row in rows for route in row["routes"])
    source_people = Counter()
    for row in rows:
        for source in row["source_counts"]:
            source_people[source] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "purpose": "широкий маршрутизируемый корпус авторов для исследования, извлечения методик и QA жалоб в КС РФ",
        "warning": "Присутствие в реестре не превращает доктрину в право. Discovery-only записи нельзя цитировать как авторитет без проверки автора и работы.",
        "status_legend": STATUS_LABELS,
        "route_legend": {route: label for route, (_, label) in ROUTE_RULES.items()},
        "sources": [
            {
                "kind": "blokhin_bibliography",
                "label": SOURCE_LABELS["blokhin_bibliography"],
                "coverage": "диссертации и научные работы, библиографические позиции 386–777",
            },
            {
                "kind": "sko_index",
                "label": SOURCE_LABELS["sko_index"],
                "coverage": "№ 1(1) 1992 — № 1(166) 2026",
                "url": "https://sko-journal.ru/wp-content/uploads/2026/05/Perechen_statej_KPVO_SKO_1992_2026_1_04052026.pdf",
            },
            {
                "kind": "mp_index",
                "label": SOURCE_LABELS["mp_index"],
                "coverage": "№ 1(1) 2011 — № 1(57) 2026",
            },
            {
                "kind": "zakon_discovery",
                "label": SOURCE_LABELS["zakon_discovery"],
                "coverage": "локальные материалы по конституционному праву; блоги и дискуссии",
            },
            {
                "kind": "curated_method",
                "label": SOURCE_LABELS["curated_method"],
                "coverage": "проверенные локальные полные тексты и уже встроенные методические карточки",
            },
        ],
        "summary": {
            "authorities_total": len(rows),
            "status_counts": dict(sorted(status_counts.items(), key=lambda item: STATUS_ORDER[item[0]])),
            "source_people_counts": dict(sorted(source_people.items())),
            "route_counts": dict(sorted(route_counts.items())),
            "works_total": sum(len(row["works"]) for row in rows),
            "needs_review_total": sum(bool(row["needs_identity_or_method_review"]) for row in rows),
        },
        "authorities": rows,
    }


def render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Корпус авторитетов по конституционному праву и правосудию",
        "",
        f"Срез на `{payload['as_of']}`. Реестр охватывает **{summary['authorities_total']}** нормализованных записей и **{summary['works_total']}** привязок к работам.",
        "",
        "Это карта поиска и извлечения методологии, а не рейтинг учёных и не самостоятельный источник права. Конституция РФ, официальный акт КС РФ, применённая норма и материалы дела всегда имеют приоритет. Запись уровня `discovery_only` нельзя называть авторитетом без проверки личности, публикации и тезиса.",
        "",
        "## Содержание",
        "",
        "- [Проверенные методические карточки](#проверенные-методические-карточки)",
        "- [Как пользоваться](#как-пользоваться)",
        "- [Уровни готовности](#уровни-готовности)",
        "- [Уже внедрённые методологи](#уже-внедрённые-методологи)",
        "- [Маршруты исследования](#маршруты-исследования)",
        "- [Правила доверия](#правила-доверия)",
        "- [Полный алфавитный реестр](#полный-алфавитный-реестр)",
        "",
        "## Проверенные методические карточки",
        "",
        f"Статусы этого реестра — срез сборщика на `{payload['as_of']}` и не отражают все последующие проверки.",
        "",
        "В [реестре проверенных карточек](constitutional-methodology-verified-cards.md) находятся 19 карточек до этапа внедрения; шесть возможных изменений поведения остаются только кандидатами до автоматической оценки и явного одобрения человеком. В [сравнительном и red-team корпусе](constitutional-methodology-reference-only-corpus.md) находятся 84 карточки с проверенными источниками и правовыми границами — для генерации вариантов, контрпримеров, вопросов проверки и пределов переноса. Ни одна из двух коллекций не разрешает перевод в обязательные правила; правовая проверка зафиксирована на `law_as_of=2026-08-14`, поэтому актуальные официальные источники нужно перепроверять.",
        "",
        "## Как пользоваться",
        "",
        "1. Определи исследовательский маршрут по проблеме жалобы.",
        "2. Сначала открой записи `method_integrated`, затем `full_text_available` и `triangulated_academic`.",
        "3. Для выбранного автора открой работу из JSON, извлеки точный тезис и зафиксируй страницу/раздел.",
        "4. Отдельно проверь, что тезис переносим в российский нормативный контекст и не подменяет официальную позицию КС РФ.",
        "5. Сохрани контраргумент и предел метода; в финальный текст включай только источник, меняющий анализ.",
        "",
        "## Уровни готовности",
        "",
        "| Статус | Число | Значение |",
        "| --- | ---: | --- |",
    ]
    for status in STATUS_ORDER:
        lines.append(f"| `{status}` | {summary['status_counts'].get(status, 0)} | {STATUS_LABELS[status]} |")

    lines.extend(["", "## Уже внедрённые методологи", "", "| Автор | Роль | Рабочие методы | Предохранитель |", "| --- | --- | --- | --- |"])
    for row in payload["authorities"]:
        if row["status"] != "method_integrated":
            continue
        methods = "; ".join(card["method"] for card in row["method_cards"])
        guardrails = "; ".join(card["guardrail"] for card in row["method_cards"])
        role = "; ".join(row["roles"])
        lines.append(f"| {row['canonical_name']} | {role} | {methods} | {guardrails} |")

    lines.extend(["", "## Маршруты исследования", "", "| Маршрут | Что искать | Авторов с совпадением |", "| --- | --- | ---: |"])
    for route, (_, description) in ROUTE_RULES.items():
        lines.append(f"| `{route}` | {description} | {summary['route_counts'].get(route, 0)} |")

    lines.extend(
        [
            "",
            "## Правила доверия",
            "",
            "- `method_integrated` означает, что из полного текста извлечена операционная карточка с предохранителем; это не обещание принятия жалобы.",
            "- `full_text_available` требует отдельного извлечения метода перед внедрением.",
            "- `triangulated_academic` подтверждает устойчивый академический след, но не конкретный тезис.",
            "- `academic_indexed` и `bibliographic_lead` служат маршрутом к публикации.",
            "- `discovery_only` — только lead из блога/дискуссии. Его нельзя цитировать как доктрину без внешней проверки.",
            "- Автоматическая нормализация по фамилии и первой букве имени может склеить однофамильцев или оставить транслитерационные дубли; записи с флагом `needs_identity_or_method_review` требуют ручной сверки.",
            "",
            "## Полный алфавитный реестр",
            "",
            "Детальные работы, URL, алиасы, счётчики источников и методические карточки находятся в `constitutionalist-authority-corpus.json`.",
            "",
        ]
    )

    alphabetical = sorted(payload["authorities"], key=lambda row: fold(row["canonical_name"]))
    current_letter = None
    for row in alphabetical:
        letter = row["canonical_name"][:1].upper() or "#"
        if letter != current_letter:
            lines.extend([f"### {letter}", ""])
            current_letter = letter
        sources = ", ".join(sorted(row["source_counts"]))
        routes = ", ".join(row["routes"][:4]) or "маршрут ещё не размечен"
        review = "; нужна ручная сверка" if row["needs_identity_or_method_review"] else ""
        lines.append(f"- **{row['canonical_name']}** — `{row['status']}`; {routes}; источники: {sources}; работ: {len(row['works'])}{review}.")
    lines.append("")
    return "\n".join(lines)


def validate(payload: dict) -> None:
    assert payload["schema_version"] == SCHEMA_VERSION
    assert "next_extraction_wave" not in payload
    assert all("local_source_hint" not in source for source in payload["sources"])
    assert "ТЗ/" not in json.dumps(payload, ensure_ascii=False)
    names = [row["canonical_name"] for row in payload["authorities"]]
    assert len(names) == len(set(names)), "canonical names must be unique"
    assert all(row["status"] in STATUS_ORDER for row in payload["authorities"])
    assert all(row["source_counts"] for row in payload["authorities"])
    assert sum(payload["summary"]["status_counts"].values()) == len(names)
    assert any(row["canonical_name"] == "Павел Дмитриевич Блохин" and row["method_integrated"] for row in payload["authorities"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    blokhin = parser.add_mutually_exclusive_group(required=True)
    blokhin.add_argument("--blokhin-text", type=Path)
    blokhin.add_argument("--blokhin-pdf", type=Path)
    parser.add_argument("--sko-index-pdf", type=Path, required=True)
    parser.add_argument("--mp-index-pdf", type=Path, required=True)
    parser.add_argument("--zakon-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args()
    args.blokhin_source = args.blokhin_text or args.blokhin_pdf
    return args


def main() -> None:
    args = parse_args()
    for path in (args.blokhin_source, args.sko_index_pdf, args.mp_index_pdf, args.zakon_json):
        if not path.is_file():
            raise FileNotFoundError(path)

    authorities: dict[str, Authority] = {}
    for occurrence in occurrence_stream(args):
        add_occurrence(authorities, occurrence)
    merge_reverse_two_token_names(authorities)
    apply_identity_canonical_names(authorities)
    apply_curated(authorities)
    payload = serialize(authorities, args.as_of)
    validate(payload)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

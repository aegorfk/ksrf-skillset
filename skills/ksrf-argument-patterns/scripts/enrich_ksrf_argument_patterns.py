#!/usr/bin/env python3
"""Сгенерировать справочники обогащения для паттернов аргументации КС РФ."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


DEFAULT_SKILL = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PatternEnrichment:
    code: str
    title: str
    articles: List[str]
    norm_types: List[str]
    harm_types: List[str]
    primary_when: str
    proof_tasks: List[str]
    evidence: List[str]
    falsifiers: List[str]
    reinforcing: List[str]
    saving: List[str]
    remedial: List[str]
    automation_hooks: List[str]
    demand_formula: str


PATTERN_ORDER = [
    "practice-split",
    "legal-certainty",
    "constitutional-meaning",
    "proportionality",
    "interest-balance",
    "effective-remedy",
    "procedural-guarantees",
    "equality-differentiation",
    "legitimate-expectations",
    "retroactivity",
    "non-mechanical-application",
    "liability-fairness",
    "property-compensation",
    "social-state-positive-obligation",
    "federalism-competence",
    "legislative-gap",
    "good-faith-abuse",
    "constitutional-identity-human-dignity",
    "international-standards",
    "reconsideration-execution",
]


P: Dict[str, PatternEnrichment] = {
    "practice-split": PatternEnrichment(
        "practice-split",
        "Разнобой и неоднозначность правоприменения",
        ["ст. 19", "ст. 46", "ст. 55"],
        ["оценочная норма", "процессуальный фильтр", "санкция", "статусное последствие"],
        ["непредсказуемость исхода", "разные правовые режимы", "риск произвола"],
        "Норма допускает несовместимые судебные подходы в юридически сходных ситуациях.",
        ["выделить одну норму и один правовой вопрос", "собрать competing holdings", "отделить различие в праве от различия в фактах"],
        ["таблица кассационной практики", "акты апелляций и кассаций", "цитаты критериев, примененных судами"],
        ["практика единообразна", "различия объясняются фактами", "нет применения нормы в деле заявителя"],
        ["legal-certainty", "equality-differentiation"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["lower-court practice split finder", "holding clustering", "quote-window extractor"],
        "Признать норму не соответствующей Конституции в той мере, в какой она допускает расходящееся применение без ясных критериев.",
    ),
    "legal-certainty": PatternEnrichment(
        "legal-certainty",
        "Правовая определенность и предсказуемость",
        ["ст. 1", "ст. 15", "ст. 19", "ст. 46", "ст. 55"],
        ["оценочная норма", "срок", "процедура", "обязанность", "санкция"],
        ["невозможность предвидеть последствия", "произвольное усмотрение", "хаотичное применение"],
        "Адресат не может разумно понять критерии, пределы обязанности или последствия.",
        ["найти неопределенный термин", "сопоставить закон и судебные критерии", "показать отсутствие порога или процедуры"],
        ["текст нормы", "судебные акты с разными критериями", "история изменения регулирования"],
        ["критерии прямо названы", "суды применили устойчивый тест", "вред вызван только оценкой доказательств"],
        ["practice-split", "procedural-guarantees"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["norm ambiguity detector", "criteria extractor", "predictability memo generator"],
        "Признать норму не соответствующей Конституции в той мере, в какой она не содержит ясных критериев и допускает непредсказуемое применение.",
    ),
    "constitutional-meaning": PatternEnrichment(
        "constitutional-meaning",
        "Конституционно-сообразное толкование / выявление смысла",
        ["ст. 15", "ст. 18", "ст. 19", "ст. 46", "ст. 55"],
        ["любая примененная норма", "система норм", "переходное положение"],
        ["неконституционный смысл в практике", "невозможность защиты права без обязательного толкования"],
        "Норму можно сохранить, если исключить неконституционный смысл, приданный судами.",
        ["сформулировать вредный смысл", "сформулировать конституционно допустимый смысл", "показать применение вредного смысла в деле"],
        ["судебные акты заявителя", "позиции КС по смежным нормам", "карта практики с тем же смыслом"],
        ["нет устойчивого смысла нормы", "жалоба просит только иной исход", "формула слишком широка"],
        ["legal-certainty", "practice-split", "non-mechanical-application"],
        ["constitutional-meaning"],
        ["reconsideration-execution"],
        ["constitutional meaning mapper", "KSRF position retriever", "demand formula drafter"],
        "Признать норму не противоречащей Конституции в выявленном конституционно-правовом смысле и исключить иной смысл.",
    ),
    "proportionality": PatternEnrichment(
        "proportionality",
        "Соразмерность ограничения",
        ["ст. 17", "ст. 18", "ст. 55"],
        ["запрет", "обязанность", "санкция", "барьер доступа", "автоматическое последствие"],
        ["чрезмерное бремя", "затрагивание существа права", "отсутствие менее обременительной альтернативы"],
        "Публичная цель есть, но мера чрезмерна для заявителя или категории лиц.",
        ["назвать цель", "оценить пригодность", "оценить необходимость", "показать бремя и альтернативы"],
        ["акт применения", "последствия для заявителя", "сравнимые менее жесткие механизмы"],
        ["ограничение минимально", "есть индивидуализация", "альтернатива не решает публичную цель"],
        ["interest-balance", "liability-fairness", "non-mechanical-application"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["proportionality worksheet", "burden inventory", "less restrictive alternatives finder"],
        "Признать норму не соответствующей Конституции в той мере, в какой она устанавливает несоразмерное ограничение без учета тяжести последствий.",
    ),
    "interest-balance": PatternEnrichment(
        "interest-balance",
        "Баланс частных и публичных интересов",
        ["ст. 17", "ст. 19", "ст. 35", "ст. 46", "ст. 55"],
        ["имущественный режим", "процедура", "конфликт прав", "публичное ограничение"],
        ["перекос бремени", "отсутствие компенсации", "доминирование сильной стороны"],
        "Регулирование смещает баланс интересов без гарантий, компенсации или судебного контроля.",
        ["назвать конкурирующие интересы", "распределить выгоды и бремя", "проверить компенсацию и процедуру"],
        ["договоры/акты", "судебные решения", "доказательства бремени и отсутствия компенсации"],
        ["баланс индивидуализирован", "компенсация достаточна", "заявитель недобросовестен"],
        ["proportionality", "property-compensation"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["balance worksheet", "compensation checker", "burden distribution table"],
        "Признать норму не соответствующей Конституции в той мере, в какой она нарушает справедливый баланс интересов без достаточных гарантий.",
    ),
    "effective-remedy": PatternEnrichment(
        "effective-remedy",
        "Эффективная судебная защита",
        ["ст. 45", "ст. 46", "ст. 52", "ст. 53"],
        ["процессуальный фильтр", "срок", "подведомственность", "средство пересмотра", "исполнение"],
        ["иллюзорная защита", "доступ заблокирован", "право не восстановлено"],
        "Формальное средство есть, но оно не дает реального восстановления нарушенного права.",
        ["описать доступное средство", "показать почему оно неэффективно", "связать дефект с нормой, а не с ошибкой суда"],
        ["процессуальная история", "отказы судов", "исполнительные документы", "нерассмотренные доводы"],
        ["средство не использовано", "можно было восстановить право обычным путем", "нет нормативного барьера"],
        ["procedural-guarantees", "legal-certainty"],
        ["constitutional-meaning"],
        ["reconsideration-execution"],
        ["ignored-dovod checker", "remedy route mapper", "access-to-court barrier detector"],
        "Признать норму не соответствующей Конституции в той мере, в какой она лишает лицо эффективного средства судебной защиты.",
    ),
    "procedural-guarantees": PatternEnrichment(
        "procedural-guarantees",
        "Процессуальные гарантии",
        ["ст. 19", "ст. 45", "ст. 46", "ст. 123"],
        ["процессуальная норма", "доказательственный режим", "срок", "обжалование"],
        ["сторона не услышана", "довод не рассмотрен", "нарушена состязательность"],
        "Процедура устроена так, что конституционно значимый довод или участие становятся фиктивными.",
        ["сопоставить доводы и ответы суда", "показать процессуальный барьер", "выделить конституционно значимый довод"],
        ["жалобы и возражения", "протоколы", "судебные акты", "карта довод/ответ"],
        ["доводы рассмотрены", "нарушение единичное и ненормативное", "довод не был заявлен"],
        ["effective-remedy", "non-mechanical-application"],
        ["constitutional-meaning"],
        ["reconsideration-execution"],
        ["ignored-dovod checker", "argument-response aligner", "procedural timeline checker"],
        "Признать норму не соответствующей Конституции в той мере, в какой она не обеспечивает рассмотрение конституционно значимых доводов.",
    ),
    "equality-differentiation": PatternEnrichment(
        "equality-differentiation",
        "Равенство и необоснованная дифференциация",
        ["ст. 19", "ст. 55"],
        ["статусная норма", "льгота", "санкция", "социальная выплата", "процессуальный режим"],
        ["необоснованное различие", "искусственное уравнивание", "дискриминационный критерий"],
        "Сопоставимые лица различаются или разные лица уравнены без объективного и разумного основания.",
        ["определить группы сравнения", "назвать критерий различия", "показать правовое последствие"],
        ["акты по группам сравнения", "статусные документы", "таблица последствий"],
        ["группы несопоставимы", "различие оправдано целью", "последствие несущественно"],
        ["proportionality", "practice-split"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["comparison group builder", "differentiation table", "similarly situated cases finder"],
        "Признать норму не соответствующей Конституции в той мере, в какой она вводит необоснованное различие между сопоставимыми лицами.",
    ),
    "legitimate-expectations": PatternEnrichment(
        "legitimate-expectations",
        "Доверие к праву и законные ожидания",
        ["ст. 1", "ст. 15", "ст. 17", "ст. 18", "ст. 55"],
        ["переходное регулирование", "льгота", "статус", "имущественное право", "процедура"],
        ["подрыв приобретенного положения", "непредвидимое ухудшение", "отсутствие переходного механизма"],
        "Лицо разумно полагалось на прежнее право, но правило изменилось без переходной защиты.",
        ["построить timeline", "показать действия в доверии к праву", "выделить изменение и вред"],
        ["даты возникновения права", "даты изменения нормы/практики", "действия заявителя", "переходные нормы"],
        ["заявитель знал о риске", "ожидание не основано на праве", "есть переходный механизм"],
        ["retroactivity", "legal-certainty"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["timeline checker", "transition-rule detector", "foreseeability memo generator"],
        "Признать норму не соответствующей Конституции в той мере, в какой она подрывает законные ожидания без переходного механизма.",
    ),
    "retroactivity": PatternEnrichment(
        "retroactivity",
        "Обратная сила и ухудшение положения",
        ["ст. 54", "ст. 55", "ст. 57"],
        ["ответственность", "налог", "срок", "переходное положение", "новое толкование"],
        ["ухудшение прошлого положения", "ретроспективное бремя", "наказание за прошлое поведение"],
        "Новая норма или новое толкование применены к прошлым фактам и ухудшили положение.",
        ["развести даты фактов и изменения", "показать ухудшение", "проверить переходные положения"],
        ["timeline", "редакции нормы", "судебный акт с новым толкованием", "доказательства прошлого поведения"],
        ["норма смягчает", "нет применения назад", "отношение продолжалось после изменения"],
        ["legitimate-expectations", "legal-certainty"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["retroactivity timeline checker", "versioned-law comparator", "transition-rule detector"],
        "Признать норму не соответствующей Конституции в той мере, в какой она придает ухудшающую обратную силу новому регулированию.",
    ),
    "non-mechanical-application": PatternEnrichment(
        "non-mechanical-application",
        "Запрет механического применения",
        ["ст. 17", "ст. 19", "ст. 46", "ст. 55"],
        ["санкция", "отказ", "льгота", "статусное последствие", "процессуальный фильтр"],
        ["автоматизм", "игнорирование значимых обстоятельств", "индивидуальная несправедливость"],
        "Правило применено автоматически, хотя Конституция требует учета значимых обстоятельств.",
        ["перечислить обстоятельства", "объяснить их конституционную значимость", "показать отсутствие оценки"],
        ["фактические документы", "судебная мотивировка", "ходатайства и доводы о значимых обстоятельствах"],
        ["норма конституционно допускает автоматизм", "суд учел обстоятельства", "обстоятельства нерелевантны"],
        ["proportionality", "liability-fairness", "procedural-guarantees"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["individualization checker", "circumstance extractor", "reasoning gap detector"],
        "Признать норму не соответствующей Конституции в той мере, в какой она допускает автоматическое применение без учета конституционно значимых обстоятельств.",
    ),
    "liability-fairness": PatternEnrichment(
        "liability-fairness",
        "Справедливость ответственности, вина, индивидуализация",
        ["ст. 19", "ст. 49", "ст. 50", "ст. 54", "ст. 55"],
        ["уголовная санкция", "административная санкция", "штраф", "конфискация", "публичная ответственность"],
        ["ответственность без вины", "несоразмерная санкция", "нет индивидуализации"],
        "Ответственность не связана с виной, тяжестью, вредом или возможностью индивидуализации.",
        ["показать состав и санкцию", "проверить учет вины", "показать невозможность индивидуализации"],
        ["постановления о привлечении", "судебные акты", "доказательства вины/невиновности", "данные о тяжести вреда"],
        ["санкция гибкая", "вина установлена", "суд индивидуализировал ответственность"],
        ["proportionality", "non-mechanical-application"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["sanction individualization checker", "mens rea mapper", "penalty proportionality worksheet"],
        "Признать норму не соответствующей Конституции в той мере, в какой она допускает ответственность без учета вины и индивидуальных обстоятельств.",
    ),
    "property-compensation": PatternEnrichment(
        "property-compensation",
        "Собственность, лишение имущества и компенсация",
        ["ст. 35", "ст. 46", "ст. 55"],
        ["изъятие", "взыскание", "компенсация", "имущественная льгота", "исполнение"],
        ["лишение имущества", "неполная компенсация", "бремя публичной цели на одном лице"],
        "Имущественное право затронуто без справедливой компенсации, процедуры или учета добросовестности.",
        ["идентифицировать имущество", "классифицировать вмешательство", "проверить компенсацию, цель, добросовестность"],
        ["документы о праве", "оценка стоимости", "акты изъятия/взыскания", "платежные документы"],
        ["компенсация полная", "заявитель недобросовестен", "вмешательство минимально"],
        ["interest-balance", "proportionality", "good-faith-abuse"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["deprivation/compensation checker", "good-faith evidence collector", "valuation gap detector"],
        "Признать норму не соответствующей Конституции в той мере, в какой она допускает лишение имущественного права без справедливой компенсации.",
    ),
    "social-state-positive-obligation": PatternEnrichment(
        "social-state-positive-obligation",
        "Социальное государство и позитивные обязанности",
        ["ст. 7", "ст. 19", "ст. 39", "ст. 41", "ст. 46", "ст. 55"],
        ["социальная выплата", "медицина", "пенсия", "льгота", "защита уязвимой группы"],
        ["провал гарантии", "исключение уязвимой группы", "иллюзорное социальное право"],
        "Государство не создало работающий механизм защиты социального права или уязвимой группы.",
        ["назвать группу и право", "показать зависимость от государства", "показать провал механизма"],
        ["статусные документы", "отказы органов", "медицинские/социальные документы", "судебные акты"],
        ["требование чисто бюджетное", "нет специальной уязвимости", "есть доступный механизм"],
        ["equality-differentiation", "effective-remedy", "legislative-gap"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["benefit eligibility checker", "vulnerable status mapper", "positive-obligation evidence checklist"],
        "Признать норму не соответствующей Конституции в той мере, в какой она не обеспечивает работающий механизм реализации социального права.",
    ),
    "federalism-competence": PatternEnrichment(
        "federalism-competence",
        "Компетенция, федерализм, разграничение полномочий",
        ["ст. 5", "ст. 71", "ст. 72", "ст. 76", "ст. 130"],
        ["акт субъекта", "муниципальный акт", "ведомственная компетенция", "публичное полномочие"],
        ["конфликт полномочий", "выход за пределы компетенции", "права зависят от уровня власти"],
        "Нарушение прав возникает из-за неправильного распределения полномочий или конфликта актов.",
        ["определить предмет ведения", "сопоставить акты разных уровней", "показать правовой вред"],
        ["нормы РФ/субъекта/муниципалитета", "акты применения", "судебные выводы о компетенции"],
        ["спор ведомственный без правового вреда", "компетенция прямо закреплена", "нет примененного акта"],
        ["legal-certainty", "effective-remedy"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["competence map builder", "act hierarchy comparator", "federalism conflict detector"],
        "Признать норму не соответствующей Конституции в той мере, в какой она допускает осуществление полномочия вне конституционных пределов компетенции.",
    ),
    "legislative-gap": PatternEnrichment(
        "legislative-gap",
        "Пробел, дефект регулирования, необходимость законодателя",
        ["ст. 15", "ст. 18", "ст. 45", "ст. 46", "ст. 55"],
        ["отсутствующая процедура", "переходный механизм", "срок", "компенсация", "способ защиты"],
        ["право невозможно реализовать", "суд не может восполнить механизм", "зависимость от усмотрения"],
        "Отсутствие правила само блокирует право и не устраняется обычным толкованием.",
        ["назвать отсутствующий механизм", "показать почему он конституционно необходим", "объяснить пределы судебного восполнения"],
        ["отказы органов", "судебные акты", "нормативная схема", "сравнимые работающие механизмы"],
        ["пробел можно закрыть толкованием", "нет обязанности законодателя", "требование слишком политическое"],
        ["effective-remedy", "legal-certainty", "social-state-positive-obligation"],
        ["constitutional-meaning"],
        ["reconsideration-execution"],
        ["gap detector", "procedure model comparator", "legislative-duty formula drafter"],
        "Признать норму не соответствующей Конституции в той мере, в какой она не предусматривает конституционно необходимый механизм реализации права.",
    ),
    "good-faith-abuse": PatternEnrichment(
        "good-faith-abuse",
        "Добросовестность, злоупотребление, доверие оборота",
        ["ст. 17", "ст. 34", "ст. 35", "ст. 46", "ст. 55"],
        ["гражданско-правовой режим", "имущественное взыскание", "регистрация", "банкротство", "исполнение"],
        ["добросовестный несет чужой риск", "злоупотребление не пресечено", "оборот непредсказуем"],
        "Норма не различает добросовестное и недобросовестное поведение или перекладывает риск на добросовестного.",
        ["описать поведение сторон", "показать добросовестность заявителя", "показать чужой риск или злоупотребление"],
        ["договоры", "переписка", "реестры", "судебные выводы о поведении сторон"],
        ["добросовестность не подтверждена", "заявитель контролировал риск", "есть эффективная защита против нарушителя"],
        ["property-compensation", "interest-balance", "legal-certainty"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["good-faith fact extractor", "risk allocation table", "abuse-of-right detector"],
        "Признать норму не соответствующей Конституции в той мере, в какой она не позволяет учитывать добросовестность и пресекать злоупотребление правом.",
    ),
    "constitutional-identity-human-dignity": PatternEnrichment(
        "constitutional-identity-human-dignity",
        "Достоинство, личность, конституционная идентичность",
        ["ст. 2", "ст. 17", "ст. 18", "ст. 21", "ст. 23", "ст. 24"],
        ["статус личности", "частная жизнь", "семейная жизнь", "медицинская информация", "личная автономия"],
        ["унижение достоинства", "исключение автономии", "необратимое вмешательство в личную сферу"],
        "Норма затрагивает ядро человеческого достоинства, автономии или частной/семейной жизни.",
        ["описать личностное ядро права", "показать необратимость или унижение", "связать с процедурой согласия/уведомления"],
        ["медицинские/семейные документы", "переписка с органами", "судебные акты", "доказательства необратимости"],
        ["вред только имущественный", "есть согласие и процедура", "личностное ядро не затронуто"],
        ["procedural-guarantees", "proportionality", "effective-remedy"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["dignity impact checklist", "consent/notification procedure checker", "irreversibility mapper"],
        "Признать норму не соответствующей Конституции в той мере, в какой она допускает вмешательство в достоинство и личную автономию без необходимых гарантий.",
    ),
    "international-standards": PatternEnrichment(
        "international-standards",
        "Международные и сравнительные стандарты как функциональная модель",
        ["ст. 15", "ст. 17", "ст. 18", "ст. 46", "ст. 55"],
        ["процедура", "гарантия", "минимальный стандарт", "средство защиты", "баланс интересов"],
        ["отсутствие минимальной гарантии", "избыточная российская модель", "нет функционального аналога защиты"],
        "Международный или сравнительный материал показывает не украшение, а работающую модель гарантии.",
        ["назвать функцию стандарта", "показать применимость к российской норме", "не подменять Конституцию внешним источником"],
        ["международные тексты", "сравнительные модели", "русское резюме", "привязка к тесту КС"],
        ["материал декоративен", "нет связи с нормой", "стандарт не применим к российскому контексту"],
        ["proportionality", "effective-remedy", "procedural-guarantees"],
        ["constitutional-meaning"],
        ["effective-remedy"],
        ["functional standard mapper", "comparative model table", "source-to-test linker"],
        "Просить истолковать норму в конституционно-правовом смысле, учитывающем минимальную функциональную гарантию защиты права.",
    ),
    "reconsideration-execution": PatternEnrichment(
        "reconsideration-execution",
        "Исполнение, пересмотр и последствия постановления КС РФ",
        ["ст. 15", "ст. 46", "ст. 79", "ст. 80"],
        ["пересмотр", "исполнение", "аналогичные дела", "новое обстоятельство", "правовые последствия акта КС"],
        ["постановление КС не исполнено", "нет пересмотра", "аналогичное дело лишено эффекта"],
        "Проблема в переводе правовой позиции КС в пересмотр, исполнение или аналогичные дела.",
        ["классифицировать акт КС", "определить заявителя/аналогичность", "выбрать процессуальный маршрут"],
        ["акт КС", "судебные акты по делу", "заявление о пересмотре", "отказы в исполнении"],
        ["акт КС не применим", "дело не аналогично", "срок/процедура пропущены без причины"],
        ["effective-remedy", "procedural-guarantees"],
        ["constitutional-meaning"],
        ["reconsideration-execution"],
        ["KSRF aftermath planner", "analogy classifier", "reconsideration route generator"],
        "Просить обеспечить пересмотр или применение выявленного конституционно-правового смысла к делу заявителя и аналогичным ситуациям.",
    ),
}


FORMULA_MARKERS = {
    "extent_formula": {
        "title": "Формула `в той мере, в какой`",
        "regex": r"в\s+той\s+мере,\s+в\s+какой.{0,260}",
        "use": "Для просительной части и точного ограничения предмета проверки.",
    },
    "practice_meaning": {
        "title": "Буквальный смысл и смысл практики",
        "regex": r"(?:по\s+смыслу,\s+придаваемому.{0,220}|по\s+своему\s+буквальному\s+смыслу.{0,220})",
        "use": "Для атаки не только текста нормы, но и устойчивого смысла применения.",
    },
    "does_not_presuppose": {
        "title": "Формула `не предполагает`",
        "regex": r"не\s+предполагает.{0,260}",
        "use": "Для исключения неконституционного толкования без полного удаления нормы.",
    },
    "does_not_exclude": {
        "title": "Формула `не исключает`",
        "regex": r"не\s+исключает.{0,260}",
        "use": "Для указания конституционно допустимого механизма, который суды должны учитывать.",
    },
    "legislative_duty": {
        "title": "Обязанность законодателя",
        "regex": r"(?:федеральн\w+\s+законодатель.{0,120}(?:обязан|должен|надлежит|призван|вправе).{0,160}|законодатель\s+(?:обязан|должен|надлежит|призван|вправе).{0,240}|надлежит\s+внести.{0,220})",
        "use": "Для пробелов, переходных механизмов и последствий постановления КС.",
    },
    "courts_must_not": {
        "title": "Пределы судебного толкования",
        "regex": r"(?:суды\s+не\s+вправе.{0,260}|не\s+может\s+рассматриваться\s+как.{0,220}|не\s+может\s+служить\s+основанием.{0,220})",
        "use": "Для блока о том, какой смысл обычные суды не вправе придавать норме.",
    },
}


COUNTERARGUMENTS = [
    {
        "objection": "Это обычная судебная ошибка",
        "check": "Покажи, что вред возник из нормы или устойчивого смысла, а не из разовой оценки доказательств.",
        "fallback": "Сузить вопрос до смысла нормы, который суд применил как обязательный.",
    },
    {
        "objection": "Жалоба просит переоценить факты",
        "check": "Убери спор о доказанности факта; оставь вопрос о критерии, процедуре, бремени или последствии.",
        "fallback": "Переписать применение через `суды истолковали норму как допускающую...`.",
    },
    {
        "objection": "Нет примененной нормы",
        "check": "Найди место в судебном акте, где норма стала основанием отказа, санкции, срока, статуса или последствия.",
        "fallback": "Если норма только упомянута, сначала готовить обычное обжалование или ходатайство о запросе.",
    },
    {
        "objection": "Вопрос уже решен КС РФ",
        "check": "Проверь, есть ли новый аспект: другой заявитель, иной вред, новая практика, новый контекст или иная формула требования.",
        "fallback": "Сформулировать `не повторную жалобу`: новый аспект применения нормы.",
    },
    {
        "objection": "Проблему можно решить обычным толкованием",
        "check": "Покажи, что обычные суды не имеют работающего критерия или системно придают норме вредный смысл.",
        "fallback": "Просить выявить обязательный конституционно-правовой смысл, а не признать норму полностью неконституционной.",
    },
    {
        "objection": "Требование слишком широкое",
        "check": "Ограничь просительную часть фактическим вредом заявителя и конкретным аспектом нормы.",
        "fallback": "Перейти к формуле `в той мере, в какой...`.",
    },
]


def load_registry(path: Path) -> Dict[str, List[dict]]:
    """Load and preflight the extractor registry before any output is written."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expanded_pattern_registry.json must contain a JSON object")

    missing = [code for code in PATTERN_ORDER if code not in payload or code not in P]
    if missing:
        raise ValueError(f"missing pattern metadata: {', '.join(missing)}")

    for code in PATTERN_ORDER:
        rows = payload.get(code)
        if not isinstance(rows, list):
            raise ValueError(
                f"expanded_pattern_registry.json pattern {code!r} must contain an array"
            )
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(
                    f"expanded_pattern_registry.json pattern {code!r} row {index} "
                    "must be an object"
                )
            number = row.get("number")
            if not isinstance(number, str) or not number.strip():
                raise ValueError(
                    f"expanded_pattern_registry.json pattern {code!r} row {index} "
                    "number must be a non-empty string"
                )
    return payload


def support_numbers(registry: Dict[str, List[dict]], code: str, limit: int = 12) -> List[str]:
    rows = registry.get(code, [])
    if len(rows) <= limit:
        return [row["number"] for row in rows]
    head = [row["number"] for row in rows[: limit // 2]]
    tail = [row["number"] for row in rows[-(limit // 2) :]]
    return head + tail


def iter_texts(analysis: Path) -> Iterable[tuple[str, str, str]]:
    for path in sorted((analysis / "texts").glob("*.txt")):
        name = path.stem
        year, number = name.split("__", 1)
        number = number.replace("_", "/")
        yield year, number, path.read_text(encoding="utf-8", errors="ignore")


def clean_snippet(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:360].rstrip()


def extract_formulas(analysis: Path, per_family: int = 35) -> Dict[str, dict]:
    formulas: Dict[str, dict] = {}
    compiled = {code: re.compile(meta["regex"], re.IGNORECASE | re.UNICODE) for code, meta in FORMULA_MARKERS.items()}
    for code, meta in FORMULA_MARKERS.items():
        formulas[code] = {**meta, "examples": []}

    for year, number, text in iter_texts(analysis):
        for code, regex in compiled.items():
            if len(formulas[code]["examples"]) >= per_family:
                continue
            match = regex.search(text)
            if not match:
                continue
            formulas[code]["examples"].append(
                {
                    "number": number,
                    "year": year,
                    "snippet": clean_snippet(match.group(0)),
                }
            )
    return formulas


def build_graph(registry: Dict[str, List[dict]]) -> dict:
    nodes = []
    edges = []
    seen = set()

    def add_node(node_id: str, kind: str, label: str, **extra: object) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append({"id": node_id, "kind": kind, "label": label, **extra})

    for code in PATTERN_ORDER:
        item = P[code]
        add_node(f"pattern:{code}", "pattern", item.title, primary_when=item.primary_when)
        for value in item.articles:
            add_node(f"article:{value}", "constitutional_article", value)
            edges.append({"from": f"pattern:{code}", "to": f"article:{value}", "type": "uses_article"})
        for value in item.norm_types:
            add_node(f"norm:{value}", "norm_type", value)
            edges.append({"from": f"norm:{value}", "to": f"pattern:{code}", "type": "may_trigger"})
        for value in item.harm_types:
            add_node(f"harm:{value}", "harm_type", value)
            edges.append({"from": f"harm:{value}", "to": f"pattern:{code}", "type": "may_trigger"})
        for value in item.automation_hooks:
            add_node(f"tool:{value}", "automation_hook", value)
            edges.append({"from": f"pattern:{code}", "to": f"tool:{value}", "type": "supported_by"})
        for value in support_numbers(registry, code, 8):
            add_node(f"decision:{value}", "ksrf_decision", value)
            edges.append({"from": f"pattern:{code}", "to": f"decision:{value}", "type": "has_anchor"})
        for relation, targets in (
            ("reinforces_with", item.reinforcing),
            ("can_be_saved_by", item.saving),
            ("remedy_with", item.remedial),
        ):
            for target in targets:
                edges.append({"from": f"pattern:{code}", "to": f"pattern:{target}", "type": relation})

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "nodes": nodes,
        "edges": edges,
    }


def md_list(values: List[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def write_argument_packages(refs: Path) -> None:
    lines = [
        "# Сборщик пакета аргументов",
        "",
        "Используй этот справочник, чтобы собирать не один довод, а пакет конституционно-правовой аргументации.",
        "",
        "## Базовая схема",
        "",
        "- `Основной паттерн`: главный дефект нормы.",
        "- `Усиливающий паттерн`: доказывает, что дефект проявлен в практике, процедуре, бремени или сравнении групп.",
        "- `Сохраняющий паттерн`: формула конституционно-правового смысла, если норму можно сохранить.",
        "- `Remedy-паттерн`: что должен дать КС РФ или обычный суд после признания дефекта.",
        "",
    ]
    for code in PATTERN_ORDER:
        item = P[code]
        lines.extend(
            [
                f"## {code}: {item.title}",
                "",
                f"**Основной, когда:** {item.primary_when}",
                "",
                f"**Усиливать через:** {', '.join(item.reinforcing)}",
                "",
                f"**Сохранять через:** {', '.join(item.saving)}",
                "",
                f"**Remedy:** {', '.join(item.remedial)}",
                "",
                f"**Формула требования:** {item.demand_formula}",
                "",
            ]
        )
    (refs / "argument-package-builder.md").write_text("\n".join(lines), encoding="utf-8")


def write_counterarguments(refs: Path) -> None:
    lines = [
        "# Secretariat Counterargument Playbook",
        "",
        "Используй перед финализацией аргумента. Цель - заранее ответить на типовые возражения о недопустимости.",
        "",
    ]
    for item in COUNTERARGUMENTS:
        lines.extend(
            [
                f"## {item['objection']}",
                "",
                f"**Проверка:** {item['check']}",
                "",
                f"**Безопасная рамка:** {item['fallback']}",
                "",
            ]
        )
    (refs / "counterargument-playbook.md").write_text("\n".join(lines), encoding="utf-8")


def write_evidence_maps(refs: Path, registry: Dict[str, List[dict]]) -> None:
    lines = [
        "# Доказательственные карты по паттернам",
        "",
        "Каждый паттерн должен превращаться в проверяемую карту материалов, а не только в тезис.",
        "",
    ]
    data = {}
    for code in PATTERN_ORDER:
        item = P[code]
        data[code] = {
            "title": item.title,
            "proof_tasks": item.proof_tasks,
            "evidence": item.evidence,
            "falsifiers": item.falsifiers,
            "automation_hooks": item.automation_hooks,
            "decision_anchors": support_numbers(registry, code),
        }
        lines.extend(
            [
                f"## {code}: {item.title}",
                "",
                "**Что доказать:**",
                md_list(item.proof_tasks),
                "",
                "**Материалы:**",
                md_list(item.evidence),
                "",
                "**Что ослабляет:**",
                md_list(item.falsifiers),
                "",
                "**Автоматизация:**",
                md_list(item.automation_hooks),
                "",
                f"**Постановления-опоры:** {', '.join(data[code]['decision_anchors'])}",
                "",
            ]
        )
    (refs / "evidence-maps.md").write_text("\n".join(lines), encoding="utf-8")
    (refs / "evidence_maps.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_language_formulas(refs: Path, formulas: Dict[str, dict]) -> None:
    lines = [
        "# Банк формул языка КС РФ",
        "",
        "Формулы извлечены регулярными маркерами из локальных текстов Постановлений КС РФ. Перед финальным цитированием проверяй полный текст постановления.",
        "",
    ]
    for code, item in formulas.items():
        lines.extend([f"## {item['title']}", "", f"**Зачем:** {item['use']}", ""])
        for example in item["examples"][:12]:
            lines.append(f"- `{example['number']}` ({example['year']}): {example['snippet']}")
        lines.append("")
    (refs / "language-formulas.md").write_text("\n".join(lines), encoding="utf-8")
    (refs / "language_formulas.json").write_text(json.dumps(formulas, ensure_ascii=False, indent=2), encoding="utf-8")


def write_graph(refs: Path, graph: dict) -> None:
    by_kind: Dict[str, int] = defaultdict(int)
    for node in graph["nodes"]:
        by_kind[node["kind"]] += 1
    edge_counts: Dict[str, int] = defaultdict(int)
    for edge in graph["edges"]:
        edge_counts[edge["type"]] += 1

    lines = [
        "# Граф конституционно-правовой аргументации",
        "",
        "Переносимый JSON-граф для перехода от фактов и дефектов нормы к статьям Конституции, паттернам, доказательствам и инструментам.",
        "",
        "## Количество узлов",
        "",
    ]
    for kind, count in sorted(by_kind.items()):
        lines.append(f"- `{kind}`: {count}")
    lines.extend(["", "## Количество связей", ""])
    for kind, count in sorted(edge_counts.items()):
        lines.append(f"- `{kind}`: {count}")
    lines.extend(["", "## Как использовать", "", "- Начинай с узлов `norm:*` или `harm:*`, когда факты уже известны.", "- Переходи к узлам `pattern:*`, чтобы выбрать семейства аргументов.", "- Иди по связям `uses_article`, `has_anchor`, `supported_by` и пакетным связям, чтобы собрать раздел жалобы.", ""])
    (refs / "constitutional-graph.md").write_text("\n".join(lines), encoding="utf-8")
    (refs / "constitutional_graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis",
        required=True,
        help="Каталог результатов extract_ksrf_argument_patterns.py; задаётся явно",
    )
    parser.add_argument("--skill", default=str(DEFAULT_SKILL))
    args = parser.parse_args()

    analysis = Path(args.analysis).expanduser().resolve()
    skill = Path(args.skill).expanduser().resolve()
    try:
        registry = load_registry(analysis / "expanded_pattern_registry.json")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot load expanded pattern registry: {exc}", file=sys.stderr)
        return 2

    refs = skill / "references"
    refs.mkdir(parents=True, exist_ok=True)

    formulas = extract_formulas(analysis)
    graph = build_graph(registry)

    write_argument_packages(refs)
    write_counterarguments(refs)
    write_evidence_maps(refs, registry)
    write_language_formulas(refs, formulas)
    write_graph(refs, graph)

    enrichment_summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "patterns": len(PATTERN_ORDER),
        "formula_families": {code: len(item["examples"]) for code, item in formulas.items()},
        "graph_nodes": len(graph["nodes"]),
        "graph_edges": len(graph["edges"]),
        "references": [
            str(refs / "argument-package-builder.md"),
            str(refs / "counterargument-playbook.md"),
            str(refs / "evidence-maps.md"),
            str(refs / "language-formulas.md"),
            str(refs / "constitutional-graph.md"),
        ],
    }
    (analysis / "enrichment_summary.json").write_text(json.dumps(enrichment_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(enrichment_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

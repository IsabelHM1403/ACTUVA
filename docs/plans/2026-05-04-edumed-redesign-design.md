# Дизайн: переход ACTUVa → EduMed-стиль с гибридом «модули + виртуальный пациент»

**Дата:** 2026-05-04
**Статус:** одобрено пользователем

## Контекст и цели

В проекте есть рабочий Django-стек ACTUVa (лендинг на Tailwind, OpenAI-чат с
ассистентами, кейсы преподавателя, учёт и feedback). В директории
`EduMed_UVa_completo/` лежат 15 готовых статичных HTML страниц с другим
дизайном и другой педагогической моделью: 12 интерактивных модулей анамнезии
на Preact + 1 главная сетка + 2 вспомогательные.

Задача — взять дизайн и контент EduMed как ядро продукта, OpenAI-чат
оставить как «виртуального пациента», запускаемого после прохождения модуля.
Весь существующий функционал ACTUVa сохраняется, шаблоны перерисовываются
в стиле EduMed.

## Решения, принятые в брейнсторме

| Вопрос | Решение |
|---|---|
| Точка входа | Лендинг с двумя CTA: «Comenzar Entrenamiento» (чат) + «Estudiar Anamnesis» (12 модулей) |
| Учёт прогресса | Полный — каждое значимое нажатие пишется как событие |
| Связь с виртуальным пациентом | 2-3 пациента на каждый модуль |
| Существующий функционал | Сохранить весь, перерисовать в стиле EduMed |
| Технология фронта модулей | Полностью переписать Preact → Django + vanilla JS |
| Хранение контента модулей | Модели Django + админка (мини-CMS) |
| Начальный контент | Парсер 12 HTML EduMed → миграция данных |
| Виртуальные пациенты | Гибрид: 12 базовых через скрипт + добавление через админку |

## Архитектура и точка входа

- `GET /` — лендинг, двухкнопочный, в стиле EduMed (паттерн со скриншота).
  «Comenzar Entrenamiento» → существующий чат-флоу, «Estudiar Anamnesis» →
  `/anamnesis/`.
- `GET /anamnesis/` — главная EduMed (адаптация исходного `index.html`):
  12 карточек в 4 группах + 2 коллекции YouTube. Если пользователь
  залогинен, на каждой карточке отображается статус прохождения
  (✓ пройден / в процессе / новый).
- `GET /anamnesis/<slug>/` — страница модуля (адаптация
  `Anamnesis_Cefalea_v1.html` и аналогичных). В конце модуля — блок
  «Hablar con paciente virtual» со списком виртуальных пациентов модуля.
- `POST /anamnesis/<slug>/event/` — endpoint для трекинга действий студента.
- `/chat/...`, `/cases/...`, `/stats/...`, `/accounts/...` — существующая
  логика, шаблоны перерисованы в стиле EduMed.

## Новое Django-приложение `anamnesis`

### Модели контента (редактируется через `/admin/`)

- **Module** — slug, name, emoji, gradient_from, gradient_to, deco_code,
  group (cardiorrespiratorio / digestivo / neurológico / general), order,
  description.
- **Patient** — module FK, name, age, diagnosis, diagnosis_key (text array),
  order.
- **PatientQuote** — patient FK, step_number, text.
- **Step** — module FK, n, title, example_question, think_box, tip_box,
  sec_label.
- **FlipCard** — step FK, label, badge, back_text.
- **IrrelevantItem** — step FK, name, badge, body_text.
- **StepDxFeedback** — step FK, patient FK, quote_idx, compat
  (neutral/positive/strong), evidence (1-3), interpretation, fits_for,
  rules_out.
- **DiagnosisCombo** — module FK, dx, compat, symptoms, key.
- **QuizQuestion** + **QuizChoice** — финальный квиз модуля.
- **VirtualPatient** — module FK, openai_assistant_id (FK на
  `assistants.Assistant`), display_name, age, persona_summary.

### Модели трекинга (студенты)

- **ModuleProgress** — student, module, started_at, completed_at, last_step.
- **StudentEvent** — student, module, event_type (`step_open`, `flip`,
  `knew`, `unknown`, `quiz_answer`, `dx_view`, `complete`, `vp_open`),
  payload (JSON), timestamp.
- **QuizAttempt** — student, module, score, total, answers (JSON),
  submitted_at.

## Frontend: переписывание Preact → vanilla JS + Django

- `static/anamnesis/css/edumed.css` — общий CSS, вытащенный из inline стилей
  `Anamnesis_Cefalea_v1.html` (это шаблон-эталон).
- `static/anamnesis/js/module.js` — vanilla JS, читает initial state из
  `<script id="module-data" type="application/json">`, рендерит шаги,
  обрабатывает flip, knew/unknown, quiz, dx-feedback. Каждое значимое
  действие → `fetch('/anamnesis/<slug>/event/', {method: 'POST', body: ...})`.
- Шаблоны: `templates/anamnesis/dashboard.html`, `templates/anamnesis/module.html`.

## Парсер контента

- Management-команда `python manage.py import_edumed_content` парсит 12 HTML
  из `EduMed_UVa_completo/`, извлекает JS-структуры (`PATIENT`, `ALL_QS`,
  `STEP_DX`, `COMBOS`, `IRRELEVANT_ITEMS`, `FLIP_CARDS`, `QUIZ`),
  заполняет модели.
- Команда идемпотентна (по `Module.slug`): повторный запуск обновляет
  существующие записи, а не дублирует.
- Реализация: regex для выделения блоков `const X = {...};`, парсинг
  «почти-JSON» через `demjson3` (хендлит JS-литералы без двойных кавычек).

## Виртуальные пациенты (OpenAI)

- 12 базовых пациентов (по одному на модуль) создаются вместе с
  `import_edumed_content`. Django создаёт запись `VirtualPatient`,
  пытается создать OpenAI-ассистента через API (если `OPENAI_API_KEY`
  доступен), сохраняет `assistant_id`. Без ключа — оставляет пустым,
  заполняется позже из админки.
- Преподаватель добавляет дополнительных через
  `/admin/anamnesis/virtualpatient/add/`.
- Кнопка «Hablar con paciente virtual» в конце модуля → `/chat/start/?virtual_patient=<id>`
  → переиспользует существующее `chat/views.py` с привязкой к ассистенту
  пациента.

## Перерисовка существующих шаблонов

Все шаблоны переписываются на CSS-переменные EduMed, отказ от Tailwind
в пользу самописного CSS:

- `templates/landing.html` — двухкнопочный hero
- `templates/dashboard.html`, `templates/base.html`
- `templates/accounts/login.html`, `register.html`
- `templates/chat/session.html`, `feedback.html`, `no_access.html`
- `templates/cases/list.html`, `create.html`
- `templates/stats/dashboard.html`, `evaluaciones.html` + новые метрики по
  модулям EduMed

## Тестирование

- `anamnesis/tests/test_models.py` — модели и кастомные методы прогресса.
- `anamnesis/tests/test_parser.py` — на одном эталонном HTML (Cefalea),
  проверяет извлечение всех структур.
- `anamnesis/tests/test_views.py` — рендер модуля, POST событий, контроль
  доступа.
- `anamnesis/tests/test_admin.py` — редактирование контента через админку
  меняет рендер.

## Этапы работ

1. Скелет приложения `anamnesis` + модели контента + миграции.
2. Парсер + management-команда + один эталонный модуль (Cefalea).
3. Frontend модуля: vanilla JS + CSS + шаблон, рендер с данными.
4. Endpoint трекинга событий + модели прогресса.
5. Дашборд `/anamnesis/` + новый лендинг + базовый шаблон в стиле EduMed.
6. Перерисовка остальных существующих шаблонов (chat, cases, stats, accounts).
7. Виртуальные пациенты: модель + интеграция с `chat/`.
8. Расширение статистики преподавателя метриками EduMed.
9. Импорт оставшихся 11 модулей и итоговая проверка.

## Риски и оговорки

- Полное переписывание Preact-логики (~2700 строк на модуль) — серьёзный
  объём. Альтернатива (минимальная обёртка вокруг существующего Preact)
  была отклонена пользователем; рекомендация зафиксирована в дизайне.
- Парсер «почти-JSON» структур из JS — хрупкое место. Покрываем тестами.
- OpenAI-ассистенты создаются только при наличии ключа; иначе чат с
  виртуальным пациентом не работает до заполнения `assistant_id` вручную.

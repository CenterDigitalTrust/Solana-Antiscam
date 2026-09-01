# КОМАНДА ДЛЯ АГЕНТА (Antigravity) — РАЗРАБОТКА САЙТА PATROL / ДОЗОР

Скопируй весь текст ниже целиком и вставь как первое сообщение агенту.

---

## РОЛЬ

Ты — senior fullstack-разработчик и arts director в одном лице. Твоя задача — построить продакшн-готовый сайт **PATROL** (кодовое имя проекта — «ДОЗОР») с нуля, строго по этому техническому заданию. Это не черновик и не концепт — результат должен быть готов к деплою. Не импровизируй с содержанием, структурой секций или копирайтингом там, где они заданы явно. Там, где решение оставлено на твоё усмотрение, оно явно помечено словом «(на твоё усмотрение)».

Перед началом работы прочитай ТЗ целиком. Если что-то противоречит друг другу — останавливайся и переспрашивай, не додумывай сам.

---

## 0. ЖЁСТКИЕ ПРАВИЛА (не нарушать ни при каких условиях)

1. Никаких градиентов, никаких теней (box-shadow/drop-shadow) — дизайн полностью плоский (flat).
2. Никаких скруглений радиусом больше 2px нигде, кроме бейджей статусов (там допустимо 0px — прямые углы предпочтительнее).
3. Границы — только 1px, цвет `--rule`. Не используй границы толще 1px нигде, кроме карточек карантина (там 1px `--ink`).
4. Никакого lorem ipsum и никакого выдуманного контента там, где копирайтинг задан ниже дословно — используй его как есть, менять можно только при переводе на другой язык интерфейса.
5. Обязательна поддержка 4 языков интерфейса: EN (по умолчанию), UA, RU, ES — через словари ключей (i18n), не хардкодить строки в разметке.
6. Продукт некастодиальный: нигде в UI не должно быть полей для приватного ключа, подключения кошелька или подписи транзакции. Ни в одной версии этого этапа.
7. Не добавляй никаких элементов, не описанных в этом ТЗ (никаких попапов с подпиской на рассылку, никаких cookie-баннеров с анимацией, никаких decorative-иконок «для красоты» сверх сигнатурного элемента, описанного ниже).
8. Все статистические утверждения на сайте обязаны сопровождаться подписью источника (см. текст ниже) — не убирай атрибуцию источника при вёрстке.
9. Мобильная адаптация обязательна и проверяется отдельно — см. раздел 8.
10. Если каких-то данных не хватает (реальный API-ключ, реальная база данных) — используй мок-данные ровно в том формате, который указан в разделе 6, и явно пометь в коде комментарием `// MOCK DATA — replace with live Supabase subscription`.

---

## 1. ДИЗАЙН-СИСТЕМА — ТОКЕНЫ (использовать ровно эти значения)

```css
--beige-0: #F5F0E6;   /* фон страницы */
--paper:   #FBF8F1;   /* карточки, инпуты, подложки таблиц */
--ink:     #1B1712;   /* основной текст, кнопки, тёмные поверхности (футер, терминал) */
--ink-soft:#4A443B;   /* вторичный текст */
--ink-faint:#8C8375;  /* подписи, лейблы, метаданные */
--rule:    #D8CDB6;   /* границы, разделители */
--rust:    #9A3F2E;   /* опасность / карантин / акцент */
--olive:   #4E5A34;   /* безопасно / рост */
--ochre:   #A87C2E;   /* предупреждение / watch */
```

Никаких других цветов не вводить. Тёмный терминал/футер — это `--ink` как фон с `--paper`/приглушённым бежевым как текст (см. готовую реализацию ниже), а не отдельный «чёрный» токен.

## 2. ТИПОГРАФИКА

Три роли шрифта, обязательно разными семействами:

- **Display (заголовки):** Fraunces (serif, вариативный вес). Подключить через Google Fonts как variable font (`Fraunces:opsz,wght@9..144,300..900`), использовать вес 600–650 для h1/h2, курсив (italic) для акцентных слов внутри заголовка (см. хедлайн ниже).
- **Основной текст:** Inter. Если по какой-то причине Inter недоступен в окружении — **допустима замена на Work Sans или Manrope** (шрифты можно немного заменить, это разрешено), но никогда не заменяй на системный sans-serif по умолчанию.
- **Данные / тикеры / таблицы / терминал:** IBM Plex Mono, обязательно — веса 400 и 700. Это принципиальный элемент бренда (отсылка к выводу торгового daemon-агента), не заменять на другой моноширинный шрифт.

Никаких дополнительных шрифтов сверх этих трёх ролей.

## 3. АССЕТЫ

- Лого — вложенный файл `logo.svg` (полный лок-ап с текстом «PATROL MD»), плюс обработанные версии:
  - `logo_icon_ink.png` — только щит-иконка, тёмная (#1B1712), прозрачный фон — для хедера на светлом фоне;
  - `logo_icon_paper.png` — только щит-иконка, светлая (#FBF8F1), прозрачный фон — для футера/тёмных поверхностей.
- Если файлы не переданы агенту физически — сгенерируй временную SVG-заглушку такой же композиции (щит + радар + растущая стрелка) в одном цвете `currentColor`, без градиента, и пометь TODO на замену настоящим лого.

## 4. СТРУКТУРА СТРАНИЦЫ (порядок фиксирован, ничего не переставлять)

### 4.1 Top strip
Тонкая полоса `--ink`/`--paper`, моноширинный текст 11–12px: пульсирующая точка + «SCANNING SOLANA — NEW SWEEP EVERY 10 SECONDS» слева; переключатель языков `UA · EN · RU · ES` справа, активный язык подчёркнут.

### 4.2 Header
Слева: иконка-лого + вордмарк «PATROL» (Fraunces) + под ним мелкий moно-сабтайтл «SOLANA ANALYTICS & SCAM PROTECTION». Справа: навигация — `Live Feed · Methodology · Growth · Quarantine · About`, текущий пункт подчёркнут. Sticky при скролле (на твоё усмотрение — допустимо, если не мешает).

### 4.3 Hero
- Эйброу-лейбл: `AUTONOMOUS ON-CHAIN AUDIT · CENTER FOR DIGITAL TRUST`.
- H1 (Fraunces, ~72–80px, два ряда): «Verify first. / Never buy *blind.*» — слово «blind.» курсивом, цвет `--rust`.
- Подзаголовок (обычный текст, ~480px max-width): «PATROL scans Solana every ten seconds, audits every new token on-chain, and publishes a verdict in the live feed before you've had time to click buy. Non-custodial by design — it never holds funds and never issues a buy or sell signal.»
- Карточка-статистика справа от подзаголовка (моно, паперный фон, 1px рамка): «**98.6%** of tokens launched on Pump.fun are rug pulls or pump-and-dumps. **$151M+** lost across three Solana DEXs in six months.» + подпись мелким серым моно: «SOURCE — SOLIDUS LABS (2025); INDEPENDENT ACADEMIC STUDY (2026)».
- Поле проверки токена: text input placeholder «Paste a token address to check it now →» + кнопка «CHECK TOKEN» (моно, тёмный фон `--ink`, текст `--paper`). По сабмиту — вызов серверного эндпоинта `/api/check?address=` (заглушка на этом этапе, см. раздел 6).
- Под полем мелкая моно-подпись: «NO WALLET CONNECTION · NO CUSTODY · NO TRADING SIGNALS — EVER».
- Фоновый декоративный сигнатурный элемент: тонкие концентрические окружности (radar rings), цвет `--rule`, 1px, без заливки, справа за текстом, `pointer-events:none`. Это единственный декоративный акцент на странице — больше decorative-графики нигде не добавлять.

### 4.4 Терминал (сигнатурный блок «живой вывод демона»)
Тёмная карточка `--ink`, моно-шрифт. Заголовок бара: «DAEMON — LIVE OUTPUT · discovery.py» + три точки-индикатора справа. Таблица без границ, колонки: `TOKEN / DISCOVERED / SCORE / Δ PRICE / STATUS`. Минимум 5 строк мок-данных, статусы трёх видов: `MONITORING` (нейтральный), `GROWTH LEADER` (зелёный `#8FBF6A`), `QUARANTINED — <причина>` (красный `#C2705A`). Это подключается к реальному realtime-каналу в проде (см. раздел 6) — на этом этапе статичный мок с пометкой TODO.

### 4.5 Statistics bar
Три ячейки через тонкие вертикальные разделители: число (моно, ~52px, bold) + подпись под ним:
- `4,812` — Tokens scanned today
- `4,398` — Rejected & quarantined
- `414` — Passed audit

Под блоком — мелкая моно-строка: «METHODOLOGY BELOW — EVERY DECISION IS LOGGED TO THE PUBLIC ARCHIVE».

### 4.6 Methodology — «01 — METHODOLOGY / How the score is built»
Подзаголовок секции: «0–100 points across six weighted checks, recomputed continuously as each token trades. Nothing here is a black box.»
Сетка 3×2 карточек (граница `--rule` между ячейками, фон `--paper`). В каждой: вес в %, лейбл-код в рамке, заголовок, описание, полоса-индикатор веса внизу (заполнение = проценту веса). Данные строго такие:

| Вес | Код | Заголовок | Текст |
|---|---|---|---|
| 25% | SECURITY | Security | Has the creator renounced mint authority? Do the top 10 wallets hold under 30–40% of supply? Is liquidity locked or burned? Serious red flags cut this score to near zero. |
| 20% | LIQUIDITY | Liquidity | Can you actually sell? Pools under $1,000 score zero. Pools growing steadily toward $10,000–$30,000 score highest. |
| 20% | MOMENTUM | Momentum | Buy and sell volume over the last five minutes, and the ratio of buyers to sellers. Broad, one-sided buying scores highest. |
| 15% | MARKET | Market | Trading volume and market-cap sanity checks — over $5,000 traded in five minutes scores 85–100%; zero volume scores 10%. Flags caps that dwarf real liquidity. |
| 15% | WALLET | Wallet | Has the creator already sold or emptied their wallet? Locking in profit early reads as a signal against a future rug pull, not against it. |
| 5% | DATA QUALITY | Data quality | A penalty for gaps in source data — for example, holder counts DexScreener couldn't return. Unknown risk is still risk. |

### 4.7 Monitoring feed — «02 — MONITORING FEED / Every token, the moment it's discovered»
Подзаголовок: «No request required. PATROL finds it first — you just watch the ticker.»
Таблица в паперной карточке-рамке, колонки: `Token / Discovered / Score / Δ from T0 / Status`. Статусные бейджи — обводка цветом статуса, без заливки: `Monitoring` (нейтральный), `Watch` (`--ochre`), `Growth leader` (`--olive`), `Quarantined` (`--rust`). Первая строка с тегом `NEW` (маленький красный лейбл справа от тикера) — для только что обнаруженного токена. Данные — реалтайм-подписка на Supabase-таблицу `tokens` (см. раздел 6), на этом этапе мок из 6 строк.

### 4.8 Growth leaders — «03 — GROWTH LEADERS / Passed audit. Up 50%+ from T0.»
Подзаголовок: «Tokens move here automatically the instant they cross +50% from discovery — proof the filter isn't just theoretical.»
Та же структура таблицы, что и в 4.7, но источник данных — материализованное вью `tokens_growth_leaders` (`price_change_pct >= 50 AND state != 'quarantine'`). Строки этой таблицы — с лёгкой заливкой фона (чуть темнее beige, `#F1F0E3`) для визуального отличия от 4.7.

### 4.9 Quarantine zone — «04 — QUARANTINE ZONE / Every rejection, stamped with its reason»
Подзаголовок: «Nothing is hidden after the fact. The public archive of what PATROL turned away, and why.»
Сетка из 3 карточек. Каждая карточка: лёгкий поворот (`rotate(-1.4deg)`, `rotate(1deg)`, `rotate(-0.6deg)` по очереди), 1px рамка `--ink`, фон `--paper`. Внутри: тикер + дата/время (UTC, моно), штамп «REJECTED» (обводка `--rust`, повёрнут на `-6deg`, крупный моно-текст), причина отказа текстом (буллет с bold-акцентом на ключевой цифре). Это публичный архив — в проде подключается к записям со `state = 'quarantine'` и полем `status_reason`.

### 4.10 About / Mission — «05 — ABOUT»
Двухколоночный лейаут. Слева: крупная цитата (Fraunces, курсив не нужен, просто крупный serif) — «"Safety isn't a feature of this product. It's the only reason it exists."» — и два абзаца текста:

> PATROL is built and maintained by the **Center for Digital Trust**, a Ukrainian non-profit working to make trust verifiable rather than declared. It's the organization's second initiative alongside MD System, an evidentiary integrity platform for public institutions — both share one principle: transparent, non-custodial, on-chain verification, with no single point of failure and no authority to edit the record.
>
> An open, public API for wallets and DEX aggregators is planned as the next phase — so any project in the ecosystem can carry the same security score, without building an audit pipeline of its own.

Справа: список принципов (нумерация 01–04, разделители `--rule`): `Open source / Non-custodial / No trading signals / Public archive of every decision`. Под списком — инфо-карточка с полями `ORGANIZATION / NETWORK / STATUS` (данные — на твоё усмотрение по смыслу проекта, ориентируйся на текст ТЗ выше).

### 4.11 Footer
Тёмная поверхность `--ink`/`--paper`. Слева — лого (светлая версия) + вордмарк + короткое описание: «An open, non-custodial security layer for the Solana ecosystem. Free to use, free to audit, built in public.» Справа — две колонки ссылок: `PRODUCT` (Monitoring feed / Methodology / Quarantine archive / Open API — coming soon) и `ORGANIZATION` (Center for Digital Trust / MD System / Open-source code). Нижняя строка: копирайт + дисклеймер «PATROL DOES NOT PROVIDE FINANCIAL ADVICE» слева, переключатель языков справа.

---

## 5. АДАПТИВНОСТЬ (проверяется отдельно, обязательна)

- Брейкпоинты: ≥1280px (desktop), 768–1279px (tablet), <768px (mobile).
- На mobile: таблицы (4.6–4.8) схлопывают второстепенные колонки (оставить минимум Token / Score / Status), либо превращаются в список карточек — выбери один подход и примени последовательно везде.
- Секции About (4.10) и Hero (4.3) складываются в одну колонку.
- Радар-декор в hero (4.3) и терминал (4.4) на mobile упрощаются или скрываются, если ломают читаемость — приоритет у текста.
- Обязательно: видимый focus-state на всех интерактивных элементах, `prefers-reduced-motion` уважается (отключает любые transition/fade), контраст текста — WCAG AA минимум.

---

## 6. ТЕХНИЧЕСКИЙ СТЕК (обязателен, не заменять без явного согласования)

- **Frontend:** Next.js (App Router), React, TypeScript.
- **Стили:** Tailwind CSS с кастомной темой, где токены из раздела 1 прописаны как CSS-переменные и проброшены в `tailwind.config` (`colors: { ink: 'var(--ink)', ... }`). Никакого styled-components/CSS-in-JS сверху.
- **i18n:** `next-intl`, роутинг `/en/...`, `/ua/...`, `/ru/...`, `/es/...`, словари `/messages/en.json`, `/messages/ua.json`, `/messages/ru.json`, `/messages/es.json`. Весь статический контент (заголовки, методология, лейблы) — через ключи словаря, не хардкодить в JSX. Данные из БД (тикеры, статус-коды) не переводятся, но человекочитаемые формулировки причин отказа (`status_reason`) должны иметь переводы по ключу.
- **Данные и реалтайм:** Supabase (Postgres) + Supabase Realtime для live-обновления таблицы `tokens` без перезагрузки страницы. Схема таблицы `tokens`: `id uuid, token_address text, ticker text, discovered_at timestamptz, state text (monitoring/quarantine/entry_eligible/closed), score numeric, price_change_pct numeric, liquidity_usd numeric, top10_holder_pct numeric, mint_authority_active boolean, freeze_authority_active boolean, status_reason text, updated_at timestamptz`. Отдельное вью `tokens_growth_leaders`.
- **Форматирование чисел/дат:** `Intl.NumberFormat` / `Intl.DateTimeFormat` под текущую локаль — не хардкодить форматы.
- **На этом этапе (без реального backend-ключа):** используй файл `/lib/mock-data.ts` с данными из разделов 4.4/4.7/4.8, структурированными по схеме `tokens` выше, и простой polling/setState-имитацию «live»-эффекта (не обязательно WebSocket) — с комментарием `// MOCK DATA`.

---

## 7. ФАЙЛОВАЯ СТРУКТУРА (ожидаемая, можно скорректировать по конвенциям Next.js App Router, но не ломать разбивку по смыслу)

```
/app/[locale]/page.tsx
/app/[locale]/layout.tsx
/components/Header.tsx
/components/Hero.tsx
/components/TerminalFeed.tsx
/components/StatsBar.tsx
/components/MethodologyGrid.tsx
/components/MonitoringTable.tsx
/components/GrowthTable.tsx
/components/QuarantineGrid.tsx
/components/About.tsx
/components/Footer.tsx
/lib/mock-data.ts
/lib/supabase-client.ts
/messages/en.json
/messages/ua.json
/messages/ru.json
/messages/es.json
/public/assets/logo_icon_ink.png
/public/assets/logo_icon_paper.png
/styles/globals.css   (CSS-переменные из раздела 1)
tailwind.config.ts
```

---

## 8. КРИТЕРИИ ПРИЁМКИ (проверь сам перед тем, как считать задачу выполненной)

- [ ] Все 11 секций из раздела 4 присутствуют, в этом порядке, без пропусков.
- [ ] Ни одного значения цвета вне палитры раздела 1.
- [ ] Ни одной тени, ни одного градиента в итоговом CSS.
- [ ] Все три шрифтовые роли подключены и используются по назначению (не перепутаны местами).
- [ ] 4 языка переключаются, весь статический текст локализован, ни одной хардкод-строки на английском внутри JSX компонентов из раздела 4.
- [ ] Мобильная версия (375px) не ломает ни одну секцию, таблицы читаемы.
- [ ] Нигде на сайте нет полей для приватного ключа/подключения кошелька.
- [ ] Статистика в hero (98.6%, $151M+) сопровождается видимой подписью источника.
- [ ] Lighthouse (или аналог) accessibility-score — не ниже 90.

---

## 9. ЧТО ЯВНО ЗАПРЕЩЕНО

- Добавлять торговые сигналы «купить/продать» где бы то ни было.
- Добавлять секции, не описанные в разделе 4 (никаких «testimonials», «pricing», «FAQ», если явно не попросят отдельно).
- Использовать любой другой шрифт вне трёх заданных ролей.
- Красить что-либо в цвет вне палитры раздела 1, включая ссылки, hover-состояния и скроллбар.
- Оставлять `console.log`, закомментированный мёртвый код или TODO без явной пометки `// MOCK DATA` / `// TODO: <что именно>`.

---

Начни с раздела 7 (файловая структура) и раздела 1–2 (токены темы, шрифты) — это фундамент. Затем реализуй секции строго по порядку раздела 4. После каждой секции — короткий self-check по разделу 8 применительно к этой секции, прежде чем переходить к следующей.

# Генератор рекламных оговорок для АСР

Скрипт собирает текст рекламных оговорок из Excel/CSV-реестра и параметров рекламной кампании.

## Что делает

- Читает реестр оговорок (`.xlsx` или `.csv`) с правилами подключения.
- Добавляет базовые обязательные блоки по категории рекламы (finance/medicine/construction/common).
- Подтягивает реквизиты рекламодателя (наименование, ИНН, ОГРН/ОГРНИП).
- Формирует единый итоговый файл с оговорками для публикации/согласования.

> Важно: это инструмент автоматизации сборки текста, а не замена юридической экспертизы.

## Формат реестра оговорок

Поддерживаемые поля (заголовки колонок должны совпадать):

- `id` — уникальный идентификатор правила.
- `law_scope` — ссылка на норму права/внутренний стандарт.
- `text` — текст оговорки.
- `required` — обязательная оговорка (`true/1/да`).
- `trigger_field` — поле из JSON кампании для условного подключения.
- `trigger_value` — допустимые значения `trigger_field` через запятую.
- `priority` — приоритет сортировки (меньше = выше).
- `additional_notes` — служебные комментарии.

Пример реестра: `examples/disclaimer_registry.csv`.

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ad_disclaimer_generator.py \
  --registry examples/disclaimer_registry.csv \
  --campaign examples/campaign_finance.json \
  --output generated_disclaimer.txt \
  --print
```

## Входной JSON кампании

Минимально рекомендуемые поля:

- `industry`: `common` / `finance` / `medicine` / `construction`
- `advertiser_name`
- `advertiser_inn`
- `advertiser_ogrn`

И любые дополнительные флаги, используемые в `trigger_field` (`has_installment`, `needs_license` и т.д.).

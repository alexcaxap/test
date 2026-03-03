#!/usr/bin/env python3
"""Генератор рекламных оговорок для АСР."""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


@dataclass
class DisclaimerRule:
    rule_id: str
    text: str
    required: bool = False
    trigger_field: str | None = None
    trigger_value: str | None = None
    priority: int = 100
    law_scope: str | None = None
    additional_notes: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "DisclaimerRule":
        return cls(
            rule_id=str(row.get("id", "")).strip(),
            text=str(row.get("text", "")).strip(),
            required=_to_bool(row.get("required", False)),
            trigger_field=_as_optional_str(row.get("trigger_field")),
            trigger_value=_as_optional_str(row.get("trigger_value")),
            priority=_to_int(row.get("priority", 100), default=100),
            law_scope=_as_optional_str(row.get("law_scope")),
            additional_notes=_as_optional_str(row.get("additional_notes")),
        )


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "да", "обязательная"}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def load_rules(path: Path) -> list[DisclaimerRule]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        rows = _load_xlsx(path)
    elif suffix == ".csv":
        rows = _load_csv(path)
    else:
        raise ValueError("Поддерживаются только .xlsx или .csv файлы реестра оговорок")

    rules = [DisclaimerRule.from_row(row) for row in rows]
    return [r for r in rules if r.text]


def _load_xlsx(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet_xml = zf.read("xl/worksheets/sheet1.xml")

    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row in root.findall(".//main:sheetData/main:row", ns):
        cells: dict[int, str] = {}
        for cell in row.findall("main:c", ns):
            ref = cell.get("r", "A1")
            col_idx = _column_index(ref)
            cell_type = cell.get("t")
            value_node = cell.find("main:v", ns)
            if value_node is None or value_node.text is None:
                value = ""
            elif cell_type == "s":
                value = shared_strings[int(value_node.text)] if value_node.text.isdigit() else ""
            else:
                value = value_node.text
            cells[col_idx] = value
        if not cells:
            continue
        max_col = max(cells.keys())
        rows.append([cells.get(i, "") for i in range(max_col + 1)])

    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    result: list[dict[str, Any]] = []
    for data in rows[1:]:
        if not any(data):
            continue
        result.append({header[i]: data[i] if i < len(data) else "" for i in range(len(header))})
    return result


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(xml)
    result: list[str] = []
    for si in root.findall("main:si", ns):
        text_parts = [t.text or "" for t in si.findall(".//main:t", ns)]
        result.append("".join(text_parts))
    return result


def _column_index(cell_ref: str) -> int:
    col = ""
    for ch in cell_ref:
        if ch.isalpha():
            col += ch
        else:
            break
    idx = 0
    for ch in col.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(idx - 1, 0)


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


BASELINE_REQUIRED_BY_INDUSTRY = {
    "common": [
        "Рекламодатель обязан быть идентифицируем: укажите наименование/ФИО и контакты.",
        "Проверьте корректность возрастной маркировки (0+/6+/12+/16+/18+) при необходимости.",
    ],
    "finance": [
        "При рекламе финансовых услуг указывайте организацию, оказывающую услугу, и существенные условия.",
        "Для кредитных продуктов: 'Оценивайте свои финансовые возможности и риски'.",
    ],
    "medicine": [
        "Для медицинских услуг/изделий: 'Имеются противопоказания, необходима консультация специалиста'.",
        "Для БАД: 'Не является лекарственным средством'.",
    ],
    "construction": [
        "Для долевого строительства укажите сведения о проектной декларации и застройщике.",
    ],
}


def match_rule(rule: DisclaimerRule, campaign: dict[str, Any]) -> bool:
    if rule.required:
        return True
    if not rule.trigger_field:
        return False
    if rule.trigger_field not in campaign:
        return False

    actual = str(campaign[rule.trigger_field]).strip().lower()
    if not rule.trigger_value:
        return bool(actual)
    allowed = {item.strip().lower() for item in rule.trigger_value.split(",") if item.strip()}
    return actual in allowed


def render_disclaimer(campaign: dict[str, Any], rules: list[DisclaimerRule]) -> str:
    industry = str(campaign.get("industry", "common")).strip().lower() or "common"

    lines: list[str] = ["# Итоговые рекламные оговорки", ""]
    lines.append("## Базовые обязательные блоки")
    for base_line in BASELINE_REQUIRED_BY_INDUSTRY.get("common", []):
        lines.append(f"- {base_line}")
    for base_line in BASELINE_REQUIRED_BY_INDUSTRY.get(industry, []):
        lines.append(f"- {base_line}")

    selected = sorted((r for r in rules if match_rule(r, campaign)), key=lambda r: (r.priority, r.rule_id))
    lines.extend(["", "## Подключенные оговорки из реестра"])
    if not selected:
        lines.append("- Нет совпавших правил из реестра.")
    for rule in selected:
        scope = f" [{rule.law_scope}]" if rule.law_scope else ""
        lines.append(f"- ({rule.rule_id or 'rule'}){scope} {rule.text}")

    lines.extend(["", "## Реквизиты кампании"])
    lines.append(f"- Рекламодатель: {campaign.get('advertiser_name', '<не указано>')}")
    lines.append(f"- ИНН: {campaign.get('advertiser_inn', '<не указано>')}")
    lines.append(f"- ОГРН/ОГРНИП: {campaign.get('advertiser_ogrn', '<не указано>')}")

    lines.extend(["", "⚠️ Перед публикацией передайте итоговый текст юристу/комплаенсу для финальной валидации."])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Генератор рекламных оговорок для АСР")
    parser.add_argument("--registry", required=True, type=Path, help="Путь к Excel/CSV реестру оговорок")
    parser.add_argument("--campaign", required=True, type=Path, help="JSON с параметрами рекламной кампании")
    parser.add_argument("--output", type=Path, default=Path("generated_disclaimer.txt"), help="Куда сохранить результат")
    parser.add_argument("--print", dest="print_output", action="store_true", help="Вывести результат в STDOUT")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rules = load_rules(args.registry)
    campaign = json.loads(args.campaign.read_text(encoding="utf-8"))

    text = render_disclaimer(campaign, rules)
    args.output.write_text(text, encoding="utf-8")

    if args.print_output:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

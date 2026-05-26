from __future__ import annotations

import hashlib
from typing import Any

from app.services.comparison.xlsx_parser import XlsxSheet, parse_xlsx


def compare_xlsx_workbooks(
    content_a: bytes,
    content_b: bytes,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    workbook_a = parse_xlsx(content_a)
    workbook_b = parse_xlsx(content_b)
    sheets_a = workbook_a.by_name
    sheets_b = workbook_b.by_name

    changes: list[dict[str, Any]] = []
    changed_cells: list[dict[str, Any]] = []

    added_names = set(sheets_b) - set(sheets_a)
    removed_names = set(sheets_a) - set(sheets_b)
    renamed_pairs, unresolved_removed, unresolved_added = _match_renamed_sheets(
        sheets_a, sheets_b, removed_names, added_names
    )

    for old_name, new_name in sorted(renamed_pairs):
        changes.append(
            _change(
                "modified",
                "sheet",
                "high",
                0.94,
                f"Sheet renamed: {old_name!r} -> {new_name!r}",
                {"document": "both", "sheet": old_name},
            )
        )

    for name in sorted(unresolved_added):
        changes.append(
            _change(
                "added",
                "sheet",
                "high",
                0.96,
                f"Sheet added: {name!r}",
                {"document": "b", "sheet": name},
            )
        )
    for name in sorted(unresolved_removed):
        changes.append(
            _change(
                "removed",
                "sheet",
                "high",
                0.96,
                f"Sheet removed: {name!r}",
                {"document": "a", "sheet": name},
            )
        )

    common_names = (set(sheets_a) & set(sheets_b)) | {old for old, _ in renamed_pairs}
    for name in sorted(common_names):
        sheet_a = sheets_a[name]
        target_name = next((new for old, new in renamed_pairs if old == name), name)
        sheet_b = sheets_b[target_name]
        _append_sheet_reorder_change(changes, sheet_a, sheet_b)
        _append_sheet_metadata_changes(changes, sheet_a, sheet_b)
        _append_hidden_dimension_changes(changes, sheet_a, sheet_b)
        _append_row_column_structure_changes(changes, sheet_a, sheet_b)
        _append_cell_changes(changes, changed_cells, sheet_a, sheet_b)

    diagnostics = {
        "sheet_count": {"a": len(workbook_a.sheets), "b": len(workbook_b.sheets)},
        "changed_cells": changed_cells,
        "sheet_summary": _sheet_summary(workbook_a.by_name, workbook_b.by_name, renamed_pairs),
    }
    return changes, diagnostics


def _append_sheet_reorder_change(
    changes: list[dict[str, Any]],
    sheet_a: XlsxSheet,
    sheet_b: XlsxSheet,
) -> None:
    if sheet_a.index == sheet_b.index:
        return
    changes.append(
        _change(
            "modified",
            "structure",
            "medium",
            0.86,
            f"Sheet reordered: {sheet_a.name!r} moved from position {sheet_a.index} "
            f"to {sheet_b.index}",
            {"document": "both", "sheet": sheet_a.name},
        )
    )


def _append_sheet_metadata_changes(
    changes: list[dict[str, Any]],
    sheet_a: XlsxSheet,
    sheet_b: XlsxSheet,
) -> None:
    if sheet_a.hidden != sheet_b.hidden:
        state_a = "hidden" if sheet_a.hidden else "visible"
        state_b = "hidden" if sheet_b.hidden else "visible"
        changes.append(
            _change(
                "modified",
                "metadata",
                "medium",
                0.9,
                f"Sheet visibility changed: {sheet_a.name!r} {state_a} -> {state_b}",
                {"document": "both", "sheet": sheet_a.name},
            )
        )
    for key in ["tab_color"]:
        if sheet_a.metadata.get(key) == sheet_b.metadata.get(key):
            continue
        changes.append(
            _change(
                "modified",
                "metadata",
                "low",
                0.82,
                f"Sheet metadata changed for {sheet_a.name!r}: {key}",
                {"document": "both", "sheet": sheet_a.name},
            )
        )


def _append_hidden_dimension_changes(
    changes: list[dict[str, Any]],
    sheet_a: XlsxSheet,
    sheet_b: XlsxSheet,
) -> None:
    for row in sorted(sheet_b.hidden_rows - sheet_a.hidden_rows):
        changes.append(
            _change(
                "added",
                "metadata",
                "low",
                0.88,
                f"Row hidden: {sheet_a.name}!{row}",
                {"document": "b", "sheet": sheet_a.name, "row": row},
            )
        )
    for row in sorted(sheet_a.hidden_rows - sheet_b.hidden_rows):
        changes.append(
            _change(
                "removed",
                "metadata",
                "low",
                0.88,
                f"Row unhidden: {sheet_a.name}!{row}",
                {"document": "a", "sheet": sheet_a.name, "row": row},
            )
        )
    for column in sorted(sheet_b.hidden_columns - sheet_a.hidden_columns):
        changes.append(
            _change(
                "added",
                "metadata",
                "low",
                0.88,
                f"Column hidden: {sheet_a.name}!{column}",
                {"document": "b", "sheet": sheet_a.name, "column": _column_to_index(column)},
            )
        )
    for column in sorted(sheet_a.hidden_columns - sheet_b.hidden_columns):
        changes.append(
            _change(
                "removed",
                "metadata",
                "low",
                0.88,
                f"Column unhidden: {sheet_a.name}!{column}",
                {"document": "a", "sheet": sheet_a.name, "column": _column_to_index(column)},
            )
        )


def _append_row_column_structure_changes(
    changes: list[dict[str, Any]],
    sheet_a: XlsxSheet,
    sheet_b: XlsxSheet,
) -> None:
    for row in sorted(sheet_b.rows_with_data - sheet_a.rows_with_data):
        changes.append(
            _change(
                "added",
                "structure",
                "medium",
                0.9,
                f"Row inserted with data: {sheet_a.name}!{row}",
                {"document": "b", "sheet": sheet_a.name, "row": row},
            )
        )
    for row in sorted(sheet_a.rows_with_data - sheet_b.rows_with_data):
        changes.append(
            _change(
                "removed",
                "structure",
                "medium",
                0.9,
                f"Row deleted with data: {sheet_a.name}!{row}",
                {"document": "a", "sheet": sheet_a.name, "row": row},
            )
        )

    for column in sorted(sheet_b.columns_with_data - sheet_a.columns_with_data):
        changes.append(
            _change(
                "added",
                "structure",
                "medium",
                0.9,
                f"Column inserted with data: {sheet_a.name}!{column}",
                {
                    "document": "b",
                    "sheet": sheet_a.name,
                    "column": _column_to_index(column),
                },
            )
        )
    for column in sorted(sheet_a.columns_with_data - sheet_b.columns_with_data):
        changes.append(
            _change(
                "removed",
                "structure",
                "medium",
                0.9,
                f"Column deleted with data: {sheet_a.name}!{column}",
                {
                    "document": "a",
                    "sheet": sheet_a.name,
                    "column": _column_to_index(column),
                },
            )
        )


def _append_cell_changes(
    changes: list[dict[str, Any]],
    changed_cells: list[dict[str, Any]],
    sheet_a: XlsxSheet,
    sheet_b: XlsxSheet,
) -> None:
    style_changes = 0
    style_limit = max(20, min(200, len(sheet_a.cells) + len(sheet_b.cells)))
    all_addresses = sorted(set(sheet_a.cells) | set(sheet_b.cells))
    for address in all_addresses:
        cell_a = sheet_a.cells.get(address)
        cell_b = sheet_b.cells.get(address)

        if cell_a is None and cell_b is not None:
            message = f"Cell added: {sheet_a.name}!{address} = {cell_b.value!r}"
            changes.append(
                _change(
                    "added",
                    "text",
                    "medium",
                    0.93,
                    message,
                    {"document": "b", "sheet": sheet_a.name, "cell": address},
                )
            )
            changed_cells.append(_cell_record(sheet_a.name, address, "value", None, cell_b.value))
            continue
        if cell_b is None and cell_a is not None:
            message = f"Cell removed: {sheet_a.name}!{address} = {cell_a.value!r}"
            changes.append(
                _change(
                    "removed",
                    "text",
                    "medium",
                    0.93,
                    message,
                    {"document": "a", "sheet": sheet_a.name, "cell": address},
                )
            )
            changed_cells.append(_cell_record(sheet_a.name, address, "value", cell_a.value, None))
            continue
        if cell_a is None or cell_b is None:
            continue

        if cell_a.formula != cell_b.formula:
            message = (
                f"Formula changed at {sheet_a.name}!{address}: "
                f"{cell_a.formula!r} -> {cell_b.formula!r}"
            )
            changes.append(
                _change(
                    "modified",
                    "formula",
                    "high",
                    0.95,
                    message,
                    {"document": "both", "sheet": sheet_a.name, "cell": address},
                )
            )
            changed_cells.append(
                _cell_record(sheet_a.name, address, "formula", cell_a.formula, cell_b.formula)
            )

        if cell_a.value != cell_b.value:
            message = (
                f"Cell value changed at {sheet_a.name}!{address}: "
                f"{cell_a.value!r} -> {cell_b.value!r}"
            )
            changes.append(
                _change(
                    "modified",
                    "text",
                    "medium",
                    0.95,
                    message,
                    {"document": "both", "sheet": sheet_a.name, "cell": address},
                )
            )
            changed_cells.append(
                _cell_record(sheet_a.name, address, "value", cell_a.value, cell_b.value)
            )

        if (
            style_changes < style_limit
            and cell_a.style_signature != cell_b.style_signature
            and cell_a.value == cell_b.value
            and cell_a.formula == cell_b.formula
        ):
            style_changes += 1
            message = f"Cell format changed at {sheet_a.name}!{address}"
            changes.append(
                _change(
                    "modified",
                    "formatting",
                    "low",
                    0.84,
                    message,
                    {"document": "both", "sheet": sheet_a.name, "cell": address},
                )
            )
            changed_cells.append(
                _cell_record(
                    sheet_a.name,
                    address,
                    "formatting",
                    cell_a.number_format,
                    cell_b.number_format,
                )
            )


def _match_renamed_sheets(
    sheets_a: dict[str, XlsxSheet],
    sheets_b: dict[str, XlsxSheet],
    removed_names: set[str],
    added_names: set[str],
) -> tuple[list[tuple[str, str]], set[str], set[str]]:
    fingerprints_a = {name: _sheet_fingerprint(sheets_a[name]) for name in removed_names}
    fingerprints_b = {name: _sheet_fingerprint(sheets_b[name]) for name in added_names}

    renamed: list[tuple[str, str]] = []
    matched_removed: set[str] = set()
    matched_added: set[str] = set()
    for old_name in sorted(removed_names):
        old_fp = fingerprints_a[old_name]
        for new_name in sorted(added_names):
            if new_name in matched_added:
                continue
            if old_fp != fingerprints_b[new_name]:
                continue
            renamed.append((old_name, new_name))
            matched_removed.add(old_name)
            matched_added.add(new_name)
            break
    return renamed, removed_names - matched_removed, added_names - matched_added


def _sheet_fingerprint(sheet: XlsxSheet) -> str:
    keys = sorted(sheet.cells)[:200]
    payload = "|".join(
        f"{address}:{sheet.cells[address].value}:{sheet.cells[address].formula}" for address in keys
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{len(sheet.cells)}:{digest}"


def _sheet_summary(
    sheets_a: dict[str, XlsxSheet],
    sheets_b: dict[str, XlsxSheet],
    renamed_pairs: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    reverse_rename = {old: new for old, new in renamed_pairs}
    summary = []
    for name, sheet_a in sorted(sheets_a.items()):
        target = reverse_rename.get(name, name)
        sheet_b = sheets_b.get(target)
        if sheet_b is None:
            continue
        summary.append(
            {
                "sheet": name,
                "sheet_b": target,
                "position_a": sheet_a.index,
                "position_b": sheet_b.index,
                "cells_a": len(sheet_a.cells),
                "cells_b": len(sheet_b.cells),
            }
        )
    return summary


def _cell_record(
    sheet: str,
    cell: str,
    kind: str,
    old_value: str | None,
    new_value: str | None,
) -> dict[str, Any]:
    return {
        "sheet": sheet,
        "cell": cell,
        "kind": kind,
        "old": old_value,
        "new": new_value,
    }


def _column_to_index(column_name: str) -> int:
    value = 0
    for char in column_name:
        value = value * 26 + (ord(char.upper()) - ord("A") + 1)
    return value


def _change(
    change_type: str,
    category: str,
    severity: str,
    confidence: float,
    message: str,
    source_ref: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": change_type,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "message": message,
        "source_ref": source_ref,
    }

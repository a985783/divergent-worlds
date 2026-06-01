from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any

from engine.language import json_output_instruction
from engine.schemas import CaseConfig, MaterialSummary
from engine.utils import (
    get_case_path,
    load_prompt,
    render_prompt,
    save_json,
    validate_structured_output,
)


def parse_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_csv_file(path: str | Path) -> str:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    columns = reader.fieldnames or []
    numeric_stats: list[str] = []
    for column in columns:
        values: list[float] = []
        for row in rows:
            raw = (row.get(column) or "").strip()
            try:
                values.append(float(raw))
            except ValueError:
                continue
        if values:
            numeric_stats.append(
                f"- {column}: count={len(values)}, min={min(values):.2f}, "
                f"max={max(values):.2f}, avg={mean(values):.2f}"
            )

    sample_rows = rows[:5]
    lines = [
        f"CSV rows: {len(rows)}",
        f"Columns: {', '.join(columns)}",
        "Numeric column summary:",
        "\n".join(numeric_stats) if numeric_stats else "- none detected",
        "Sample rows:",
        json.dumps(sample_rows, ensure_ascii=False, indent=2),
    ]
    return "\n".join(lines)


def parse_pdf_file(path: str | Path) -> str:
    try:
        import pdfplumber
    except Exception as exc:
        raise RuntimeError("pdfplumber is required to parse PDF files") from exc

    chunks: list[str] = []
    skipped: list[int] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        chunks.append(text)
                except Exception:
                    skipped.append(page_num)
    except Exception as exc:
        raise ValueError(f"PDF 文件打开失败：{exc}。请尝试手动粘贴文本内容。") from exc

    if not chunks:
        raise ValueError(
            "PDF 中未提取到任何文本。可能是扫描件或加密文档，请手动粘贴文本内容。"
        )

    text = "\n\n".join(chunks)
    if skipped:
        text += f"\n\n[注意：第 {', '.join(str(p) for p in skipped)} 页提取失败，已跳过]"
    return text


def parse_material(path_or_text: str | Path, file_type: str | None = None) -> str:
    candidate = Path(path_or_text) if not isinstance(path_or_text, str) else Path(path_or_text)
    if candidate.exists():
        suffix = (file_type or candidate.suffix.lstrip(".")).lower()
        if suffix in {"txt", "md", "markdown"}:
            return parse_text_file(candidate)
        if suffix == "csv":
            return parse_csv_file(candidate)
        if suffix == "pdf":
            return parse_pdf_file(candidate)
        if suffix == "json":
            return json.dumps(json.loads(candidate.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
        raise ValueError(f"Unsupported material type: {suffix}")
    return str(path_or_text)


def detect_forks_from_series(rows: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    """Detect forks using rolling mean baseline deviation (≥25%)."""
    values: list[float] = []
    for row in rows:
        try:
            values.append(float(row[metric]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(values) < 7:
        return []

    baseline = mean(values[: min(7, len(values) // 2)])
    if baseline == 0:
        return []
    forks: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        deviation = (value - baseline) / baseline
        if abs(deviation) >= 0.25:
            forks.append(
                {
                    "index": index,
                    "metric": metric,
                    "method": "rolling_mean",
                    "deviation": f"{deviation:.1%}",
                    "possible_interpretations": ["structural_shift", "temporary_noise"],
                }
            )
    return forks[:5]


def detect_forks_zscore(
    rows: list[dict[str, Any]], metric: str, threshold: float = 2.0
) -> list[dict[str, Any]]:
    """Detect forks using z-score: points where |z| > threshold."""
    values: list[float] = []
    for row in rows:
        try:
            values.append(float(row[metric]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(values) < 7:
        return []

    avg = mean(values)
    if len(values) < 2:
        return []
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    std_dev = variance ** 0.5
    if std_dev == 0:
        return []

    forks: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        z = (value - avg) / std_dev
        if abs(z) >= threshold:
            forks.append(
                {
                    "index": index,
                    "metric": metric,
                    "method": "z_score",
                    "z_score": round(z, 2),
                    "deviation": f"{(value - avg) / avg:.1%}" if avg != 0 else "N/A",
                    "possible_interpretations": [
                        "anomaly" if abs(z) > 3 else "notable_shift",
                        "structural_change",
                    ],
                }
            )
    return forks[:5]


def detect_all_forks(rows: list[dict[str, Any]], metrics: list[str] | None = None) -> list[dict[str, Any]]:
    """Run both rolling_mean and z_score detection across all specified (or auto-detected) numeric metrics."""
    if not rows:
        return []
    if metrics is None:
        # Auto-detect numeric columns
        metrics = []
        for key in rows[0]:
            try:
                float(rows[0][key])
                metrics.append(key)
            except (TypeError, ValueError):
                continue

    all_forks: list[dict[str, Any]] = []
    for metric in metrics:
        all_forks.extend(detect_forks_from_series(rows, metric))
        all_forks.extend(detect_forks_zscore(rows, metric))

    # Deduplicate by (index, metric) keeping richer entries
    seen: dict[tuple[int, str], dict[str, Any]] = {}
    for fork in all_forks:
        key = (fork["index"], fork["metric"])
        if key not in seen:
            seen[key] = fork
    return sorted(seen.values(), key=lambda f: f["index"])[:15]


def summarize_materials(
    texts: list[str],
    llm_client: Any,
    case_config: CaseConfig | None = None,
) -> MaterialSummary:
    template = load_prompt("ingest_summary.md")
    user_prompt = render_prompt(
        template,
        question=case_config.question if case_config else "",
        scenario_type=case_config.scenario_type if case_config else "custom",
        materials="\n\n---\n\n".join(texts),
    )
    summary = validate_structured_output(
        llm_client.generate(
            MaterialSummary,
            [
                {
                    "role": "system",
                    "content": json_output_instruction("MaterialSummary"),
                },
                {"role": "user", "content": user_prompt},
            ],
        ),
        MaterialSummary,
        "MaterialSummary LLM output",
    )
    if case_config:
        save_json(summary, get_case_path(case_config.case_id, "01_material_summary.json"))
    return summary

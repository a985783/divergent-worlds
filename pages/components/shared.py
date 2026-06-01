from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import streamlit as st
from pages.state_manager import state
from engine.schemas import CaseConfig
from engine.utils import ensure_case_dir, get_case_path, save_json
from engine.ingest import parse_material

SCENARIOS = {
    "电商 / 平台经营": "ecommerce",
    "政策 / 宏观": "policy",
    "开源项目趋势": "open_source",
    "舆论 / 品牌": "public_opinion",
    "创作 / 世界观": "creative",
    "自定义": "custom",
}

HORIZONS = {"7 天": "7d", "30 天": "30d", "3 个月": "3m", "1 年": "1y"}

SCENARIO_TEMPLATES: dict[str, dict[str, str]] = {
    "ecommerce": {
        "question": "最近平台经营出现异常波动，是平台算法、需求变化，还是竞品冲击导致？",
        "branches": "算法调整\n需求下降\n竞品冲击\n供给侧变化\n政策调控",
    },
    "policy": {
        "question": "如果某政策未实施/提前/延后实施，关键指标会如何变化？",
        "branches": "现实政策路径\n无政策反事实\n提前实施\n延后实施\n替代方案",
    },
    "open_source": {
        "question": "该开源项目的增长趋势是短期热度还是长期采用？未来会如何演化？",
        "branches": "短期热度消退\n深度技术采用\n资本介入商业化\n维护者倦怠\n生态扩展",
    },
    "public_opinion": {
        "question": "当前舆论事件将如何演化？品牌声誉会受到怎样的影响？",
        "branches": "快速平息\n持续发酵\n二次引爆\n品牌重塑\n竞品借势",
    },
    "creative": {
        "question": "在给定世界观设定下，不同势力/角色的发展路径会如何分化？",
        "branches": "势力 A 崛起\n势力 B 衰落\n联盟形成\n技术突破\n外部冲击",
    },
    "custom": {"question": "", "branches": ""},
}

SUPPORTED_EXTENSIONS = {"txt", "md", "markdown", "csv", "pdf", "json"}
MAX_CONTEXT_FILES = 80
MAX_FILE_CHARS = 60000
MAX_TOTAL_CHARS = 220000

def _activate_case(config: CaseConfig, *, demo: bool) -> None:
    ensure_case_dir(config.case_id)
    save_json(config, get_case_path(config.case_id, "00_case_config.json"))
    state.case_config = config
    
    for k, v in {
        "material_summary": None,
        "material_preview": [],
        "base_world": None,
        "branches": [],
        "profiles": [],
        "actors_by_branch": {},
        "simulation_logs": {},
        "divergence": None,
        "forecast_cards": [],
        "report": "",
    }.items():
        state.set_dynamic(k, v)
        
    state.demo_case_loaded = demo
    state.demo_material_paths = []

def _load_material_preview(paths: list[Path]) -> list[dict[str, str]]:
    preview: list[dict[str, str]] = []
    for path in paths:
        text = parse_material(path, path.suffix.lstrip("."))
        preview.append({"name": path.name, "text": _cap_text(text)})
        if path.suffix.lower() == ".csv":
            try:
                import csv
                with path.open("r", encoding="utf-8-sig", newline="") as h:
                    state.csv_data_rows = list(csv.DictReader(h))
            except Exception as e:
                st.warning(f"CSV 读取失败: {e}")
    return preview

def _collect_materials(uploads: list[object] | None, pasted_text: str, folder_path: str, case_id: str) -> list[dict[str, str]]:
    case_dir = ensure_case_dir(case_id)
    materials: list[dict[str, str]] = []

    if state.csv_data_rows is not None:
        del state.csv_data_rows

    for upload in uploads or []:
        name = getattr(upload, "name", "uploaded")
        suffix = Path(name).suffix.lower().lstrip(".")
        if suffix == "zip":
            materials.extend(_collect_zip_materials(upload, case_dir))
        elif suffix in SUPPORTED_EXTENSIONS:
            target = case_dir / "uploads" / Path(name).name
            target.write_bytes(upload.getbuffer())
            materials.append({"name": name, "text": _cap_text(parse_material(target, suffix))})
            if suffix == "csv":
                try:
                    import csv
                    with target.open("r", encoding="utf-8-sig", newline="") as h:
                        state.csv_data_rows = list(csv.DictReader(h))
                except Exception as e:
                    st.warning(f"CSV 读取失败: {e}")
        else:
            st.warning(f"跳过不支持的文件: {name}")

    if folder_path.strip():
        materials.extend(_collect_folder_materials(Path(folder_path).expanduser()))

    if pasted_text.strip():
        materials.append({"name": "粘贴材料", "text": _cap_text(pasted_text.strip())})

    return _cap_material_set(materials)

def _collect_folder_materials(root: Path) -> list[dict[str, str]]:
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {root}")
    materials: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if len(materials) >= MAX_CONTEXT_FILES:
            break
        if not path.is_file() or path.suffix.lower().lstrip(".") not in SUPPORTED_EXTENSIONS:
            continue
        materials.append({"name": str(path.relative_to(root)), "text": _cap_text(parse_material(path, path.suffix.lstrip(".")))})
        if path.suffix.lower() == ".csv":
            try:
                import csv
                with path.open("r", encoding="utf-8-sig", newline="") as h:
                    state.csv_data_rows = list(csv.DictReader(h))
            except Exception as e:
                st.warning(f"CSV 读取失败: {e}")
    return materials

def _safe_zip_member_name(name: str) -> Path | None:
    candidate = Path(name)
    if name.endswith("/") or candidate.is_absolute() or ".." in candidate.parts:
        return None
    if any(part.startswith(".") or part == "__MACOSX" for part in candidate.parts):
        return None
    return candidate

def _collect_zip_materials(upload: object, case_dir: Path) -> list[dict[str, str]]:
    target_dir = case_dir / "uploads" / f"{Path(getattr(upload, 'name', 'archive')).stem}_zip"
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        archive = ZipFile(BytesIO(upload.getvalue()))
    except BadZipFile as exc:
        raise ValueError("ZIP 文件无法读取") from exc

    materials: list[dict[str, str]] = []
    with archive:
        for member in archive.infolist():
            if len(materials) >= MAX_CONTEXT_FILES:
                break
            safe_name = _safe_zip_member_name(member.filename)
            if not safe_name:
                continue
            suffix = safe_name.suffix.lower().lstrip(".")
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            target = target_dir / safe_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
            materials.append({"name": str(safe_name), "text": _cap_text(parse_material(target, suffix))})
            if suffix == "csv":
                try:
                    import csv
                    with target.open("r", encoding="utf-8-sig", newline="") as h:
                        state.csv_data_rows = list(csv.DictReader(h))
                except Exception as e:
                    st.warning(f"CSV 读取失败: {e}")
    return materials

def _cap_text(text: str) -> str:
    return text[:MAX_FILE_CHARS] + "\n\n[截断]" if len(text) > MAX_FILE_CHARS else text

def _cap_material_set(materials: list[dict[str, str]]) -> list[dict[str, str]]:
    capped: list[dict[str, str]] = []
    total = 0
    for item in materials[:MAX_CONTEXT_FILES]:
        rem = MAX_TOTAL_CHARS - total
        if rem <= 0:
            break
        text = item["text"][:rem]
        capped.append({"name": item["name"], "text": text})
        total += len(text)
    return capped


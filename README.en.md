# Divergent Worlds

[中文](README.md) | English

> Turn one real-world question into multiple parallel futures, pre-register falsifiable forecasts for each future, and use reality feedback to track which world is materializing.

Divergent Worlds is not another one-shot AI report generator. Its stance is simple: do not predict a single future. Generate several plausible futures, make each one concrete and falsifiable, then let reality score them.

It does three things:

1. **Branch**: build a current-world baseline from your background materials, then generate 3-7 mutually distinct counterfactual branches.
2. **Pre-register**: turn each branch into a falsifiable forecast card with probability, validation window, support signals, failure signals, no-information signals, watch actions, and a kill condition.
3. **Calibrate**: store forecast cards in a local ledger, score outcomes with Brier, and learn which kinds of forecasts are useful.

![Five-act workbench and agent simulation stage](docs/assets/workbench.png)

## 1.0 Highlights

- **Visual five-act workbench**: project setup, material parsing, base world, parallel branches, simulation console, branch comparison, and forecast report are connected in one Streamlit app.
- **Worldline cockpit**: worldline map, branch lanes, step-by-step event timeline, and agent array make the simulation process visible.
- **Structured engine**: material summary, base world, branches, world profiles, agents, simulation steps, divergence analysis, forecast cards, and reports are constrained by Pydantic models.
- **Falsifiable forecast cards**: each branch outputs a probability, validation window, support signals, failure signals, no-information signals, watch actions, and kill condition.
- **Forecast calibration ledger**: local SQLite ledger stores forecast cards, supports outcome updates, and calculates Brier scores.
- **Local-first persistence**: intermediate artifacts are saved under `DATA_DIR/cases/`, so interrupted runs can be restored.
- **Bilingual mode**: the frontend supports Chinese and English. English mode also switches model output prompts and report generation to English.

## Project Structure

```text
app.py                    Streamlit entrypoint
engine/                   Core simulation engine
  schemas.py              Pydantic data models
  ingest.py               Material parsing and fork detection
  world_builder.py        T0 base-world builder
  fork_generator.py       Branch generation and diversity checks
  world_profiler.py       Branch sensitivity profiles
  actor_generator.py      Agent generation
  simulation_runner.py    Multi-step simulation and resume logic
  divergence_analyzer.py  Branch comparison and ranking
  forecast_card.py        Falsifiable forecast-card generation
  forecast_ledger.py      SQLite forecast ledger and Brier scoring
  report_generator.py     Markdown and JSON report generation
pages/                    Streamlit UI pages and workbench components
prompts/                  Chinese prompt templates
prompts/en/               English prompt templates
tests/                    Unit, integration, and Streamlit AppTest coverage
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env`:

```bash
LLM_LIVE_ENABLED=false
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_real_api_key_here
LLM_MODEL=gpt-4o-mini
APP_LANGUAGE=en
LLM_OUTPUT_LANGUAGE=en
DATA_DIR=data
```

Run locally:

```bash
streamlit run app.py --server.port 8507
```

Open `http://127.0.0.1:8507`.

## Language Mode

The sidebar language selector switches the UI between Chinese and English. The selection is stored locally under `~/.parallel_worlds/llm_config.json`.

- `APP_LANGUAGE=zh|en` controls the default UI language.
- `LLM_OUTPUT_LANGUAGE=zh|en` controls the target language for model-generated user-facing strings.
- In English mode, the engine loads templates from `prompts/en/`.

Existing saved cases keep their original generated text. New runs follow the current language mode.

## Testing

```bash
ruff check .
python -m pytest
```

## Privacy

Divergent Worlds is local-first. Uploaded files, intermediate states, and final reports are stored under `DATA_DIR`. When you run LLM-backed steps, the app sends project materials and simulation context to your configured OpenAI-compatible model endpoint. Do not upload secrets, identity documents, customer private data, or other sensitive raw text unless your model provider and usage policy allow it.

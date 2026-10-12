import json
from pathlib import Path
from eis_engine.providers import build_catalog
from eis_engine import contracts

root = Path(__file__).resolve().parents[1]
catalog = build_catalog()
(root / "engine/eis_engine/provider_catalog.json").write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n")
for name in ["Request","ImportText","ManualDraft","Analyze","Generate","Profile","AnalysisResult","GeneratedDraft","ChatSend","ChatReply","CustomAgentSave"]:
    schema = getattr(contracts,name).model_json_schema()
    (root / "schemas" / (name+".json")).write_text(json.dumps(schema,ensure_ascii=False,indent=2)+"\n")
print(f"Catalog: {len(catalog['providers'])} adapters, Agno {catalog['agno_version']}")

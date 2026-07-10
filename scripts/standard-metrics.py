#!/usr/bin/env python3
"""Record and report product metrics for standardized consumer projects."""
from __future__ import annotations
import argparse, json
from datetime import date
from pathlib import Path
REL = Path("docs/quality/STANDARD_ADOPTION.json")
def load(project: Path) -> dict:
    path = project / REL; data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("created_at"), str) or not isinstance(data.get("interventions"), list): raise ValueError(f"invalid standard adoption log: {path}")
    return data
def write(project: Path, data: dict) -> None: (project / REL).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--project",action="append",type=Path,required=True); p.add_argument("--record-first-green",action="store_true"); p.add_argument("--self-service",choices=("true","false")); p.add_argument("--record-intervention"); a=p.parse_args()
    if (a.record_first_green and a.record_intervention) or (a.self_service and not a.record_first_green): p.error("record exactly one event; --self-service requires --record-first-green")
    reports=[]
    for project in a.project:
        project=project.resolve(); data=load(project)
        if a.record_first_green:
            if data.get("first_green_at") is not None: raise ValueError(f"first green already recorded: {project / REL}")
            data["first_green_at"]=date.today().isoformat(); data["first_green_self_service"]=a.self_service == "true"; write(project,data)
        elif a.record_intervention: data["interventions"].append({"recorded_at":date.today().isoformat(),"reason":a.record_intervention}); write(project,data)
        reports.append({"project":str(project),"created_at":data["created_at"],"first_green_at":data.get("first_green_at"),"self_service":data.get("first_green_self_service"),"manual_interventions":len(data["interventions"])})
    print(json.dumps(reports,ensure_ascii=False,indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())

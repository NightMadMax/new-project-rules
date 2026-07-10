#!/usr/bin/env python3
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT = Path(__file__).with_name("standard-metrics.py")
class MetricsTests(unittest.TestCase):
 def project(self, root):
  path=Path(root)/"p"/"docs/quality"; path.mkdir(parents=True)
  (path/"STANDARD_ADOPTION.json").write_text('{"schema_version":1,"created_at":"2026-07-10","first_green_at":null,"first_green_self_service":null,"interventions":[]}')
  return path.parents[1]
 def invoke(self,*args): return subprocess.run([sys.executable,str(SCRIPT),*args],capture_output=True,text=True)
 def test_records_and_reports(self):
  with tempfile.TemporaryDirectory() as root:
   p=self.project(root); self.assertEqual(self.invoke("--project",str(p),"--record-first-green","--self-service","true").returncode,0)
   self.assertNotEqual(self.invoke("--project",str(p),"--record-first-green","--self-service","true").returncode,0)
   self.assertEqual(self.invoke("--project",str(p),"--record-intervention","missing migration step").returncode,0)
   data=json.loads((p/"docs/quality/STANDARD_ADOPTION.json").read_text()); self.assertTrue(data["first_green_self_service"]); self.assertEqual(len(data["interventions"]),1)
 def test_rejects_invalid_input(self):
  with tempfile.TemporaryDirectory() as root:
   p=self.project(root); self.assertNotEqual(self.invoke("--project",str(p),"--self-service","true").returncode,0); self.assertNotEqual(self.invoke("--project",str(p),"--record-intervention"," ").returncode,0)
if __name__ == "__main__": unittest.main()

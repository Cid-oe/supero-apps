"""
test_stages.py — regression test verifying that Summit CRM's UI stages
are dynamically resolved from the schema registry and that OPEN_STAGES
is derived by filtering out stages starting with 'Closed'.
"""

import json
import subprocess
import unittest
from pathlib import Path

from _test_lib import load_schemas


class DealStagesResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schemas, error = load_schemas()
        if error:
            raise RuntimeError(error)
        deal_schema = next(s for s in schemas if s.get("name") == "Deal")
        stage_attr = next(
            a for a in deal_schema["attributes"] if a.get("name") == "deal_stage"
        )
        cls.declared_stages = list(stage_attr["values"])
        cls.app_js_path = Path(__file__).resolve().parent.parent / "ui" / "app.js"

    def test_deal_stages_declared_in_schemas_py(self):
        """schemas.py must declare non-empty DEAL_STAGES for deal_stage."""
        self.assertTrue(len(self.declared_stages) > 0)
        self.assertIn("Closed Won", self.declared_stages)
        self.assertIn("Closed Lost", self.declared_stages)

    def test_app_js_resolves_stages_from_schema_registry(self):
        """app.js must dynamically read stage values from SuperoSchemaRegistry."""
        app_js = self.app_js_path.read_text(encoding="utf-8")
        self.assertIn("SuperoSchemaRegistry", app_js)
        self.assertIn("resolveDealStages", app_js)
        self.assertIn("deriveOpenStages", app_js)

        # Execute in node with a custom stage list to verify dynamic derivation
        custom_stages = ["Lead", "Discovery", "Proposal", "Closed Won", "Closed Lost"]
        node_script = f"""
const fs = require('fs');
const code = fs.readFileSync('{self.app_js_path}', 'utf8');
const vm = require('vm');

let context = {{
  setTimeout: () => {{}},
  React: {{ createElement: () => {{}}, useState: (v) => [v, () => {{}}], useEffect: () => {{}} }},
  ReactDOM: {{ createRoot: () => ({{ render: () => {{}} }}) }},
  document: {{ readyState: 'complete', getElementById: () => ({{}}) }},
  window: {{ location: {{}}, addEventListener: () => {{}}, removeEventListener: () => {{}}, scrollTo: () => {{}} }},
  client: {{ isAuthenticated: () => false, can: () => false }},
  services: {{}},
  showToast: () => {{}},
  resolveImageUrl: () => {{}},
  ErrorBoundary: () => {{}},
  formatCurrency: (n) => '$' + n,
  SuperoSchemaRegistry: {{
    get: (name) => {{
      if (name === 'deal' || name === 'summit:deal') {{
        return {{
          attributes: [
            {{ name: 'deal_stage', type: 'string', values: {json.dumps(custom_stages)} }}
          ]
        }};
      }}
      return null;
    }},
    ready: () => Promise.resolve()
  }}
}};

vm.createContext(context);
vm.runInContext(code, context);

const result = vm.runInContext('(function() {{ return {{ stages: window._resolveDealStages(), open: window._deriveOpenStages(window._resolveDealStages()) }}; }})()', context);
console.log(JSON.stringify(result));
"""
        proc = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True,
            text=True,
            check=True,
        )
        res = json.loads(proc.stdout)
        self.assertEqual(res["stages"], custom_stages)
        self.assertEqual(res["open"], ["Lead", "Discovery", "Proposal"])

    def test_app_js_fallback_when_registry_absent(self):
        """When SuperoSchemaRegistry is absent, fallback stages must be used."""
        node_script = f"""
const fs = require('fs');
const code = fs.readFileSync('{self.app_js_path}', 'utf8');
const vm = require('vm');

let context = {{
  setTimeout: () => {{}},
  React: {{ createElement: () => {{}}, useState: (v) => [v, () => {{}}], useEffect: () => {{}} }},
  ReactDOM: {{ createRoot: () => ({{ render: () => {{}} }}) }},
  document: {{ readyState: 'complete', getElementById: () => ({{}}) }},
  window: {{ location: {{}}, addEventListener: () => {{}}, removeEventListener: () => {{}}, scrollTo: () => {{}} }},
  client: {{ isAuthenticated: () => false, can: () => false }},
  services: {{}},
  showToast: () => {{}},
  resolveImageUrl: () => {{}},
  ErrorBoundary: () => {{}},
  formatCurrency: (n) => '$' + n
}};

vm.createContext(context);
vm.runInContext(code, context);

const result = vm.runInContext('(function() {{ return {{ stages: window._resolveDealStages(), open: window._deriveOpenStages(window._resolveDealStages()) }}; }})()', context);
console.log(JSON.stringify(result));
"""
        proc = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True,
            text=True,
            check=True,
        )
        res = json.loads(proc.stdout)
        self.assertEqual(res["stages"], self.declared_stages)
        expected_open = [s for s in self.declared_stages if not s.startswith("Closed")]
        self.assertEqual(res["open"], expected_open)


if __name__ == "__main__":
    unittest.main()

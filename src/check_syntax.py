import sys
import json
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
# Mock LanguageServer before importing AgoLsp to avoid pygls issues in subprocess if needed
# Wait, pygls should be available because we run this inside the nix shell!
from src.AgoLsp import compute_diagnostics

def main():
    source = sys.stdin.read()
    try:
        diags = compute_diagnostics(source)
        out = []
        for d in diags:
            out.append({
                "line": d.range.start.line,
                "col": d.range.start.character,
                "end_line": d.range.end.line,
                "end_col": d.range.end.character,
                "msg": d.message
            })
        print(json.dumps(out))
    except Exception as e:
        import traceback
        # Return exception as a diagnostic
        print(json.dumps([{"line": 0, "col": 0, "end_line": 0, "end_col": 0, "msg": str(e)}]))

if __name__ == "__main__":
    main()

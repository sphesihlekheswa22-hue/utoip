from pathlib import Path
import re
import ast

p = Path("uitop/services/calendar_view.py")
text = p.read_text(encoding="utf-8")
# Fix url="...",)  -> url="...",
fixed = re.sub(r'url="([^"]+)"\)\s*,', r'url="\1",', text)
# Also fix any remaining url("...") forms
fixed = re.sub(r'url\("([^"]+)"\)\s*,', r'url="\1",', fixed)
p.write_text(fixed, encoding="utf-8")
ast.parse(fixed)
print("syntax ok")

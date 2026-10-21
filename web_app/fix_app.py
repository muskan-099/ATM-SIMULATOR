
from pathlib import Path
import ast

path = Path("app.py")
source = path.read_text(encoding="utf-8")

start = source.find("code = r'''")
if start == -1:
    raise SystemExit("Actual Flask code nahi mila.")

start += len("code = r'''")
end = source.find("'''", start)

if end == -1:
    raise SystemExit("Closing marker nahi mila.")

flask_code = source[start:end]

# Check syntax before replacing the file.
ast.parse(flask_code)

backup = Path("app.py.broken-backup")
backup.write_text(source, encoding="utf-8")
path.write_text(flask_code, encoding="utf-8")

print("Fixed app.py successfully.")
print("Backup saved as app.py.broken-backup")

import os
import sys

# Ensure project paths are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAS_DIR = os.path.join(BASE_DIR, "multi-agent-support")
if MAS_DIR not in sys.path:
    sys.path.insert(0, MAS_DIR)

# Run the UI app script
target_file = os.path.join(MAS_DIR, "ui", "app.py")
with open(target_file, "rb") as f:
    code = compile(f.read(), target_file, "exec")
    exec(code, globals())

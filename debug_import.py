import sys
import os

print("Current working directory:", os.getcwd())
engine_path = os.path.join(os.getcwd(), "apps", "engine")
print("Adding to sys.path:", engine_path)
sys.path.append(engine_path)

try:
    print("Attempting to import memory.store...")
    print("Import success!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()

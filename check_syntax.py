#!/usr/bin/env python3
import py_compile
import sys

files_to_check = [
    r"d:\Projects\Zynexra\backend\app.py",
    r"d:\Projects\Zynexra\backend\services\db_service.py"
]

errors_found = False

for file_path in files_to_check:
    try:
        py_compile.compile(file_path, doraise=True)
        print(f"✓ {file_path}: Syntax OK")
    except py_compile.PyCompileError as e:
        print(f"✗ {file_path}: SYNTAX ERROR")
        print(f"  {e}")
        errors_found = True

if errors_found:
    sys.exit(1)
else:
    print("\nAll files passed syntax check!")
    sys.exit(0)

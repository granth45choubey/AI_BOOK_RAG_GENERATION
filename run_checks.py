#!/usr/bin/env python
import sys
import os
import py_compile
import subprocess

os.chdir(r"F:\D_backup\Work\GlobalBook\AI_BOOK_RAG_GENERATION")

print("=" * 60)
print("1. SYNTAX CHECK: streamlit_app.py")
print("=" * 60)
try:
    py_compile.compile('streamlit_app.py', doraise=True)
    print("✓ Syntax check PASSED\n")
    check1_pass = True
except py_compile.PyCompileError as e:
    print(f"✗ Syntax check FAILED:\n{e}\n")
    check1_pass = False

print("=" * 60)
print("2. TEST API CHECK: test_api.py")
print("=" * 60)
if os.path.exists('test_api.py'):
    try:
        result = subprocess.run([sys.executable, 'test_api.py'], 
                              capture_output=True, 
                              text=True, 
                              timeout=60)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        if result.returncode == 0:
            print("✓ test_api.py PASSED")
            check2_pass = True
        else:
            print(f"✗ test_api.py FAILED (exit code: {result.returncode})")
            check2_pass = False
    except subprocess.TimeoutExpired:
        print("✗ test_api.py TIMEOUT (exceeded 60s)")
        check2_pass = False
    except Exception as e:
        print(f"✗ test_api.py ERROR: {e}")
        check2_pass = False
else:
    print("test_api.py not found")
    check2_pass = None

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Syntax Check (py_compile): {'PASS' if check1_pass else 'FAIL'}")
print(f"API Test: {'PASS' if check2_pass else ('FAIL' if check2_pass is False else 'SKIPPED')}")

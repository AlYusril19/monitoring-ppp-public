"""Jalankan uji regresi bot di salinan sementara project.

    python tests/run_regresi.py

* Tidak butuh token, internet, atau router: Telegram & RouterOS ditiru (tests/stubs).
* Project disalin ke folder sementara, jadi datauser.json, app_info.json, dan .env
  asli TIDAK disentuh.
* Keluar dengan kode 1 bila ada uji yang gagal.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {".git", "graphify-out", "__pycache__", ".env", "tests",
        "datauser.json", "app_info.json", "chat_messages.json", "last_notification_time.json"}


def _missing(module):
    try:
        __import__(module)
        return False
    except ImportError:
        return True


def main():
    sandbox = tempfile.mkdtemp(prefix="skytama-test-")
    try:
        for name in os.listdir(ROOT):
            if name in SKIP or name.startswith("datauser.backup"):
                continue
            src, dst = os.path.join(ROOT, name), os.path.join(sandbox, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            elif name.endswith(".py"):
                shutil.copy2(src, dst)
        tests = os.path.join(ROOT, "tests")
        paths = [os.path.join(tests, "stubs")]
        if _missing("pytz") or _missing("dotenv"):
            paths.append(os.path.join(tests, "stubs_fallback"))
        paths.append(sandbox)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(paths), SKYTAMA_TEST_SANDBOX="1",
                   PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, os.path.join(tests, "regresi.py")], cwd=sandbox, env=env)
        return result.returncode
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

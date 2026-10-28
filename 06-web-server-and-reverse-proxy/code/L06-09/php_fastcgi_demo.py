#!/usr/bin/env python3
"""php_fastcgi_demo.py — local php-cgi (FastCGI mode) চালিয়ে nginx + PHP-এর তিনটি ক্লাসিক পরিস্থিতি আসলে দেখায়।

  python3 php_fastcgi_demo.py

temp directory-তে একটি ছোট docroot: index.php, এবং uploads/avatar.jpg (ভেতরে PHP code — একজন আক্রমণকারীর upload)।
php-cgi -b 127.0.0.1:<port> দুইভাবে চালানো হয়: cgi.fix_pathinfo=1 (PHP default) ও =0। nginx-এর ভূমিকায় fcgi_client।
শুধু 127.0.0.1-এ; শেষে php-cgi বন্ধ ও temp directory মোছা। php-cgi না থাকলে স্পষ্ট বার্তা দিয়ে থামে।
"""
from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcgi_client as fc  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_php(fix_pathinfo: int) -> tuple[subprocess.Popen[bytes], int]:
    port = free_port()
    proc = subprocess.Popen(["php-cgi", "-n", "-d", f"cgi.fix_pathinfo={fix_pathinfo}", "-b", f"127.0.0.1:{port}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return proc, port
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("php-cgi did not start")


def short(r: fc.Response) -> str:
    headers, body = r.headers_and_body
    status = headers.get("status", "200")
    printable = "".join(ch for ch in body.decode("utf-8", "replace") if ch.isprintable() and ch != "�")
    text = " ".join(printable.split())[:90]                          # jpeg-এর binary byte বাদ
    return f"{status:<16} {text}"


def run(docroot: Path) -> list[tuple[str, str]]:
    root = docroot.as_posix()
    results = []
    for fix in (1, 0):
        proc, port = start_php(fix)
        try:
            cases = [
                ("correct SCRIPT_FILENAME", fc.nginx_params(f"{root}/index.php", "/index.php?p=1", root)),
                ("SCRIPT_FILENAME missing (fastcgi_params)", fc.nginx_params(None, "/index.php", root)),
                ("/uploads/avatar.jpg/x.php (path-info trick)",
                 fc.nginx_params(f"{root}/uploads/avatar.jpg/x.php", "/uploads/avatar.jpg/x.php", root)),
            ]
            for label, params in cases:
                results.append((f"fix_pathinfo={fix}  {label}", short(fc.request(("127.0.0.1", port), params))))
        finally:
            proc.terminate()
            proc.wait(timeout=10)
    return results


def make_docroot(d: Path) -> Path:
    (d / "uploads").mkdir()
    (d / "index.php").write_text("<?php echo 'TaskFlow blog: PHP ', PHP_VERSION, ', p=', $_GET['p'] ?? '-';",
                                 encoding="utf-8")
    # "ছবি" যার ভেতরে PHP — কৃত্রিম, শুধু একটি লাইন print করে
    (d / "uploads" / "avatar.jpg").write_bytes(b"\xff\xd8\xff\xe0 fake jpeg <?php echo 'UPLOADED FILE EXECUTED AS PHP'; ?>")
    return d


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if shutil.which("php-cgi") is None:
        print("php-cgi not found (Ubuntu: sudo apt install php-cgi; or use php-fpm with fcgi_client.py)")
        return 2
    with tempfile.TemporaryDirectory() as d:
        for label, result in run(make_docroot(Path(d))):
            print(f"{label:<58} → {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

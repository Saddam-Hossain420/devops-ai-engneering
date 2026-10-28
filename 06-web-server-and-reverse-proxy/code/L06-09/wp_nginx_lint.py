#!/usr/bin/env python3
"""wp_nginx_lint.py — WordPress-এর nginx configuration-এর নিরাপত্তা ও সঠিকতা যাচাই (L06-02-এর parser দিয়ে)।

  python3 wp_nginx_lint.py wordpress.conf

যাচাই: PHP location-এ `try_files $uri =404` (বা fastcgi_split_path_info + file যাচাই) — নইলে upload-করা file PHP হিসেবে চলার
ঝুঁকি; SCRIPT_FILENAME আছে কিনা (Ubuntu-র fastcgi_params-এ নেই, fastcgi.conf-এ আছে); uploads-এ PHP deny; dotfile
ও wp-config.php deny; client_max_body_size (media upload); fastcgi_pass যাচাই।
Exit: 0 কোনো error নেই, 1 error আছে, 2 file error।
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "L06-02"))
import nginx_conf as nc  # noqa: E402


def where(d: nc.Directive) -> str:
    return f"{Path(d.file).name}:{d.line}"


def lint(tree: list[nc.Directive]) -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    locations = [d for _, d in nc.walk(tree) if d.name == "location" and d.block is not None]
    php_locs = [d for d in locations if d.first("fastcgi_pass") is not None]
    if not php_locs:
        return [("error", "-", "no-php-location", "no location with fastcgi_pass — PHP will be downloaded as text")]
    for loc in php_locs:
        block = loc.block or []
        try_files = loc.first("try_files")
        has_404 = try_files is not None and try_files.args[-1:] == ["=404"]
        if not has_404:
            out.append(("error", where(loc), "php-no-file-check",
                        "PHP location without 'try_files $uri =404;' — /uploads/x.jpg/y.php may run x.jpg as PHP "
                        "(depends on cgi.fix_pathinfo / security.limit_extensions)"))
        includes = [d.args[0] for d in block if d.name == "include" and d.args]
        params = {d.args[0] for d in block if d.name == "fastcgi_param" and d.args}
        via_conf = any(i.endswith("fastcgi.conf") or i.endswith("fastcgi-php.conf") for i in includes)
        if "SCRIPT_FILENAME" not in params and not via_conf:
            out.append(("error", where(loc), "no-script-filename",
                        "SCRIPT_FILENAME not set — 'include fastcgi_params' alone lacks it (use fastcgi.conf or set it) "
                        "→ PHP answers 'No input file specified.'"))
        if loc.args and loc.args[0] not in ("~", "~*"):
            out.append(("warning", where(loc), "php-location-not-regex", "PHP location is usually '~ \\.php$'"))
    upload_deny = any("uploads" in " ".join(d.args) and d.first("deny") is not None and "php" in " ".join(d.args)
                      for d in locations)
    if not upload_deny:
        out.append(("warning", "-", "uploads-php-allowed",
                    "no 'location ~* /wp-content/uploads/.*\\.php$ { deny all; }' — defense in depth for uploads"))
    if not any(d.first("deny") is not None and d.args and "\\." in d.args[-1] and "php" not in d.args[-1]
               for d in locations):
        out.append(("warning", "-", "dotfiles-allowed", "no deny for dotfiles (.git, .env, .htaccess)"))
    if not any(d.name == "client_max_body_size" for _, d in nc.walk(tree)):
        out.append(("warning", "-", "upload-size", "client_max_body_size not set — media uploads over 1m get 413"))
    root_loc = next((d for d in locations if d.args == ["/"]), None)
    tf = root_loc.first("try_files") if root_loc else None
    if tf is None or not any("index.php" in a for a in tf.args):
        out.append(("warning", where(root_loc) if root_loc else "-", "no-front-controller",
                    "location / should have 'try_files $uri $uri/ /index.php?$args;' (pretty permalinks)"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint a WordPress nginx configuration.")
    ap.add_argument("config", type=Path)
    a = ap.parse_args(argv)
    try:
        # include expand নয়: site file-এর `include fastcgi.conf` nginx-এর prefix (/etc/nginx)-এর সাপেক্ষে —
        # এখানে include-টাই যাচাইয়ের বিষয় (কোনটা include হচ্ছে), তার বিষয়বস্তু নয়
        findings = lint(nc.parse(a.config.read_text(encoding="utf-8"), str(a.config)))
    except (OSError, nc.ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for level, w, code, msg in findings:
        print(f"{level.upper():<7} {w:<20} {code:<24} {msg}")
    print(f"{len(findings)} finding(s)")
    return 1 if any(f[0] == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())

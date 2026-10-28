#!/usr/bin/env python3
"""Lab 06-A verification — আপনার lab06a.conf (offline) ও চলমান nginx (--live, VM-এ) যাচাই।

  python3 check_a.py ~/lab06a/lab06a.conf              # শুধু config (যেকোনো OS)
  python3 check_a.py ~/lab06a/lab06a.conf --live       # সাথে 127.0.0.1:80-এ আসল request (nginx চালু থাকতে হবে)

Offline: catch-all default_server (444), দুটি site, hidden-file deny, try_files … =404, server_select.py-র ভবিষ্যদ্বাণী।
Live: একই request-গুলো আসল nginx-এ পাঠিয়ে ভবিষ্যদ্বাণীর সাথে মেলানো।
"""
from __future__ import annotations

import argparse
import http.client
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "06-web-server-and-reverse-proxy" / "code" / "L06-03"))
import server_select as ss  # noqa: E402

nc = ss.nc


def offline(conf: Path) -> list[tuple[bool, str]]:
    tree = nc.parse(conf.read_text(encoding="utf-8"), str(conf))
    servers = ss.servers_of(tree)
    out = []
    defaults = [s for s in servers if any(l.default and l.port == 80 for l in s.listens)]
    ret = defaults[0].directive.first("return") if defaults else None
    out.append((bool(defaults) and ret is not None and ret.args[:1] == ["444"],
                "a default_server on port 80 that returns 444"))
    names = {n for s in servers for n in s.names}
    out.append(({"site-a.lab", "site-b.lab"} <= names, "server_name site-a.lab and site-b.lab exist"))
    for host in ("site-a.lab", "site-b.lab"):
        try:
            srv, _ = ss.select_server(servers, host, 80)
        except LookupError:
            out.append((False, f"{host}: no server on port 80"))
            continue
        locs = [d for d in srv.directive.find("location") if d.block is not None]
        deny = any(d.first("deny") is not None and d.args and "\\." in d.args[-1] for d in locs)
        tf = [d.first("try_files") for d in locs if d.first("try_files") is not None]
        out.append((deny, f"{host}: hidden files (.git, .env) denied"))
        out.append((any(t.args[-1:] == ["=404"] for t in tf), f"{host}: try_files ends with =404"))
        out.append((srv.directive.first("root") is not None, f"{host}: has a root"))
    srv, why = ss.select_server(servers, "203.0.113.9", 80)
    out.append(("default_server" in why, "unknown Host goes to the default_server"))
    return out


def get(host: str, path: str) -> tuple[int | None, str]:
    conn = http.client.HTTPConnection("127.0.0.1", 80, timeout=5)
    try:
        conn.request("GET", path, headers={"Host": host})
        r = conn.getresponse()
        return r.status, r.read(200).decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as exc:            # 444 = response ছাড়াই connection বন্ধ
        return None, type(exc).__name__
    finally:
        conn.close()


def live() -> list[tuple[bool, str]]:
    out = []
    for host in ("site-a.lab", "site-b.lab"):
        status, body = get(host, "/")
        out.append((status == 200 and host.split(".")[0] in body, f"live {host}/ → 200 with its own page"))
        out.append((get(host, "/.env")[0] in (403, 404), f"live {host}/.env → 403/404"))
        out.append((get(host, "/no-such-page")[0] == 404, f"live {host}/no-such-page → 404"))
    status, detail = get("203.0.113.9", "/")
    # 444 = connect সফল, তারপর উত্তর ছাড়া বন্ধ (RemoteDisconnected)। Refused মানে nginx-ই নেই — সেটা PASS নয়।
    closed = status is None and detail in ("RemoteDisconnected", "BadStatusLine", "ConnectionResetError")
    out.append((closed, f"live unknown Host → connection closed without response (444) [{status or detail}]"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    try:
        results = offline(a.config) + (live() if a.live else [])
    except (OSError, nc.ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

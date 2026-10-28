#!/usr/bin/env python3
"""proxy_uri.py — nginx `proxy_pass` upstream-এ কোন URI পাঠায়, documentation-এর নিয়মে হিসাব করে।

  python3 proxy_uri.py --location /api/ --proxy-pass http://127.0.0.1:8000/ --uri /api/tasks?done=true
  python3 proxy_uri.py --table          # সাধারণ সব রূপের তুলনা

নিয়ম (https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass):
  - proxy_pass-এ URI অংশ আছে (host-এর পরে '/' বা আরও কিছু): location-এর মেলা prefix বাদ দিয়ে সেই URI বসে
  - URI অংশ নেই: client-এর URI যেমন আছে তেমন যায়
  - proxy_pass-এ variable থাকলে, বা regex location-এ: URI বদলানো হয় না (client-এর URI, বা লেখা URI হুবহু)
"""
from __future__ import annotations

import argparse
import sys
from urllib.parse import urlsplit


def upstream_uri(location: str, proxy_pass: str, request_uri: str, regex_location: bool = False) -> str:
    parts = urlsplit(proxy_pass)
    uri_part = proxy_pass[len(f"{parts.scheme}://{parts.netloc}"):]          # host:port-এর পরের সব
    path, sep, query = request_uri.partition("?")
    if "$" in proxy_pass:
        if not uri_part:
            return request_uri
        return uri_part                                                       # variable সহ লেখা URI হুবহু (query নিজে যোগ করতে হয়)
    if not uri_part:
        return request_uri
    if regex_location:
        raise ValueError('"proxy_pass" cannot have URI part in location given by regular expression')
    if not path.startswith(location):
        raise ValueError(f"request {path!r} does not match location {location!r}")
    return uri_part + path[len(location):] + (sep + query)


CASES = [
    ("/api/", "http://app:8000", "/api/tasks"),
    ("/api/", "http://app:8000/", "/api/tasks"),
    ("/api", "http://app:8000/", "/api/tasks"),
    ("/api/", "http://app:8000/v1/", "/api/tasks?done=true"),
    ("/api/", "http://app:8000/v1", "/api/tasks"),
    ("/api", "http://app:8000/v1/", "/apiary"),
]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Which URI does nginx proxy_pass send upstream?")
    ap.add_argument("--location")
    ap.add_argument("--proxy-pass")
    ap.add_argument("--uri")
    ap.add_argument("--regex-location", action="store_true")
    ap.add_argument("--table", action="store_true")
    a = ap.parse_args(argv)
    rows = CASES if a.table else [(a.location, a.proxy_pass, a.uri)]
    if not a.table and None in rows[0]:
        ap.error("--location, --proxy-pass and --uri are required (or use --table)")
    for loc, pp, uri in rows:
        try:
            result = upstream_uri(loc, pp, uri, a.regex_location)
        except ValueError as exc:
            result = f"ERROR: {exc}"
        print(f"location {loc:<6} proxy_pass {pp:<22} {uri:<22} → {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

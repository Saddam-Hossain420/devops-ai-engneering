#!/usr/bin/env python3
"""presign.py — S3 presigned URL (Signature Version 4, query-string auth) নিজে বানিয়ে দেখা — কোনো network call নেই।

  python3 presign.py --bucket my-bucket --key reports/a.csv --region ap-south-1 --expires 300 --profile-env
  (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN env থেকে — অস্থায়ী credential হলে token-ও URL-এ যায়)

শেখার উদ্দেশ্যে: boto3-এর `generate_presigned_url` এটাই করে। URL-এ secret থাকে না, থাকে signature; যার কাছে URL আছে
সে মেয়াদ পর্যন্ত সেই একটি object পড়তে পারে — URL-টিই এখন একটি "চাবি"। সঠিকতা AWS documentation-এর প্রকাশিত
উদাহরণের signature-এর সাথে মিলিয়ে test-এ যাচাই করা।
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sys
from datetime import UTC, datetime
from urllib.parse import quote


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def signing_key(secret: str, day: str, region: str, service: str) -> bytes:
    k = _hmac(("AWS4" + secret).encode(), day)
    k = _hmac(k, region)
    k = _hmac(k, service)
    return _hmac(k, "aws4_request")


def presign(bucket: str, key: str, region: str, access_key: str, secret: str, when: datetime, expires: int,
            session_token: str | None = None, host: str | None = None, method: str = "GET") -> str:
    if not 1 <= expires <= 604800:
        raise ValueError("expires must be 1..604800 seconds (7 days) for SigV4")
    host = host or f"{bucket}.s3.{region}.amazonaws.com"
    amz_date, day = when.strftime("%Y%m%dT%H%M%SZ"), when.strftime("%Y%m%d")
    scope = f"{day}/{region}/s3/aws4_request"
    params = {"X-Amz-Algorithm": "AWS4-HMAC-SHA256", "X-Amz-Credential": f"{access_key}/{scope}",
              "X-Amz-Date": amz_date, "X-Amz-Expires": str(expires), "X-Amz-SignedHeaders": "host"}
    if session_token:
        params["X-Amz-Security-Token"] = session_token
    query = "&".join(f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}" for k, v in sorted(params.items()))
    path = "/" + quote(key, safe="/-_.~")
    canonical = "\n".join([method, path, query, f"host:{host}", "", "host", "UNSIGNED-PAYLOAD"])
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    signature = hmac.new(signing_key(secret, day, region, "s3"), to_sign.encode(), hashlib.sha256).hexdigest()
    return f"https://{host}{path}?{query}&X-Amz-Signature={signature}"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Build an S3 presigned GET URL locally (SigV4).")
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--expires", type=int, default=300)
    ap.add_argument("--profile-env", action="store_true", help="read credentials from AWS_* environment variables")
    a = ap.parse_args(argv)
    if not a.profile_env or not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        print("error: set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY (e.g. eval \"$(aws configure export-credentials "
              "--format env)\") and pass --profile-env", file=sys.stderr)
        return 2
    try:
        url = presign(a.bucket, a.key, a.region, os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"],
                      datetime.now(UTC), a.expires, os.environ.get("AWS_SESSION_TOKEN"))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(url)
    print(f"valid for {a.expires} s — anyone holding this URL can GET the object until then", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

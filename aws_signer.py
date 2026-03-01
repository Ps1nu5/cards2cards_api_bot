from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signing_key(secret_access_key: str, date: str, region: str, service: str) -> bytes:
    k_date    = _hmac_sha256(("AWS4" + secret_access_key).encode("utf-8"), date)
    k_region  = _hmac_sha256(k_date,    region)
    k_service = _hmac_sha256(k_region,  service)
    return      _hmac_sha256(k_service, "aws4_request")


def sign_request(
    method:            str,
    url:               str,
    body:              str,
    access_key_id:     str,
    secret_access_key: str,
    session_token:     str,
    region:            str,
    service:           str = "execute-api",
) -> dict[str, str]:
    parsed   = urllib.parse.urlparse(url)
    host     = parsed.netloc
    path     = parsed.path or "/"
    raw_qs   = parsed.query

    now        = datetime.now(timezone.utc)
    amz_date   = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    canon_hdr: dict[str, str] = {"host": host, "x-amz-date": amz_date}
    has_body = bool(body)
    if has_body:
        canon_hdr["content-type"] = "application/json"
    if session_token:
        canon_hdr["x-amz-security-token"] = session_token

    canonical_headers_str = "".join(f"{k}:{v}\n" for k, v in sorted(canon_hdr.items()))
    signed_headers_str    = ";".join(sorted(canon_hdr.keys()))

    if raw_qs:
        pairs    = urllib.parse.parse_qsl(raw_qs, keep_blank_values=True)
        canon_qs = urllib.parse.urlencode(sorted(pairs))
    else:
        canon_qs = ""

    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    canonical_request = "\n".join([
        method.upper(), path, canon_qs,
        canonical_headers_str, signed_headers_str, payload_hash,
    ])

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    signing_key = _get_signing_key(secret_access_key, date_stamp, region, service)
    signature   = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 "
        f"Credential={access_key_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers_str}, "
        f"Signature={signature}"
    )

    result: dict[str, str] = {"Authorization": authorization, "x-amz-date": amz_date}
    if has_body:
        result["Content-Type"] = "application/json"
    if session_token:
        result["x-amz-security-token"] = session_token
    return result

"""Convert backend/openapi.json into a Postman Collection v2.1.

Run after `make openapi`:

    uv run python scripts/openapi_to_postman.py

Writes docs/postman/kyros-api.postman_collection.json plus a local
environment file. Auth endpoints carry a test script that captures
access/refresh tokens into collection variables, so every other request
authenticates automatically after one login call.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
OUT_DIR = REPO_ROOT / "docs" / "postman"

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

# Tag → human-readable folder name. Untagged routes fall back by path prefix.
FOLDER_TITLES = {
    "auth": "Auth",
    "users": "Users",
    "notifications": "Notifications",
    "wellness": "Wellness — Reminders & Health Sync",
    "abha": "ABHA (ABDM)",
    "consultations": "Consultations (Patient)",
    "payments": "Payments",
    "lab-reports": "Lab Reports (Patient)",
    "biomarker-trends": "Biomarker Trends",
    "patient-prescriptions": "Prescriptions (Patient)",
    "patient-education": "Education (Patient)",
    "pre-consult-report": "Pre-Consult Report (Patient)",
    "doctor-profile": "Doctor — Profile",
    "doctor-schedule": "Doctor — Schedule",
    "doctor-patients": "Doctor — Patients",
    "doctor-consultations": "Doctor — Consultations",
    "doctor-prescriptions": "Doctor — Prescriptions",
    "doctor-lab-review": "Doctor — Lab Review",
    "doctor-pre-consult-report": "Doctor — Pre-Consult Reports",
    "doctor-video": "Doctor — Video",
    "admin-analytics": "Admin API — Analytics",
    "admin-content": "Admin API — Content",
    "public": "Public (Website)",
    "webhooks": "Webhooks",
}

# Auth endpoints whose JSON responses carry tokens worth capturing.
TOKEN_CAPTURE_SCRIPT = [
    "const data = pm.response.json ? (() => { try { return pm.response.json(); } catch { return {}; } })() : {};",
    "if (data.access_token) { pm.collectionVariables.set('accessToken', data.access_token); }",
    "if (data.refresh_token) { pm.collectionVariables.set('refreshToken', data.refresh_token); }",
]

# Runs on every request in the collection.
COLLECTION_TEST_SCRIPT = [
    "pm.test('no server error (status < 500)', () => pm.expect(pm.response.code).to.be.below(500));",
    "const path = '/' + pm.request.url.path.join('/');",
    "if (path.startsWith('/v1')) {",
    "  pm.test('PHI cache protection: Cache-Control is no-store', () => {",
    "    pm.expect(pm.response.headers.get('Cache-Control')).to.eql('no-store');",
    "  });",
    "}",
]

# Synthetic dev fixtures from `make seed` (scripts/seed_dev.py). All users share
# password DemoPass123! and are phone-verified. Dev/test data only — these
# accounts never exist in production.
DEMO_VARIABLES = [
    {"key": "demoPassword", "value": "DemoPass123!"},
    {"key": "demoPatientPhone", "value": "+919700000001"},
    {"key": "demoPatientEmail", "value": "sunita.reddy@dev.kyros.local"},
    {"key": "demoDoctorPhone", "value": "+919800000001"},
    {"key": "demoDoctorEmail", "value": "dr.meera@dev.kyros.local"},
    {"key": "demoCoordinatorPhone", "value": "+919800000010"},
    {"key": "demoCoordinatorEmail", "value": "ananya.menon@dev.kyros.local"},
    {"key": "otp", "value": ""},
    # MailHog — the dev SMTP inbox (docker-compose `mailhog` service)
    {"key": "mailhogUrl", "value": "http://localhost:8025"},
]

# Extra request descriptions appended to what the OpenAPI spec provides.
OTP_DELIVERY_NOTE = (
    "OTP delivery: the optional `channel` field ('whatsapp' | 'email' | 'sms') "
    "selects which channel is tried first; omit it for the default order "
    "WhatsApp → email → SMS. The remaining channels stay as fallback if the "
    "chosen one fails. `channel: email` returns 422 email_channel_unavailable "
    "if the account has no registered email (or the email fallback is "
    "disabled via KYROS_OTP_EMAIL_FALLBACK_ENABLED). All channels deliver the "
    "same 6-digit code; verification is identical regardless of channel. In "
    "local dev emailed codes land in MailHog ({{mailhogUrl}})."
)
OP_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("/v1/auth/signup", "post"): OTP_DELIVERY_NOTE
    + " With KYROS_DEBUG=true the response also includes otp_hint.",
    ("/v1/auth/send-otp", "post"): OTP_DELIVERY_NOTE,
    ("/v1/auth/verify-otp", "post"): (
        "Verifies the code regardless of which channel delivered it "
        "(WhatsApp, email, or SMS) — single Redis-stored HMAC per phone."
    ),
}

# Pre-filled bodies so auth works out of the box against a seeded dev backend.
DEMO_BODIES: dict[tuple[str, str], dict[str, str]] = {
    ("/v1/auth/login", "post"): {
        "email_or_phone": "{{demoPatientPhone}}",
        "password": "{{demoPassword}}",
    },
    ("/v1/auth/send-otp", "post"): {"phone": "{{demoPatientPhone}}"},
    ("/v1/auth/verify-otp", "post"): {"phone": "{{demoPatientPhone}}", "otp": "{{otp}}"},
    ("/v1/auth/refresh", "post"): {"refresh_token": "{{refreshToken}}"},
}


def _resolve(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    name = ref.rsplit("/", 1)[-1]
    return components.get(name, {})


def example_from_schema(
    schema: dict[str, Any], components: dict[str, Any], depth: int = 0
) -> Any:
    if depth > 6 or not isinstance(schema, dict):
        return None
    schema = _resolve(schema, components)
    if "example" in schema:
        return schema["example"]
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    if schema.get("enum"):
        return schema["enum"][0]
    for combinator in ("anyOf", "oneOf", "allOf"):
        if combinator in schema:
            options = [s for s in schema[combinator] if s.get("type") != "null"]
            if options:
                return example_from_schema(options[0], components, depth + 1)
            return None
    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        return {
            key: example_from_schema(prop, components, depth + 1)
            for key, prop in schema.get("properties", {}).items()
        }
    if schema_type == "array":
        item = example_from_schema(schema.get("items", {}), components, depth + 1)
        return [item] if item is not None else []
    if schema_type == "string":
        fmt = schema.get("format", "")
        return {
            "uuid": "00000000-0000-0000-0000-000000000000",
            "date-time": "2026-01-01T00:00:00Z",
            "date": "2026-01-01",
            "email": "user@example.com",
        }.get(fmt, "string")
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0
    if schema_type == "boolean":
        return True
    return None


def build_url(path: str, parameters: list[dict[str, Any]], components: dict[str, Any]) -> dict[str, Any]:
    segments = [seg for seg in path.split("/") if seg]
    postman_segments: list[str] = []
    variables: list[dict[str, Any]] = []
    for seg in segments:
        if seg.startswith("{") and seg.endswith("}"):
            name = seg[1:-1]
            postman_segments.append(f":{name}")
            variables.append({"key": name, "value": "", "description": "(required path param)"})
        else:
            postman_segments.append(seg)

    query: list[dict[str, Any]] = []
    for param in parameters:
        if param.get("in") != "query":
            continue
        value = example_from_schema(param.get("schema", {}), components)
        query.append(
            {
                "key": param["name"],
                "value": "" if value is None else str(value),
                "disabled": not param.get("required", False),
                "description": param.get("description", ""),
            }
        )

    url: dict[str, Any] = {
        "raw": "{{baseUrl}}/" + "/".join(postman_segments)
        + ("?" + "&".join(f"{q['key']}={q['value']}" for q in query if not q["disabled"]) if any(not q["disabled"] for q in query) else ""),
        "host": ["{{baseUrl}}"],
        "path": postman_segments,
    }
    if query:
        url["query"] = query
    if variables:
        url["variable"] = variables
    return url


def build_request(
    path: str, method: str, op: dict[str, Any], components: dict[str, Any]
) -> dict[str, Any]:
    parameters = op.get("parameters", [])
    headers: list[dict[str, Any]] = [
        {
            "key": param["name"],
            "value": "",
            "description": param.get("description", ""),
            "disabled": not param.get("required", False),
        }
        for param in parameters
        if param.get("in") == "header"
    ]

    description = op.get("description") or op.get("summary", "")
    extra = OP_DESCRIPTIONS.get((path, method))
    if extra:
        description = f"{description}\n\n{extra}" if description else extra

    request: dict[str, Any] = {
        "method": method.upper(),
        "header": headers,
        "url": build_url(path, parameters, components),
        "description": description,
    }

    body = op.get("requestBody", {})
    content = body.get("content", {})
    if "application/json" in content:
        demo = DEMO_BODIES.get((path, method))
        if demo is not None:
            example: Any = demo
        else:
            example = example_from_schema(
                content["application/json"].get("schema", {}), components
            )
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(example, indent=2) if example is not None else "{}",
            "options": {"raw": {"language": "json"}},
        }
    elif "multipart/form-data" in content:
        schema = _resolve(content["multipart/form-data"].get("schema", {}), components)
        request["body"] = {
            "mode": "formdata",
            "formdata": [
                {
                    "key": key,
                    "type": "file" if prop.get("format") == "binary" else "text",
                    "value": "" if prop.get("format") == "binary" else str(example_from_schema(prop, components) or ""),
                }
                for key, prop in schema.get("properties", {}).items()
            ],
        }
    elif "application/x-www-form-urlencoded" in content:
        schema = _resolve(content["application/x-www-form-urlencoded"].get("schema", {}), components)
        request["body"] = {
            "mode": "urlencoded",
            "urlencoded": [
                {"key": key, "value": str(example_from_schema(prop, components) or "")}
                for key, prop in schema.get("properties", {}).items()
            ],
        }

    # No bearer token on auth/public/health endpoints; admin and coord portals
    # use session cookies, so the collection-level bearer is disabled there too.
    if (
        path.startswith(("/v1/auth", "/v1/public", "/admin", "/coord", "/healthz", "/readyz"))
        or path.startswith("/v1/webhooks")
    ):
        request["auth"] = {"type": "noauth"}

    return request


def folder_for(path: str, op: dict[str, Any]) -> str:
    tags = op.get("tags") or []
    if tags:
        return FOLDER_TITLES.get(tags[0], tags[0].replace("-", " ").title())
    if path.startswith("/admin"):
        return "Admin Portal (HTMX, session cookie)"
    if path.startswith("/coord"):
        return "Coordinator Portal (HTMX, session cookie)"
    return "Misc"


def _demo_request(
    name: str,
    method: str,
    path: str,
    *,
    body: dict[str, str] | None = None,
    tests: list[str],
    description: str = "",
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "method": method,
        "header": [],
        "url": {
            "raw": "{{baseUrl}}" + path,
            "host": ["{{baseUrl}}"],
            "path": [seg for seg in path.split("/") if seg],
        },
        "description": description,
        "auth": {"type": "noauth"} if path.startswith(("/v1/auth", "/health", "/readyz")) else None,
    }
    if request["auth"] is None:
        del request["auth"]
    if body is not None:
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    return {
        "name": name,
        "request": request,
        "response": [],
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}],
    }


def _login_tests(role: str) -> list[str]:
    return [
        f"pm.test('login as demo {role} succeeded', () => pm.response.to.have.status(200));",
        "const data = pm.response.json();",
        "pm.test('access and refresh tokens returned', () =>",
        "  pm.expect(Boolean(data.access_token && data.refresh_token)).to.be.true);",
        "pm.collectionVariables.set('accessToken', data.access_token);",
        "pm.collectionVariables.set('refreshToken', data.refresh_token);",
    ]


def build_demo_folder() -> dict[str, Any]:
    """Smoke-test folder runnable top-to-bottom against a seeded dev backend.

    Requires `make bootstrap` (or `make dev` + `make migrate` + `make seed`).
    """
    return {
        "name": "00 — Demo & Smoke (seeded dev data)",
        "description": (
            "Run top-to-bottom with the Collection Runner against a dev backend "
            "after `make seed`. Demo accounts (synthetic, dev-only):\n\n"
            "| Role | Phone | Email |\n|---|---|---|\n"
            "| Patient | +919700000001…05 | sunita.reddy@dev.kyros.local … |\n"
            "| Doctor | +919800000001…03 | dr.meera@dev.kyros.local … |\n"
            "| Coordinator | +919800000010 | ananya.menon@dev.kyros.local |\n\n"
            "Password for all: `DemoPass123!`. With KYROS_DEBUG=true the signup "
            "response includes `otp_hint`, so OTP flows are testable without SMS.\n\n"
            "OTP delivery chain: WhatsApp → email → SMS. In dev the email lands in "
            "MailHog ({{mailhogUrl}}); the 'Email OTP 1/3..3/3' requests run the "
            "whole flow hands-free."
        ),
        "item": [
            _demo_request(
                "Liveness — GET /healthz",
                "GET",
                "/healthz",
                tests=["pm.test('backend is up', () => pm.response.to.have.status(200));"],
            ),
            _demo_request(
                "Readiness — GET /readyz (probes Postgres + Redis)",
                "GET",
                "/readyz",
                tests=[
                    "pm.test('ready', () => pm.response.to.have.status(200));",
                    "const data = pm.response.json();",
                    "pm.test('database ok', () => pm.expect(data.database).to.eql('ok'));",
                    "pm.test('redis ok', () => pm.expect(data.redis).to.eql('ok'));",
                ],
            ),
            _demo_request(
                "Login as demo patient",
                "POST",
                "/v1/auth/login",
                body={"email_or_phone": "{{demoPatientPhone}}", "password": "{{demoPassword}}"},
                tests=_login_tests("patient"),
            ),
            _demo_request(
                "Get my profile (verifies bearer token)",
                "GET",
                "/v1/users/me",
                tests=[
                    "pm.test('authenticated', () => pm.response.to.have.status(200));",
                ],
            ),
            _demo_request(
                "Email OTP 1/3 — request OTP via email channel",
                "POST",
                "/v1/auth/send-otp",
                body={"phone": "{{demoPatientPhone}}", "channel": "email"},
                tests=[
                    "pm.test('OTP issued', () => pm.response.to.have.status(200));",
                ],
                description=(
                    "`channel: email` asks for email delivery first (WhatsApp/SMS "
                    "remain as fallback). The code lands in MailHog in dev — run "
                    "2/3 next to fetch it automatically. Omit `channel` for the "
                    "default WhatsApp-first chain. Note the 60s per-phone resend "
                    "cooldown (429 otp_cooldown)."
                ),
            ),
            {
                "name": "Email OTP 2/3 — fetch code from MailHog (dev inbox)",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{mailhogUrl}}/api/v2/search?kind=to&query={{demoPatientEmail}}",
                        "host": ["{{mailhogUrl}}"],
                        "path": ["api", "v2", "search"],
                        "query": [
                            {"key": "kind", "value": "to"},
                            {"key": "query", "value": "{{demoPatientEmail}}"},
                        ],
                    },
                    "auth": {"type": "noauth"},
                    "description": (
                        "Reads the demo patient's inbox from MailHog (the dev SMTP "
                        "server, UI at {{mailhogUrl}}) and extracts the 6-digit code "
                        "from the latest 'Your Kyros verification code' email into "
                        "the {{otp}} variable. Dev-only — production uses real SMTP."
                    ),
                },
                "response": [],
                "event": [
                    {
                        "listen": "test",
                        "script": {
                            "type": "text/javascript",
                            "exec": [
                                "pm.test('MailHog reachable', () => pm.response.to.have.status(200));",
                                "const data = pm.response.json();",
                                "pm.test('an OTP email was delivered', () => pm.expect(data.total).to.be.above(0));",
                                "// MailHog stores raw MIME: undo quoted-printable soft line breaks, then",
                                "// pull the code out of the HTML body (rendered as >123456<).",
                                "const body = (data.items[0].Content.Body || '').replace(/=\\r?\\n/g, '');",
                                "const m = body.match(/>(\\d{6})</);",
                                "pm.test('6-digit code extracted into {{otp}}', () => pm.expect(m).to.not.eql(null));",
                                "if (m) { pm.collectionVariables.set('otp', m[1]); }",
                            ],
                        },
                    }
                ],
            },
            _demo_request(
                "Email OTP 3/3 — verify code (logs in as patient)",
                "POST",
                "/v1/auth/verify-otp",
                body={"phone": "{{demoPatientPhone}}", "otp": "{{otp}}"},
                tests=_login_tests("patient (via email OTP)"),
                description=(
                    "Verifies the emailed code through the same path as WhatsApp/SMS "
                    "codes (one Redis-stored HMAC per phone) and returns tokens. "
                    "Max 5 attempts per code; the code expires after 5 minutes."
                ),
            ),
            _demo_request(
                "Login as demo doctor",
                "POST",
                "/v1/auth/login",
                body={"email_or_phone": "{{demoDoctorPhone}}", "password": "{{demoPassword}}"},
                tests=_login_tests("doctor"),
                description="Overwrites {{accessToken}} — subsequent requests run as the doctor.",
            ),
            _demo_request(
                "Login as demo coordinator",
                "POST",
                "/v1/auth/login",
                body={
                    "email_or_phone": "{{demoCoordinatorPhone}}",
                    "password": "{{demoPassword}}",
                },
                tests=_login_tests("coordinator"),
                description="Overwrites {{accessToken}} — subsequent requests run as the coordinator.",
            ),
            _demo_request(
                "Refresh tokens (rotation — old refresh token is revoked)",
                "POST",
                "/v1/auth/refresh",
                body={"refresh_token": "{{refreshToken}}"},
                tests=_login_tests("session refresh"),
            ),
        ],
    }


def main() -> None:
    spec = json.loads((BACKEND_ROOT / "openapi.json").read_text(encoding="utf-8"))
    components = spec.get("components", {}).get("schemas", {})

    folders: dict[str, list[dict[str, Any]]] = {}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if method not in HTTP_METHODS:
                continue
            item: dict[str, Any] = {
                "name": op.get("summary") or f"{method.upper()} {path}",
                "request": build_request(path, method, op, components),
                "response": [],
            }
            if path.startswith("/v1/auth") and method == "post":
                item["event"] = [
                    {
                        "listen": "test",
                        "script": {"type": "text/javascript", "exec": TOKEN_CAPTURE_SCRIPT},
                    }
                ]
            folders.setdefault(folder_for(path, op), []).append(item)

    ordered = sorted(folders.items(), key=lambda kv: (kv[0] != "Auth", kv[0]))
    collection = {
        "info": {
            "name": "Kyros API",
            "description": (
                "Generated from backend/openapi.json — regenerate with "
                "`make openapi && make postman`.\n\n"
                "Quick start: run the '00 — Demo & Smoke' folder against a seeded "
                "dev backend (`make bootstrap` or `make seed`). Logging in via any "
                "auth request auto-captures {{accessToken}}/{{refreshToken}}.\n\n"
                "Demo accounts (synthetic dev fixtures, password `DemoPass123!`): "
                "patients +919700000001..05, doctors +919800000001..03, "
                "coordinator +919800000010. None of these exist in production.\n\n"
                "Every request asserts status < 500, and every /v1 response is "
                "checked for `Cache-Control: no-store` (PHI cache protection)."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "event": [
            {
                "listen": "test",
                "script": {"type": "text/javascript", "exec": COLLECTION_TEST_SCRIPT},
            }
        ],
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}],
        },
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000"},
            {"key": "accessToken", "value": ""},
            {"key": "refreshToken", "value": ""},
            *DEMO_VARIABLES,
        ],
        "item": [
            build_demo_folder(),
            *({"name": name, "item": items} for name, items in ordered),
        ],
    }

    environment = {
        "name": "Kyros — Local",
        "values": [
            {"key": "baseUrl", "value": "http://localhost:8000", "enabled": True},
            {"key": "accessToken", "value": "", "enabled": True},
            {"key": "refreshToken", "value": "", "enabled": True},
            *({**v, "enabled": True} for v in DEMO_VARIABLES),
        ],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coll_path = OUT_DIR / "kyros-api.postman_collection.json"
    env_path = OUT_DIR / "kyros-local.postman_environment.json"
    coll_path.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
    env_path.write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    total = sum(len(items) for items in folders.values())
    print(f"wrote {coll_path} ({total} requests in {len(folders)} folders)")
    print(f"wrote {env_path}")


if __name__ == "__main__":
    main()

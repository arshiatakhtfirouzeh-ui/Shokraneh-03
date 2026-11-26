import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from helpers import D0, END, month_data, rich_week

from shokraneh import ai, analytics

REPORT = {
    "title": "گزارش",
    "sections": [
        {"h": "نگاه کلی", "text": "هفته‌ی خوبی بود."},
        {"h": "بازخورد", "items": ["یکی", "دو", "", 3]},
        {"nope": 1},
        "junk",
    ],
}


class Handler(BaseHTTPRequestHandler):
    calls: list = []
    plan: dict = {}

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        Handler.calls.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        status, payload = Handler.plan.get(self.path, (404, {"error": {"message": "nope"}}))
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):  # silence
        pass


@pytest.fixture()
def server():
    Handler.calls, Handler.plan = [], {}
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=lambda: srv.serve_forever(poll_interval=0.02), daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def anthropic_reply(text):
    return (200, {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"})


def openai_reply(text):
    return (200, {"choices": [{"message": {"role": "assistant", "content": text}}]})


def cfg(base, provider="anthropic", **kw):
    return {"provider": provider, "api_key": "sk-test-123", "base_url": base, "consent": True, **kw}


# ------------------------------------------------------------------ readiness / url
def test_is_ready_rules():
    assert not ai.is_ready({})
    assert not ai.is_ready({"provider": "anthropic", "api_key": "k", "consent": False})
    assert not ai.is_ready({"provider": "anthropic", "api_key": "", "consent": True})
    assert ai.is_ready({"provider": "anthropic", "api_key": "k", "consent": True})
    assert not ai.is_ready({"provider": "openai", "api_key": "", "consent": True})
    assert ai.is_ready({"provider": "openai", "api_key": "", "consent": True, "base_url": "http://localhost:11434/v1"})
    assert not ai.is_ready({"provider": "offline", "api_key": "k", "consent": True})
    assert ai.effective({"provider": "anthropic"})["model"] == "claude-sonnet-5-5"


@pytest.mark.parametrize("url", ["http://example.com/v1", "ftp://x.y", "", "javascript:alert(1)"])
def test_bad_urls_rejected(url):
    with pytest.raises(ai.AIError) as e:
        ai.complete({"provider": "openai", "api_key": "k", "consent": True, "base_url": url or "x"}, "s", "u")
    assert e.value.code == "url"


# ------------------------------------------------------------------ providers (real HTTP on loopback)
def test_anthropic_roundtrip(server):
    Handler.plan["/v1/messages"] = anthropic_reply("```json\n" + json.dumps(REPORT, ensure_ascii=False) + "\n```")
    dg = analytics.week_digest(rich_week(), D0, END, END)
    rep = ai.generate_weekly(cfg(server), dg, "fa", "سارا", True)
    assert rep["source"] == "ai" and rep["title"] == "گزارش"
    assert [s["h"] for s in rep["sections"]] == ["نگاه کلی", "بازخورد"]
    assert rep["sections"][1]["items"] == ["یکی", "دو", "3"]
    path, headers, body = Handler.calls[0]
    assert path == "/v1/messages"
    assert headers["x-api-key"] == "sk-test-123" and headers["anthropic-version"] == "2023-06-01"
    assert body["model"] == "claude-sonnet-5-5" and body["max_tokens"] >= 1000 and "Persian" in body["system"]
    payload = json.loads(body["messages"][0]["content"])
    assert payload["week"]["days"] == 7 and payload["entries"] and payload["person"] == "سارا"


def test_openai_compatible_roundtrip(server):
    Handler.plan["/v1/chat/completions"] = openai_reply(json.dumps(REPORT, ensure_ascii=False))
    data, s, e = month_data()
    ms = analytics.month_stats(data, s, e, today=e)
    rep = ai.generate_monthly(cfg(server + "/v1", "openai", model="my-model"), ms, "en", "", False)
    assert rep["source"] == "ai"
    path, headers, body = Handler.calls[0]
    assert path == "/v1/chat/completions" and headers["authorization"] == "Bearer sk-test-123"
    assert body["model"] == "my-model" and "max_tokens" not in body and "temperature" not in body
    assert [m["role"] for m in body["messages"]] == ["system", "user"] and "English" in body["messages"][0]["content"]


def test_base_url_variants(server):
    Handler.plan["/v1/messages"] = anthropic_reply("{}")
    for base in (server, server + "/", server + "/v1", server + "/v1/messages"):
        Handler.calls.clear()
        ai.complete(cfg(base), "s", "u")
        assert Handler.calls[0][0] == "/v1/messages"
    Handler.plan["/chat/completions"] = openai_reply("{}")
    Handler.calls.clear()
    ai.complete(cfg(server, "openai", api_key=""), "s", "u")  # local server, no key, no auth header
    assert Handler.calls[0][0] == "/chat/completions" and "authorization" not in Handler.calls[0][1]


@pytest.mark.parametrize(
    "status,code",
    [(401, "auth"), (403, "auth"), (404, "notfound"), (400, "badrequest"), (429, "rate"), (500, "server"), (503, "server"), (418, "http")],
)
def test_http_errors(server, status, code):
    Handler.plan["/v1/messages"] = (status, {"error": {"type": "x", "message": "details here"}})
    with pytest.raises(ai.AIError) as e:
        ai.complete(cfg(server), "s", "u")
    assert e.value.code == code and ("details here" in e.value.detail)
    assert e.value.text("fa") and e.value.text("en")


def test_bad_bodies(server):
    Handler.plan["/v1/messages"] = (200, b"<html>oops</html>")
    with pytest.raises(ai.AIError) as e:
        ai.complete(cfg(server), "s", "u")
    assert e.value.code == "parse"
    Handler.plan["/v1/messages"] = (200, {"content": []})
    with pytest.raises(ai.AIError) as e2:
        ai.complete(cfg(server), "s", "u")
    assert e2.value.code == "parse"
    Handler.plan["/v1/messages"] = anthropic_reply("sorry, I cannot help")
    dg = analytics.week_digest(rich_week(), D0, END, END)
    with pytest.raises(ai.AIError) as e3:
        ai.generate_weekly(cfg(server), dg, "en")
    assert e3.value.code == "parse"


def test_network_error():
    with pytest.raises(ai.AIError) as e:
        ai.complete(cfg("http://127.0.0.1:9"), "s", "u")  # nothing listens on the discard port
    assert e.value.code in ("network", "timeout")


def test_ping(server):
    Handler.plan["/v1/messages"] = anthropic_reply("ok")
    assert ai.ping(cfg(server)) == "ok"
    assert Handler.calls[0][2]["max_tokens"] == 16


def test_missing_key_or_offline():
    with pytest.raises(ai.AIError) as e:
        ai.complete({"provider": "anthropic", "api_key": "", "consent": True}, "s", "u")
    assert e.value.code == "config"
    with pytest.raises(ai.AIError):
        ai.complete({"provider": "offline"}, "s", "u")


# ------------------------------------------------------------------ parsing
def test_extract_json_variants():
    obj = {"title": "t", "sections": [{"h": "a", "text": "با } آکولاد { داخل رشته"}]}
    raw = json.dumps(obj, ensure_ascii=False)
    assert ai.extract_json(raw) == obj
    assert ai.extract_json("```json\n" + raw + "\n```") == obj
    assert ai.extract_json("Sure! Here you go:\n" + raw + "\nHope it helps.") == obj
    assert ai.extract_json(raw[:-20]) is None
    assert ai.extract_json("no json") is None


def test_normalize_report_limits():
    rep = ai.normalize_report({"sections": [{"h": "x" * 500, "text": "y" * 5000, "items": [str(i) for i in range(20)]}] * 12}, "Default")
    assert rep["title"] == "Default" and len(rep["sections"]) == 8
    s = rep["sections"][0]
    assert len(s["h"]) == 80 and len(s["text"]) == 1600 and len(s["items"]) == 8
    with pytest.raises(ai.AIError):
        ai.normalize_report({"sections": []})
    with pytest.raises(ai.AIError):
        ai.normalize_report([])


# ------------------------------------------------------------------ privacy of the payload
def test_payload_privacy_and_budget():
    data = rich_week()
    dg = analytics.week_digest(data, D0, END, END)
    text = json.dumps(ai.weekly_payload(dg, "fa", "سارا"), ensure_ascii=False)
    assert "مامان" not in text  # loved-ones' names are never sent
    assert "api_key" not in text and "sk-" not in text
    assert dg["neglected"] and json.loads(text)["loved_ones_not_contacted_for_3_weeks"] == 1

    big = rich_week()
    for i in range(7):
        d = D0.fromordinal(D0.toordinal() + i).isoformat()
        big["morning"][d]["answers"]["m7"] = "کلمه " * 300
        big["night"].setdefault(d, {"answers": {}})["answers"]["n8"] = "متن " * 300
    dg2 = analytics.week_digest(big, D0, END, END)
    legend, rows = ai._entries(dg2["texts"], "fa")
    assert len(json.dumps(rows, ensure_ascii=False)) < 9000
    assert all(len(r["a"]) <= 170 * 5 for r in rows)


def test_monthly_payload_shape():
    data, s, e = month_data()
    ms = analytics.month_stats(data, s, e, today=e)
    p = ai.month_payload(ms, "en", "Ali")
    assert p["energy_1_to_10"]["logged_days"] == 30 and p["average_energy_by_weekday"]
    assert all(k in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday") for k in p["average_energy_by_weekday"])
    json.dumps(p)  # serialisable

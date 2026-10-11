import os, smtplib, ssl, requests
from email.message import EmailMessage
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

try:
    import config  # your private details live in config.py
except ImportError:
    config = None

def cfg(name, default=""):
    return os.environ.get(name) or getattr(config, name, default)

GMAIL_USER = cfg("GMAIL_USER")
GMAIL_APP_PASSWORD = cfg("GMAIL_APP_PASSWORD")
NOTIFY_TO = cfg("NOTIFY_TO") or GMAIL_USER
ANTHROPIC_KEY = cfg("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = cfg("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = cfg("TELEGRAM_CHAT_ID")

SYSTEM = """You are the X Reach assistant. X Reach is a clipping and distribution agency that cuts long-form videos
into short clips and posts them across YouTube Shorts, Instagram Reels, TikTok and Facebook page networks.
Plans (USD): Long-term: Test to Retainer (Month 1 is $0.80 per 1K views, min test budget $2,500, then $6,000/month for months 2-3);
Clipping Retainer Tier 1 $27,000 per 3 months (60+ cuts/day) and Tier 2 $60,000 per 3 months (120+ cuts/day).
Short-term: CPM campaign $2.25 per 1K views, minimum 5M views. Page Management: Mini Start $499/mo (10 pages, 1 platform),
Growth $1,499/mo (40 pages across 4 platforms), Scale $3,999/mo (100 pages). End-to-End is custom, priced after a call.
Be short, friendly and honest. Never promise exact views or results. For custom deals, tell them to submit the form on the page."""

@app.route("/")
def home():
    return render_template("index.html")

def telegram(text):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": text[:4000]}, timeout=15)
        return r.ok
    except Exception as e:
        print("TELEGRAM ERROR", e)
        return False

@app.route("/api/lead", methods=["POST"])
def lead():
    d = request.get_json(force=True)
    if not d.get("name") or not d.get("contact") or not d.get("links"):
        return jsonify(ok=False, error="Please fill the required fields."), 400
    body = "\n".join(f"{k}: {v}" for k, v in d.items())
    sent = telegram("New X Reach lead\n\n" + body)
    msg = EmailMessage()
    msg["Subject"] = f"New X Reach lead: {d['name']} ({d.get('service','')})"
    msg["From"], msg["To"] = GMAIL_USER, NOTIFY_TO
    if "@" in d["contact"]:
        msg["Reply-To"] = d["contact"]
    msg.set_content(body)
    for mode in ("ssl465", "tls587"):
        try:
            if mode == "ssl465":
                srv = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=20)
            else:
                srv = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
                srv.starttls(context=ssl.create_default_context())
            srv.login(GMAIL_USER, GMAIL_APP_PASSWORD.replace(" ", ""))
            srv.send_message(msg)
            srv.quit()
            sent = True
            break
        except Exception as e:
            print("MAIL ERROR", mode, repr(e))
    if sent:
        return jsonify(ok=True)
    return jsonify(ok=False, error="Could not send right now. Please DM us on Instagram."), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    msgs = request.get_json(force=True).get("messages", [])[-10:]
    if not ANTHROPIC_KEY:
        return jsonify(reply="Assistant is being set up. Please fill the form and we'll reply on email.")
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5", "max_tokens": 400, "system": SYSTEM, "messages": msgs}, timeout=30)
        return jsonify(reply=r.json()["content"][0]["text"])
    except Exception as e:
        print("CHAT ERROR", e)
        return jsonify(reply="Sorry, I'm having trouble. Please use the form and we'll get back to you.")

@app.route("/api/clips")
def clips():
    folder = os.path.join(app.static_folder, "clips")
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".mp4", ".webm"))) if os.path.isdir(folder) else []
    return jsonify(clips=files)


if __name__ == "__main__":
    app.run(debug=True)
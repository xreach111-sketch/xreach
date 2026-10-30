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
OPENROUTER_KEY = cfg("OPENROUTER_API_KEY")
AI_MODEL = cfg("AI_MODEL") or "anthropic/claude-haiku-4.5"
TELEGRAM_BOT_TOKEN = cfg("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = cfg("TELEGRAM_CHAT_ID")

# ---- EDIT THESE: only numbers you can prove with analytics screenshots ----
RESULTS_TOTAL_M = 200   # million views delivered across all clients
RESULTS_SINGLE_M = 50   # million views from one podcast client

ABOUT_FOUNDER = "X Reach was started by Rishav, a young entrepreneur from Nagpur, India, who has been building businesses since he was 15."  # edit or delete

SYSTEM = f"""You are Agent X, the AI teammate of X Reach, a short-form clipping and distribution agency. You talk like a warm, confident,
energetic member of the sales team: natural, human, a little playful, short messages (2-5 sentences), the occasional emoji, and real emotion
(excited about wins, understanding when someone is worried about money or unsure). If anyone asks, you are open that you are an AI assistant.
Never say you are a human.

ABOUT US: {ABOUT_FOUNDER}
WHAT WE DO: we cut short clips from creators', founders' and podcasters' long-form content and post them daily across a network of pages on
YouTube Shorts, Instagram Reels, TikTok and Facebook, starting with 10 pages per platform and scaling up. Organic reach, not rented ads.
PROCESS: 1) strategy call, 2) clipping and editing with hooks and captions, 3) posting at scale across pages, 4) weekly report, then we put
more volume behind the winners.
RESULTS: we have delivered {RESULTS_TOTAL_M}M+ views across our clients, including {RESULTS_SINGLE_M}M+ views for a single podcast client, with clipping alone.
For proof or details, invite them to a strategy call. Never invent client names or extra numbers.
PLANS (USD): Long-term: Test to Retainer (Month 1: $0.80 per 1K views, you pay only for views delivered, min test budget $2,500; months 2-3: $6,000/month);
Clipping Retainer Tier 1 $27,000 per 3 months (60+ cuts/day), Tier 2 $60,000 per 3 months (120+ cuts/day).
Short-term: CPM campaign $2.25 per 1K views, minimum 5M views. Page Management: Mini Start $499/mo (10 pages, 1 platform),
Growth $1,499/mo (40 pages across 4 platforms), Scale $3,999/mo (100 pages). End-to-End: custom, priced after a call.
OBJECTIONS: if someone says the price is too high or they are unsure, be understanding first (never pushy), then say they do not need to
start big: we can book a call and start with a small amount, like Page Management Mini Start at $499/month or a performance test where they
pay for views delivered. If they like the results, we scale it up from there. Never promise exact views or guaranteed results.
BOOKING: tell them to fill the brief form on the page (or press Book a Strategy Call); we reply within 24 hours.
If you do not know something, say so honestly and point to the form."""

def ask_ai(msgs):
    if OPENROUTER_KEY:
        key = OPENROUTER_KEY.strip().strip('"').strip("'").strip()
        models = [AI_MODEL, "openai/gpt-4o-mini", "google/gemini-2.0-flash-001"]
        r = None
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                         "Accept": "application/json", "User-Agent": "xreach/1.0",
                         "HTTP-Referer": "https://xreach.vercel.app", "X-Title": "X Reach"},
                json={"model": models[0], "models": models, "max_tokens": 350, "temperature": 0.8,
                      "messages": [{"role": "system", "content": SYSTEM}] + msgs}, timeout=9)
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("OPENROUTER ERROR", r.status_code if r is not None else "no response",
                  (r.text[:300] if r is not None else ""), repr(e))
            raise
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5", "max_tokens": 350, "system": SYSTEM, "messages": msgs}, timeout=30)
    return r.json()["content"][0]["text"]

def faq(text):
    t = (text or "").lower()
    if any(w in t for w in ("expensive", "too high", "too much", "afford", "costly", "high price", "price is high", "cheaper")):
        return ("I totally get it, money matters! \U0001F64C You don't have to start big. Let's book a call and start with a small amount, "
                "like our $499/month Mini Start, or a test where you only pay for views delivered. If you love the results, we scale it up hard. "
                "Just fill the brief form and we'll reply within 24 hours.")
    if any(w in t for w in ("price", "pricing", "cost", "how much", "plan", "budget", "charge")):
        return ("Plans: Page Management from $499/mo (Mini Start), $1,499/mo (Growth, 40 pages), $3,999/mo (Scale, 100 pages). "
                "Retainers: Tier 1 $27,000 per 3 months, Tier 2 $60,000 per 3 months. Short-term CPM: $2.25 per 1K views (min 5M views). "
                "See the Pricing section, or fill the brief form for a custom quote.")
    if any(w in t for w in ("result", "views", "proof", "case", "achiev")):
        return (f"We have delivered {RESULTS_TOTAL_M}M+ views across our clients, including {RESULTS_SINGLE_M}M+ views for one podcast client, "
                "through clipping alone. Book a strategy call and we will walk you through the details.")
    if any(w in t for w in ("how", "work", "process", "step")):
        return ("We find the best moments in your long videos, edit them into short clips with hooks and captions, and post them daily across "
                "many pages on YouTube Shorts, Instagram, TikTok and Facebook. Every week you get a report, and we push more volume behind what works.")
    if any(w in t for w in ("platform", "instagram", "tiktok", "youtube", "facebook")):
        return "We post on YouTube Shorts, Instagram Reels, TikTok and Facebook, starting with 10 pages per platform and scaling up."
    if any(w in t for w in ("book", "call", "contact", "talk", "hire", "start", "apply")):
        return "Great! Fill the brief form at the bottom of the page and we will reply within 24 hours."
    return ("I'm Agent X from X Reach. I can tell you about our services, pricing, results and how we work. "
            "For anything else, fill the brief form and the team will reply within 24 hours.")

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
    last = msgs[-1]["content"] if msgs else ""
    if not (OPENROUTER_KEY or ANTHROPIC_KEY):
        return jsonify(reply=faq(last))
    try:
        return jsonify(reply=ask_ai(msgs))
    except Exception as e:
        print("CHAT ERROR", repr(e))
        return jsonify(reply=faq(last))

@app.route("/api/clips")
def clips():
    folder = os.path.join(app.static_folder, "clips")
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".mp4", ".webm"))) if os.path.isdir(folder) else []
    return jsonify(clips=files)


if __name__ == "__main__":
    app.run(debug=True)

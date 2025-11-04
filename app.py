import os
from flask import Flask, request, jsonify
from supabase import create_client
import requests

app = Flask(__name__)

# ENV (set these on Railway / locally)
SUPABASE_URL = os.getenv("https://zqqnmzxceknnhprltzuz.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpxcW5tenhjZWtubmhwcmx0enV6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIxNTk3MjksImV4cCI6MjA3NzczNTcyOX0.rG2yHURv8FLM_0LCShnvHBOPKLACIxHxwhiv9kcZBWw")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")         # Meta token
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")       # Meta phone number id
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "verify_token_example")  # webhook verify token

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Simple webhook verification endpoint required by Meta
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    try:
        # Navigate typical structure from WhatsApp cloud API
        entries = data.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    from_number = msg.get("from")
                    text_obj = msg.get("text", {})
                    message_text = text_obj.get("body", "").strip().lower()

                    # Check DB
                    res = supabase.table("users").select("*").eq("phone_number", from_number).execute()
                    user_data = res.data or []

                    if len(user_data) == 0 and message_text == "hello":
                        # New user who said "hello"
                        supabase.table("users").insert({"phone_number": from_number}).execute()
                        preset = build_preset_message()
                        send_whatsapp_text(from_number, preset)

                    elif len(user_data) == 1 and user_data[0].get("name") is None:
                        # If previously asked for name and user replies, consider storing it
                        # (This branch optional based on your flow)
                        name_candidate = message_text.title()
                        supabase.table("users").update({"name": name_candidate}).eq("phone_number", from_number).execute()
                        # You chose to not auto-reply further per original requirement
                    else:
                        # Do nothing for further messages
                        pass

    except Exception as e:
        print("Webhook handling error:", e)

    return jsonify({"status": "received"}), 200


def build_preset_message():
    # Customize this text. Line breaks allowed.
    return (
        "Hey 👋 Thanks for messaging!\n\n"
        "Work number: +91-XXXXXXXXXX\n"
        "Email: youremail@example.com\n\n"
        "Connect with me:\n"
        "Twitter: https://twitter.com/yourhandle\n"
        "LinkedIn: https://www.linkedin.com/in/yourhandle\n"
        "Instagram: https://instagram.com/yourhandle\n\n"
        "What I do: I build web apps, automations, and data tools."
    )


def send_whatsapp_text(to, message):
    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code >= 400:
        print("WhatsApp API error:", r.status_code, r.text)
    return r


@app.route("/", methods=["GET"])
def home():
    return "WhatsApp automation running", 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

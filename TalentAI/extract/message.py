import os
import json
import re
import smtplib
import psycopg2
from email.mime.text import MIMEText
from openai import OpenAI
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")

# CONFIGS from .env
XAI_API_KEY = os.getenv("XAI_API_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
twilio_client = TwilioClient(TWILIO_SID, TWILIO_AUTH_TOKEN)

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group() if match else None

def extract_phone(text):
    match = re.search(r'(\+?\d[\d\s-]{7,})', text)
    return match.group().strip() if match else None

def send_email(recipient, body):
    msg = MIMEText(body)
    msg["Subject"] = "Hello from your assistant"
    msg["From"] = EMAIL_USER
    msg["To"] = recipient

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
    print("✅ Email sent to", recipient)

def send_sms(recipient, body):
    twilio_client.messages.create(
        body=body,
        from_=TWILIO_PHONE,
        to=recipient
    )
    print("✅ SMS sent to", recipient)

def detect_and_store(text):
    prompt = f"""
Check if the following text contains:
- Email
- Phone number
- LinkedIn profile link

Text: "{text}"

Respond in JSON like: {{"email": true/false, "phone": true/false, "linkedin": true/false}}
"""

    response = client.chat.completions.create(
        model="grok-3-beta",
        messages=[
            {"role": "system", "content": "You are Grok, a highly intelligent assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("❌ Bad JSON response:", response.choices[0].message.content)
        return

    # Insert the raw text into database
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("INSERT INTO mitai (text) VALUES (%s)", (text,))
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Inserted into DB:", text)

    message = "Hey there! Thanks for sharing your contact info."

    if result.get("email"):
        email = extract_email(text)
        if email:
            send_email(email, message)

    if result.get("phone"):
        phone = extract_phone(text)
        if phone:
            send_sms(phone, message)

# Example usage
detect_and_store("Reach me at emeka2025@yahoo.com or call +14155552671 or visit linkedin.com/in/emeka-ai")
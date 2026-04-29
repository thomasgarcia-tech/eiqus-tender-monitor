import os, base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def send_email(subject, html_body, to, sender):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw    = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    print(f"✅ Email envoyé — ID: {result.get('id')}")
    return result

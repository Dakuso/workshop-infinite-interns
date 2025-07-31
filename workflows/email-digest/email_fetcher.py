import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")  # fallback to Gmail
SAVE_ATTACHMENTS = False

SAVE_DIR = "./attachments"
os.makedirs(SAVE_DIR, exist_ok=True)

# Connect and login
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(EMAIL, PASSWORD)
mail.select("inbox")

# Search for unread emails
# FROM "string": Messages with the specified string in the envelope structure's FROM field.
# status, messages = mail.search(None, '(UNSEEN)')
# mail.select("inbox")  # Select only the "Primary" inbox

date_string = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
status, messages = mail.search(None, 'SINCE', date_string)

for num in messages[0].split():
    _, data = mail.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])

    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")
    print("\nSubject:", subject)

    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition"))
        if "attachment" in content_disposition:
            filename = part.get_filename()
            if filename:
                filename = decode_header(filename)[0][0]
                if isinstance(filename, bytes):
                    filename = filename.decode()
                filepath = os.path.join(SAVE_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                print(f"Saved attachment: {filepath}")


    # Extract and print the body (text/plain only)
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))

        if content_type == "text/plain" and "attachment" not in content_disposition:
            body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
            print(f"Body:    {body}"[:80])

        # Save attachments only if enabled
        elif "attachment" in content_disposition and SAVE_ATTACHMENTS:
            filename = part.get_filename()
            if filename:
                filename = decode_header(filename)[0][0]
                if isinstance(filename, bytes):
                    filename = filename.decode()
                filepath = os.path.join(SAVE_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                print(f"Saved attachment: {filepath}")

import imaplib
import sys

email = "SeymourWrobbel1284@hotmail.com"
password = "OFsd6cn2g0QXY7AL"

try:
    print(f"Testing IMAP for {email}...")
    mail = imaplib.IMAP4_SSL('imap-mail.outlook.com')
    mail.login(email, password)
    print("SUCCESS: Logged in via IMAP!")
    mail.logout()
except Exception as e:
    print(f"FAILED: {e}")

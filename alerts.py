import smtplib
import requests
from email.mime.text import MIMEText

# -------------------------------
# TELEGRAM SETTINGS
# -------------------------------
TELEGRAM_BOT_TOKEN = "8633517801:AAFmmfCr70vGXnLo7BM80WmLujm6sYHaktE"
TELEGRAM_CHAT_ID = "5542675157"

# -------------------------------
# EMAIL SETTINGS
# -------------------------------
EMAIL_ADDRESS = "bhagwatilalprajapati675@gmail.com"
EMAIL_PASSWORD = "xflm zgpy ojlh uiuw"
TO_EMAIL = "bhagwatilalprajapati675@gmail.com"


# -------------------------------
# TELEGRAM ALERT FUNCTION
# -------------------------------
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        response = requests.post(url, data=data)

        if response.status_code == 200:
            print("Telegram alert sent")
        else:
            print("Telegram Error:", response.text)

    except Exception as e:
        print("Telegram Exception:", e)


# -------------------------------
# EMAIL ALERT FUNCTION
# -------------------------------
def send_email(subject, message):
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_EMAIL

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        server.sendmail(EMAIL_ADDRESS, TO_EMAIL, msg.as_string())
        server.quit()

        print("Email alert sent")

    except Exception as e:
        print("Email Error:", e)


# -------------------------------
# TEST ALERT
# -------------------------------
if __name__ == "__main__":
    test_message = "🚀 Trading Bot Alert Working!"

    send_telegram(test_message)
    send_email("Trading Bot Alert", test_message)
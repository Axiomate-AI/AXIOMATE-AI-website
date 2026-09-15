from datetime import datetime
import pytz

# Target Timezone (e.g., IST)
tz = pytz.timezone("Asia/Kolkata")
now = datetime.now(tz)

weekday = now.weekday()  # 0: Mon, 1: Tue, ..., 5: Sat, 6: Sun
current_hour = now.hour  # 24-hour format

# 1. Sunday (weekday == 6): Complete OFF
if weekday == 6:
    print("Sunday is OFF. No messages sent.")
    exit(0)

# 2. Saturday (weekday == 5): Max 10 messages, till 4:00 PM (16:00)
if weekday == 5:
    if current_hour >= 16:
        print("Saturday after 4:00 PM. No messages sent.")
        exit(0)
    else:
        max_messages = 10

# 3. Monday to Friday (weekday 0 to 4): Max 15 messages
else:
    max_messages = 15

print(f"Today is allowed to send up to {max_messages} messages.")


# --- Yahan aapka Message Sending Logic aayega ---
def send_messages(limit):
    for i in range(limit):
        # Yahan message bhejne ka code likhein
        print(f"Sending message {i + 1} of {limit}")


send_messages(max_messages)

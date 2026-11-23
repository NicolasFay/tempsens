import smbus2
import smtplib
import mimetypes
import os
import time
import io
from email.message import EmailMessage
from email.utils import make_msgid
from gpiozero import LED
from matplotlib.figure import Figure
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

TEMP_THRESHOLD_F = 70.0       # Alert if temp drops below this (Farenheit)
CHECK_INTERVAL = 60            # Check every 60 seconds
ALERT_COOLDOWN = 3600          # Wait 1 hour (3600s) before sending another alert

IMAGE_PATH = "/home/njfay/Desktop/Temp/images/hi.png"

RECORD_LENGTH = 60 # how many temp records you store at a time

led = LED(17)

# --- I2C SETUP ---
bus = smbus2.SMBus(1)
ADDRESS = 0x48

def get_temp_f():
    data = bus.read_i2c_block_data(ADDRESS, 0x00, 2)
    temp_raw = (data[0] << 4) | (data[1] >> 4)
    if temp_raw > 2047:
        temp_raw -= 4096
    temp_c = temp_raw * 0.0625
    return (temp_c * 1.8) + 32

def make_graph_png(records, threshold):
    n = len(records)
    # x-axis: minutes ago (0 = now)
    minutes_ago = [-(n - 1 - i) * CHECK_INTERVAL / 60 for i in range(n)]

    fig = Figure(figsize=(6, 3), dpi=100)
    ax = fig.subplots()
    ax.plot(minutes_ago, records, marker="o", markersize=3, label="Temp")
    ax.axhline(threshold, color="red", linestyle="--", label=f"Threshold ({threshold}°F)")
    ax.set_xlabel("Minutes ago")
    ax.set_ylabel("Temperature (°F)")
    ax.set_title("Recent Temperature")
    ax.grid(True, alpha=0.3)
    ax.legend()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    return buf.getvalue()

def send_email_img(current_temp, sender, receiver, graph_bytes=None, image_path=None):
    msg = EmailMessage()
    msg['Subject'] = f"Low Temp Alert: {current_temp:.1f}°F"
    msg['From'] = sender
    msg['To'] = receiver

    # Plain-text fallback for email clients that don't render HTML
    msg.set_content(
        f"Warning: Your Raspberry Pi TMP102 sensor recorded a temperature of "
        f"{current_temp:.2f}°F, which is below your {TEMP_THRESHOLD_F}°F threshold."
    )

    # Only embed the image and graph if the file actually exists
    embed_graph = graph_bytes is not None
    embed_image = image_path and os.path.isfile(image_path)

    graph_cid = make_msgid(domain="rpi.local") if embed_graph else None
    image_cid = make_msgid(domain="rpi.local") if embed_image else None

    graph_tag = f'<img src="cid:{graph_cid[1:-1]}" style="max-width:100%;">' if embed_graph else ""
    img_tag = f'<img src="cid:{image_cid[1:-1]}" style="max-width:100%;">' if embed_image else ""

    msg.add_alternative(f"""\
<html>
  <body>
    <h2>Low Temperature Alert</h2>
    <p>Your Raspberry Pi TMP102 sensor recorded
       <b>{current_temp:.2f}°F</b>, which is below your
       {TEMP_THRESHOLD_F}°F threshold.</p>
    <h3>Recent Temperature</h3>
    {graph_tag}
    {img_tag}
  </body>
</html>
""", subtype='html')

    html_part = msg.get_payload()[1]

    if embed_image:
        mime_type, _ = mimetypes.guess_type(image_path)
        maintype, subtype = (mime_type or "image/png").split("/")
        with open(image_path, "rb") as f:
            html_part.add_related(f.read(), maintype, subtype, cid=image_cid)

    if embed_graph:
        html_part.add_related(graph_bytes, "image", "png", cid=graph_cid)


    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, APP_PASSWORD)
            smtp.send_message(msg)
        print("Alert email sent!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    
# --- MAIN LOOP ---
last_alert_time = 0
low_temp_counter = 0
below_temp = False
records = []

while True:
    if below_temp:
        led.on()
    else:
        led.off()

    try:
        temp = get_temp_f()
        records.append(temp)
        if len(records) > RECORD_LENGTH : del records[0]
        
        current_time = time.time()

        print(f"Current Temp: {temp:.2f}°F")

        if temp < TEMP_THRESHOLD_F:
            below_temp = True
            if (current_time - last_alert_time) > ALERT_COOLDOWN:
                low_temp_counter += 1
    
        else:
            below_temp = False
            low_temp_counter = 0
        if low_temp_counter >= 3:
            try: 
                graph = make_graph_png(records, TEMP_THRESHOLD_F)
            except Exception as e:
                print(f"Graph error: {e}")
                graph = None  # still send the alert without the graph

            if send_email_img(temp, SENDER_EMAIL, RECEIVER_EMAIL, graph_bytes=graph, image_path=IMAGE_PATH):
                last_alert_time = current_time
                low_temp_counter = 0
            
    except Exception as e:
        print(f"Sensor read error: {e}")
        
    time.sleep(CHECK_INTERVAL)
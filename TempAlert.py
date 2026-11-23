import smbus2
import smtplib
import mimetypes
import os
import time
import io
import yaml
import sys
from email.message import EmailMessage
from email.utils import make_msgid
from gpiozero import LED
from matplotlib.figure import Figure
from dotenv import load_dotenv
from pathlib import Path

# --- Configuration Functions ---
DEFAULT_CONFIG = {
    "temp_threshold_f": 70.0, 
    "check_interval": 60,         
    "alert_cooldown": 3600        
}

def load_config(filepath="config.yaml"):
    try:
        with open(filepath, "r") as file:
            # Returns None if the file is completely empty
            data = yaml.safe_load(file)
            if data is None:
                print(f"Warning: {filepath} is empty. Using default settings.")
                return DEFAULT_CONFIG
            return data

    except FileNotFoundError:
        print(f"Error: {filepath} not found. Using default settings.")
        return DEFAULT_CONFIG

    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax in {filepath}.")
        # Optional: print the exact line and column of the syntax error
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            print(f"Syntax error at line {mark.line + 1}, column {mark.column + 1}")
        sys.exit(1)  # Stop execution if the config is broken

def load_environment(env_path=".env", required_vars=None):
    if required_vars is None:
        required_vars = ["SMTP_EMAIL", "SMTP_PASSWORD", "RECEIVER_EMAIL"]

    env_file = Path(env_path)

    # 1. Check if the .env file actually exists (since load_dotenv won't raise an error)
    if not env_file.is_file():
        print(f"Warning: {env_path} file not found. Checking system environment variables...")
    else:
        try:
            # override=True ensures .env values update any stale system variables
            loaded = load_dotenv(dotenv_path=env_file, override=True)
            if not loaded:
                print(f"Warning: {env_path} is empty or contains no valid variables.")
        except PermissionError:
            print(f"Error: Permission denied when trying to read {env_path}.")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error loading {env_path}: {e}")
            sys.exit(1)

    # 2. Verify that all required variables exist and are not empty strings
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Ensure they are set in your .env file or system environment.")
        sys.exit(1)

# --- CONFIGURATION ---
load_environment(required_vars=["SMTP_EMAIL", "SMTP_PASSWORD", "RECEIVER_EMAIL"])
config = load_config("config.yaml")

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

TEMP_THRESHOLD_F = config["temp_threshold_f"]        # Alert if temp drops below this (Farenheit)
CHECK_INTERVAL = config["check_interval"]            # Check every 60 seconds
ALERT_COOLDOWN = config["alert_cooldown"]            # Wait 1 hour (3600s) before sending another alert

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
            smtp.login(sender, SMTP_PASSWORD)
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

            if send_email_img(temp, SMTP_EMAIL, RECEIVER_EMAIL, graph_bytes=graph, image_path=IMAGE_PATH):
                last_alert_time = current_time
                low_temp_counter = 0
            
    except Exception as e:
        print(f"Sensor read error: {e}")
        
    time.sleep(CHECK_INTERVAL)
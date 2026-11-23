import time
from collections import deque

from gpiozero import LED

from config import load_settings
from monitor import AlertState
from notifer import EmailNotifier
from sensor import TMP102
from graph import make_graph_png

# --- CONFIGURATION ---
def main():
    s = load_settings()
    led = LED(17)
    sensor = TMP102()
    state = AlertState(s.temp_threshold_f, s.alert_cooldown)
    notifier = EmailNotifier(s.smtp_email, s.smtp_password,
                             s.receiver_email, s.temp_threshold_f)
    records = deque(maxlen=s.record_length)

    while True:
        try:
            temp = sensor.read_f()
            records.append(temp)
            print(f"Current Temp: {temp:.2f}°F")

            should_alert = state.update(temp, time.time())
            led.value = state.below_thresh

            if should_alert:
                try:
                    graph = make_graph_png(list(records), s.temp_threshold_f,
                                            s.check_interval)
                except Exception as e:
                    print(f"Graph error: {e}")
                    graph = None

                if notifier.send_low_temp(temp, graph, s.image_path):
                    state.mark_sent(time.time())
        except Exception as e:
            print(f"Loop error: {e}")

        time.sleep(s.check_interval)

if __name__ == "__main__":
    main()
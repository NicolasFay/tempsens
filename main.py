import time
import logging
from collections import deque

from gpiozero import LED

from config import load_settings
from monitor import AlertState
from notifier import EmailNotifier
from sensor import TMP102
from graph import make_graph_png
from telegram_bot import TelegramBot

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

def main():
    logger = logging.getLogger(__name__) 
    s = load_settings()
    led = LED(17)
    sensor = TMP102()
    state = AlertState(s.temp_threshold_f, s.alert_cooldown)
    notifier = EmailNotifier(s.smtp_email, s.smtp_password,
                             s.receiver_email, s.temp_threshold_f)
    records = deque(maxlen=s.records_kept)

    bot = TelegramBot(
        s.telegram_token,
        s.telegram_chat_id,
        get_latest_temp=lambda: records[-1] if records else None,
    )
    bot.start()
    
    while True:
        try:
            temp = sensor.read_f()
            records.append(temp)
            logger.info("Current Temp: %.2f°F", temp)

            should_alert = state.update(temp, time.time())
            led.value = state.below_thresh

            if should_alert:
                try:
                    graph = make_graph_png(list(records), s.temp_threshold_f,
                                            s.check_interval)
                except Exception as e:
                    logger.error("Graph Error: %s", e)
                    graph = None

                if notifier.send_low_temp(temp, graph, s.image_path):
                    state.mark_sent(time.time())
        except Exception as e:
            logger.error("Loop Error: %s", e)

        time.sleep(s.check_interval)

if __name__ == "__main__":
    main()
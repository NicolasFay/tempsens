class AlertState:
    def __init__(self, threshold_f, cooldown_s, required_readings=3):
        self.threshold_f = threshold_f
        self.cooldown_s = cooldown_s
        self.required = required_readings
        self.counter = 0
        self.last_alert_time = 0.0
        self.below_thresh = False

    def update(self, temp_f, now) -> bool:
        """Record a reading. Returns True if an alert should be sent."""
        self.below_thresh = temp_f < self.threshold_f
        if not self.below_thresh:
            self.counter = 0
            return False
        if now - self.last_alert_time > self.cooldown_s:
            self.counter += 1
        return self.counter >= self.required

    def mark_sent(self, now):
        self.last_alert_time = now
        self.counter = 0
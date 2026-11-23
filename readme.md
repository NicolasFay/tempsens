# Temperature Tracker and Notifier

This program is built for the Raspberry Pi 4 Model B+ using 64 bit Raspi OS. To operate this software download these files and create a project folder on your RPI. To continue setup from there follow the next steps below.

## Environment Setup

Use a virtual environment and install dependencies by using `pip install -r requirements.txt`

After that create your `.env` folder with values

```text
SMTP_EMAIL = "youremail@smtp.com"
SMTP_PASSWORD = "your smtp password"
RECEIVER_EMAIL = "receiveremail@smtp.com"
```

## Service File Setup

To run the program on startup and automatically in the background we need to create a service file.

1. Run `sudo nano /etc/systemd/system/tempalert.service` to create your service file
2. Enter this into the file:

```text
[Unit]
Description=TMP102 Low Temperature Alert
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=</home/pi/my-project>
ExecStart=</home/pi/my-project/.venv/bin/python> -u </home/pi/my-project/script.py>
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Once you have done that reload the service file `sudo systemctl daemon-reload`
5. Then enable it `sudo systemctl enable tempalert.service`
6. And finally start it up `sudo systemctl start tempalert.service`

Repeat Steps 4-6 if you ever change the service file with `sudo systemctl edit --full tempalert`

## Status of the Program

* To check the status of the program run `sudo systemctl status tempalert`
* To check the journal output of our program run `journalctl -u tempalert.service -f` in the terminal

---

## Code Breakdown

### config.yaml



### main.py

### config.py

### graph.py

### monitor.py

### notifier.py

### sensor.py

# CMD code

## system

### check system service status

* `sudo systemctl status tempalert`

### check journal of system service running

* `journalctl -u tempalert.service -f`

### restart service file once updated

* `sudo systemctl daemon-reload`
* `sudo systemctl restart tempalert`

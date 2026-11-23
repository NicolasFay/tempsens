import mimetypes
import smtplib
import os
from email.message import EmailMessage
from email.utils import make_msgid

class EmailNotifier:
    def __init__(self, sender, password, receiver, threshold_f):
        self.sender = sender
        self.password = password
        self.receiver = receiver
        self.threshold_f = threshold_f

    def send_email_img(self, temp_f, graph_bytes=None, image_path=None):
        msg = EmailMessage()
        msg['Subject'] = f"Low Temp Alert: {temp_f:.1f}°F"
        msg['From'] = self.sender
        msg['To'] = self.receiver

        # Plain-text fallback for email clients that don't render HTML
        msg.set_content(
            f"Warning: Your Raspberry Pi TMP102 sensor recorded a temperature of "
            f"{temp_f:.2f}°F, which is below your {self.threshold_f}°F threshold."
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
        <b>{temp_f:.2f}°F</b>, which is below your
        {self.threshold_f}°F threshold.</p>
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
                smtp.login(self.sender, self.password)
                smtp.send_message(msg)
            print("Alert email sent!")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
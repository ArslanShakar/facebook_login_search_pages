# -*- coding: utf-8 -*-

import time

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


RECEIVER_EMAIL = 'alifarslan786@gmail.com'  # REPLACE YOUR RECEIVING E-MAIL
SENDER_EMAIL = 'huwaiguest@gmail.com'  # REPLACE YOUR SENDING E-MAIL
SENDER_PASSWORD = 'huwai78600'  # REPLACE YOUR Sender Email PASSWORD

port = 587
SERVER = 'smtp.gmail.com:{}'.format(port)
SUBJECT = 'Email Notification'

HTML_T = """
     <!DOCTYPE html>
     <html>
     <head>
     <meta charset="utf-8" />
     <style type="text/css">
     </style>
     </head>
     <body>
     Hi there,<br>
     <h3>Message Body Description.....{}</h3>
     <a href=''></a><br> <br>
     Thank you!
     </body>
     </html>"""


class SendEmailNotifications:
    def generate_message(self, receiver_email, html):
        message = MIMEMultipart("alternative", None, [MIMEText(html, 'html')])
        message['Subject'] = SUBJECT
        message['From'] = SENDER_EMAIL
        message['To'] = receiver_email
        return message

    def send_message(self, receiver_email, message_body):
        print(f"Sending Email Notification: {receiver_email}")
        try:
            server = smtplib.SMTP("smtp.gmail.com", port)
            html = HTML_T.format(message_body)
            message = self.generate_message(receiver_email, html)

            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
            server.quit()
            print("Email has been sent to " + RECEIVER_EMAIL)

        except Exception as err:
            print(err)
            a = 0


# if __name__ == "__main__":
#     try:
#         obj = SendEmailNotifications()
#         obj.send_message(RECEIVER_EMAIL, 'Blah blah blah')
#     except Exception as e:
#         print(e)

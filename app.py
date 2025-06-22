from flask import Flask, request, render_template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import os
import smtplib
from dotenv import load_dotenv
import schedule
import threading
import time
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def message(subject="Notification", text="", img=None, attachment=None):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg.attach(MIMEText(text))

    if img:
        if not isinstance(img, list):
            img = [img]
        for one_img in img:
            with open(one_img, 'rb') as f:
                msg.attach(MIMEImage(f.read(), name=os.path.basename(one_img)))

    if attachment:
        if not isinstance(attachment, list):
            attachment = [attachment]
        for one_attachment in attachment:
            with open(one_attachment, 'rb') as f:
                part = MIMEApplication(
                    f.read(), name=os.path.basename(one_attachment))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(one_attachment)}"'
            msg.attach(part)
    return msg


def send_mail(subject, text, recipients, img_path=None, attach_path=None):
    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.starttls()
    smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    msg = message(subject, text, img_path, attach_path)
    smtp.sendmail(from_addr=os.getenv("EMAIL_USER"),
                  to_addrs=recipients, msg=msg.as_string())
    smtp.quit()
    print("✅ Mail sent to:", recipients)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


threading.Thread(target=run_scheduler, daemon=True).start()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        subject = request.form['subject']
        body = request.form['body']
        recipients = request.form['recipients'].split(',')

        send_time = request.form['send_time']
        delay = request.form['delay']
        recur = request.form['recur']

        img_file = request.files['image']
        attachment_file = request.files['attachment']
        img_path = attach_path = None

        if img_file and img_file.filename:
            img_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
            img_file.save(img_path)

        if attachment_file and attachment_file.filename:
            attach_path = os.path.join(UPLOAD_FOLDER, attachment_file.filename)
            attachment_file.save(attach_path)

        def job():
            send_mail(subject, body, recipients, img_path, attach_path)

        if send_time:
            now = datetime.now()
            send_at = datetime.strptime(send_time, '%H:%M')
            send_at = send_at.replace(
                year=now.year, month=now.month, day=now.day)
            if send_at < now:
                send_at += timedelta(days=1)
            threading.Timer((send_at - now).total_seconds(), job).start()
            return render_template('index.html', success=True)

        elif delay:
            threading.Timer(int(delay), job).start()
            return render_template('index.html', success=True)

        elif recur:
            if recur == '2s':
                schedule.every(2).seconds.do(job)
            elif recur == '10min':
                schedule.every(10).minutes.do(job)
            elif recur == 'hourly':
                schedule.every().hour.do(job)
            elif recur == 'daily':
                schedule.every().day.at("10:30").do(job)
            elif recur == 'monday':
                schedule.every().monday.at("09:00").do(job)
            elif recur == 'wednesday':
                schedule.every().wednesday.at("13:15").do(job)
            return render_template('index.html', success=True)

        return render_template('index.html', success=False)

    return render_template('index.html', success=False)


if __name__ == '__main__':
    app.run(debug=True)

from app.celery import celery
import boto3

import smtplib
from email.message import EmailMessage

from app.core import settings
from app.core.database import get_sync_db
from app.models import Reminder

from sqlalchemy import delete


def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.FROM_EMAIL, settings.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)



@celery.task
def send_notification(email: str, task: dict):

    with get_sync_db() as session:
        stmt = delete(Reminder).where(
            Reminder.plannable_id==task.get('plannable_id')
        )
        result = session.execute(stmt)
        session.commit()
        print(f"Deleted {result.rowcount} rows")

    # ses = boto3.client('ses', region_name=settings.AWS_REGION)

    # response = ses.send_email(
    #     Source=settings.FROM_EMAIL,
    #     Destination={'ToAddresses': [f"{email}"]},
    #     Message={
    #         'Subject': {'Data': 'Deadline Reminder'},
    #         'Body': {'Text': {
    #             'Data': f"Don't forget to upload {task.get('assignment_name')} for "
    #                     f"{task.get('course_name')}. Deadline is {task.get('deadline')}"}}
    #     }
    # )

    # print("Email sent:", response['MessageId'])
    message = f"Don't forget to upload {task.get('assignment_name')} for {task.get('course_name')}. Deadline is {task.get('deadline')}"

    send_email(email, "Reminder", message)


@celery.task
def send_verification_email(email: str, token: str):

    # ses = boto3.client('ses', region_name=settings.AWS_REGION)
    # response = ses.send_email(
    #     Source=settings.FROM_EMAIL,
    #     Destination={'ToAddresses': [f"{email}"]},
    #     Message={
    #         'Subject': {'Data': 'Verification'},
    #         'Body': {'Text': {
    #             'Data': f"Verification URL: {settings.FRONT_URL}/verify?token={token}"}}
    #     }
    # )

    message = f"Verification URL: {settings.FRONT_URL}/verify?token={token}"

    send_email(email, "Verification", message)

@celery.task
def send_password_reset_email(email: str, token: str):

    # ses = boto3.client('ses', region_name=settings.AWS_REGION)
    # response = ses.send_email(
    #     Source=settings.FROM_EMAIL,
    #     Destination={'ToAddresses': [f"{email}"]},
    #     Message={
    #         'Subject': {'Data': 'Password Reset'},
    #         'Body': {'Text': {
    #             'Data': f"Password Reset URL: {settings.FRONT_URL}/reset-password?token={token}"}}
    #     }
    # )

    message = f"Password Reset URL: {settings.FRONT_URL}/reset-password?token={token}"
    send_email(email, "Password Reset", message)
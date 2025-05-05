from app.celery import celery
import boto3

from app.core import settings
from app.core.database import get_sync_db
from app.models import Reminder

from sqlalchemy import delete


@celery.task
def send_notification(email: str, task: dict):

    with get_sync_db() as session:
        stmt = delete(Reminder).where(
            Reminder.plannable_id==task.get('plannable_id')
        )
        result = session.execute(stmt)
        session.commit()
        print(f"Deleted {result.rowcount} rows")

    ses = boto3.client('ses', region_name=settings.AWS_REGION)

    response = ses.send_email(
        Source=settings.FROM_EMAIL,
        Destination={'ToAddresses': [f"{email}"]},
        Message={
            'Subject': {'Data': 'Deadline Reminder'},
            'Body': {'Text': {
                'Data': f"Don't forget to upload {task.get('assignment_name')} for "
                        f"{task.get('course_name')}. Deadline is {task.get('deadline')}"}}
        }
    )

    print("Email sent:", response['MessageId'])


@celery.task
def send_verification_email(email: str, token: str):

    ses = boto3.client('ses', region_name=settings.AWS_REGION)
    response = ses.send_email(
        Source=settings.FROM_EMAIL,
        Destination={'ToAddresses': [f"{email}"]},
        Message={
            'Subject': {'Data': 'Verification'},
            'Body': {'Text': {
                'Data': f"Verification URL: {settings.FRONT_URL}/verify?token={token}"}}
        }
    )

    print("Email sent:", response['MessageId'])

@celery.task
def send_password_reset_email(email: str, token: str):

    ses = boto3.client('ses', region_name=settings.AWS_REGION)
    response = ses.send_email(
        Source=settings.FROM_EMAIL,
        Destination={'ToAddresses': [f"{email}"]},
        Message={
            'Subject': {'Data': 'Password Reset'},
            'Body': {'Text': {
                'Data': f"Password Reset URL: {settings.FRONT_URL}/reset-password?token={token}"}}
        }
    )

    print("Email sent:", response['MessageId'])
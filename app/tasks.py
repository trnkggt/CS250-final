from app.celery import celery
import boto3


@celery.task
def send_notification(email: str, task: dict):
    ses = boto3.client('ses')

    response = ses.send_email(
        Source="",
        Destination={'ToAddresses': [f"{email}"]},
        Message={
            'Subject': {'Data': 'Deadline Reminder'},
            'Body': {'Text': {
                'Data': f"Don't forget to upload {task.get('assignment_name')} for "
                        f"{task.get('course_name')}. Deadline is {task.get('deadline')}"}}
        }
    )

    print("Email sent:", response['MessageId'])

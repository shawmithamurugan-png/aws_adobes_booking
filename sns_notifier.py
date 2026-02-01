import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
TOPIC_ARN = "arn:aws:sns:us-east-1:977098995659:Booking_confirmed"

sns = boto3.client(
    "sns",
    region_name=AWS_REGION
)

def send_sns_message(subject, message):
    try:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=subject,
            Message=message
        )
        print("✅ SNS message sent successfully")

    except ClientError as e:
        print("❌ SNS error:", e)

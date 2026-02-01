import boto3
from botocore.exceptions import ClientError

print("Starting DynamoDB table creation...")

# Connect using aws configure credentials
dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1'
)

try:
    table = dynamodb.create_table(
        TableName='Users',   # ✅ must match Flask app
        KeySchema=[
            {
                'AttributeName': 'email',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'email',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'  # ✅ On-demand
    )

    print("Creating table...")
    table.wait_until_exists()
    print("✅ Table 'Users' created successfully!")

except ClientError as e:
    if e.response['Error']['Code'] == 'ResourceInUseException':
        print("ℹ️ Table already exists. No action needed.")
    else:
        print("❌ AWS error:")
0        print(e)


 


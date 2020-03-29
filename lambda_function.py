import json

import boto3

ENCODING = 'utf8'
TABLE_NAME = 'you_table_name_here'


def persist_email(db, from_email, from_name, to_email, subject, date, msg_id, folder):
    put_item = {'from_email': {'S': from_email}, 'from_name': {'S': from_name}, 'to_email': {'S': to_email},
                'subject': {'S': subject}, 'date': {'S': date}, 'id': {'S': msg_id}, 'folder': {'S': folder}}
    resp = db.put_item(TableName=TABLE_NAME, Item=put_item)
    return resp['ResponseMetadata']['HTTPStatusCode']


def lambda_handler(event, context):
    if event is not None and 'body' in event.keys():
        params = json.loads(event['body'])
        db = boto3.client('dynamodb')
        ret_code = persist_email(db, params['from_email'], params['from_name'], params['to_email'],
                                 params['subject'], params['date'], params['id'], params['folder'])
    else:
        ret_code = 500
    return {
        "statusCode": ret_code
    }

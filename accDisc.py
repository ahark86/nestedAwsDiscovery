import boto3, requests, urllib3, sys
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

role = 'OrganizationAccountAccessRole'
creds = []
morphurl = 'https://68.39.65.192'
apitoken = sys.argv[1]

#Instantiate 'organization' object
org_client = boto3.client('organizations',
	aws_access_key_id=sys.argv[2],
    aws_secret_access_key=sys.argv[3])

#instantiate 'sts' object
sts_client = boto3.client('sts',
	aws_access_key_id=sys.argv[2],
    aws_secret_access_key=sys.argv[3])

#Call list_accounts() method on organization object
org_response = org_client.list_accounts()

#Iterate through listed accounts
for i in range(0, int(len(org_response['Accounts']))):
	#Instantiate datetime account was added to org
	added = org_response['Accounts'][i]['JoinedTimestamp']
	#Instantiate account name
	name = org_response['Accounts'][i]['Name']
	
	if (added.date() - datetime.today().date()).days == -1: #If the account was added to the organization on the prior date (yesterday)
		#Instantiate the ID for the AWS account currently being iterated on
		current = org_response['Accounts'][i]['Id']
	else:
		#Skip to the next iteration if the currently considered account was not added to the organization in the last day
		continue

	try:
		#Run assume_role() method on sts object
		sts_response = sts_client.assume_role(
			RoleArn=f'arn:aws:iam::{current}:role/{role}',
			RoleSessionName='mySession')

		#Append the temporary creds/role arn as a tuple to a list called 'creds'
		creds.append((name, 
			sts_response['Credentials']['AccessKeyId'],  
			sts_response['Credentials']['SecretAccessKey'], 
			#sts_response['Credentials']['SessionToken'], 
			sts_response['AssumedRoleUser']['Arn']))

		try:
			#Attempt to integrate a new cloud with Morpheus using the temporary creds from assumerole using Morpheus API
			requestHeaders = {'Content-type': 'application/json', 
				'Authorization': f'Bearer {apitoken}'}

			requests.post(f'{morphurl}/api/zones', 
				data={"zone": {"name": name, "description": "None", "groupId": 1, "zoneType": {"code": "amazon"},
					"config": {"certificateProvider": "internal", "endpoint": "ec2.us-east-1.amazonaws.com", "accessKey": f'{creds[i][0]}', "secretKey": f'{creds[i][1]}', "vpc": "None", "importExisting": "off"},
					"code": "None",
					"location": "None",
					"visibility": "private"}
					}, 
				headers=requestHeaders, 
				verify=False)

			print(f'Account {current}: Added')
		
		except:
			#Print friendly message if the API post request fails for any reason
			print('API post failed')
			continue

	except:
		#Print friendly message if there is a failure running the assume_role() method or if there's an issue loading the 'creds' list
		print(f'Account {current}: Failed to add')


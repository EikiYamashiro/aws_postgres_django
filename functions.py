import sys
import boto3
import time
OHIO_NAME = "ohio_key_pair"
NORTH_VIRGINIA_NAME = "north_virginia_key_pair"

def create_client(region, tipo="ec2"):
    
    return boto3.client(tipo, region_name=region)
    
def create_key_pair(client, name):
    
    name_flag = True
    
    for KeyPair in client.describe_key_pairs()["KeyPairs"]:

        if KeyPair["KeyName"] == name:
            
            print("KeyName ", name, " already exists")
            name_flag = False
            return False
            break
            
    if name_flag:
        
        response = client.create_key_pair(KeyName=name)
        print("KeyPair ",name," created successfully")
        return response

def delete_key_pair(client , name):
    
    for KeyPair in client.describe_key_pairs()["KeyPairs"]:
        
        if KeyPair["KeyName"] == name:

            response = client.delete_key_pair(KeyName=name)
            print("KeyPair ",name," deleted successfully")
            
            return True
            
            break

    print("Unable to delete KeyPair ", name)
    return False

def create_instance(hw, os, region, client, KeyPair, script, security_group_id):
    
    instance = client.run_instances(
        ImageId= os, 
        MinCount=1,
        MaxCount=1,
        InstanceType= hw,
        KeyName = KeyPair["KeyName"],
        SecurityGroupIds = [security_group_id],
        TagSpecifications=[
        {
          "ResourceType": "instance",
          "Tags": [
            {
              "Key": "Name",
              "Value": f'{region}-instance'
            }
          ]
        }
      ],
        UserData = script
    )
    
    waiter = client.get_waiter('instance_status_ok')
    
    waiter.wait(InstanceIds=[instance["Instances"][0]["InstanceId"]])
    
    print(f'Instance {instance["Instances"][0]["InstanceId"]} created successfully')
    
    return instance

def get_ip(instance, instance_id):
    
    for e in instance.cursor.client.describe_instances()["Reservations"]:
        if e["Instances"][0]["InstanceId"] == instance_id:
            saida = e["Instances"][0]["PublicIpAddress"]
            
    return saida
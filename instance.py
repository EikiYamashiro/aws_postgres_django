import sys
import boto3
import time
OHIO_NAME = "ohio_key_pair"
NORTH_VIRGINIA_NAME = "north_virginia_key_pair"
from functions import *
from cursor import *

class Instance():
    
    def __init__(self, cursor, region):
        
        self.cursor = cursor
        self.counter = 0
        
        if region == "ohio":
            self.hw = "t2.micro"
            self.os = "ami-00399ec92321828f5"
            
        if region == "north-virginia":
            self.hw = "t2.micro"
            self.os = "ami-09e67e426f25ce0d7"
        
    def setHW(self, hw):
        self.hw = hw
        
    def setOS(self, os):
        self.os = os
        
    def create_instance(self, script):
        
        self.script = script
        
        if self.hw == None:
            print("Set the instance hardware!")
            
        if self.os == None:
            print("Set the instance operational system!")
        
        self.instance = create_instance(self.hw, 
                                        self.os, 
                                        self.cursor.region, 
                                        self.cursor.client, 
                                        self.cursor.keypair,
                                        self.script,
                                        self.security_group['GroupId'],
                                        )
        
        self.id = self.instance["Instances"][0]['InstanceId']
        
    def delete_instance(self):
        
        response = input(f"Are you sure you want to delete the instance {self.id} from {self.cursor.region}? (y/n)")
        
        if response == 'y' or response == "yes":
            
            response = self.cursor.client.terminate_instances(InstanceIds=[self.id])
            
            waiter = self.cursor.client.get_waiter('instance_terminated')
    
            waiter.wait(InstanceIds=[self.id])
            
            print("Instance ",self.id," deleted successfully")
            
        else: 
            print("Operation canceled")
        
    def create_security_group(self, permissions_config):
       
        self.vpc_id = self.cursor.client.describe_vpcs()["Vpcs"][0]["VpcId"]
        
        self.security_group_name = f'security-group-{str(time.time())[-3:]}'
        
        self.security_group = self.cursor.client.create_security_group(GroupName = self.security_group_name,
                                                                       Description = 'Security Group of instance')
        
        self.cursor.client.authorize_security_group_ingress(GroupId = self.security_group['GroupId'],
                                                            IpPermissions = permissions_config)
        print("Security Group ",self.security_group_name," created successfully")
        
        self.counter += 1
        
    def delete_security_group(self):
        response = input(f"Are you sure you want to delete the security group {self.security_group['GroupId']} from {self.cursor.region}? (y/n)")
        
        if response == 'y' or response == "yes":
            for e in cursorOH.client.describe_security_groups()["SecurityGroups"]:
            
                if e["GroupName"] == self.security_group_name:
                    
                    r = self.cursor.client.delete_security_group(GroupName=e["GroupName"], GroupId=e["GroupId"])
                    print("Security Group ",self.security_group['GroupId']," deleted successfully")
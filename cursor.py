import sys
import boto3
import time
OHIO_NAME = "ohio_key_pair"
NORTH_VIRGINIA_NAME = "north_virginia_key_pair"
from functions import *

class Cursor():
    
    def __init__(self , client, region, name, keypair=None):
        self.client = client
        self.region = region
        self.name = name
        self.keypair = keypair
        
    def createKeyPair(self):
        self.keypair = create_key_pair(self.client, self.name)
        
    def setKeyPair(self, keypair):
        self.keypair = keypair
        
    def deleteKeyPair(self):
        response = input(f"Are you sure you want to delete {self.name}? (y/n)")
        if response == 'y' or response == "yes":
            
            delete_key_pair(self.client, self.name)
            
        else: 
            print("Operation canceled")
import sys
import boto3
import time
OHIO_NAME = "ohio_key_pair"
NORTH_VIRGINIA_NAME = "north_virginia_key_pair"
from functions import *
from cursor import *
from instance import *

# Criar a Imagem

def create_image(instance):
    
    response = instance.cursor.client.create_image(InstanceId=instance.id, Name=f'{instance.cursor.region}-image')
    return response["ImageId"]
    
def delete_image_function(client, image_id):

    for image in postgresOH.cursor.client.describe_images():
        
        if image["ImageId"] == image_id:
            client.deregister_image(ImageId = image_id)
            print("Image ", image_id, "deleted successfuly")
            return True
    
    return False
    
class Image():
    
    def __init__(self, instance):
        self.id = create_image(instance)
        self.cursor = instance.cursor
        self.instance = instance
        
    def delete_image(self):
        
        delete_image_function(self.cursor.client, self.id)

# Criar o Load Balancer 

# Criar o Target Group

# Criar o Auto Scalling
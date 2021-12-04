import sys
import boto3
import time
OHIO_NAME = "ohio_key_pair"
NORTH_VIRGINIA_NAME = "north_virginia_key_pair"
import logging
logging.basicConfig(filename='log.txt', filemode='w',format='%(asctime)s - %(levelname)s - %(message)s',level=logging.INFO)

def create_client(region, tipo="ec2"):
    
    return boto3.client(tipo, region_name=region)
    
def create_key_pair(client, name):
    
    name_flag = True
    
    for KeyPair in client.describe_key_pairs()["KeyPairs"]:

        if KeyPair["KeyName"] == name:
            
            logging.info(f"KeyName {name} already exists")
            print("KeyName ", name, " already exists")

            name_flag = False
            return False
            break
            
    if name_flag:
        
        response = client.create_key_pair(KeyName=name)
        logging.info("KeyPair {name} created successfully")
        print("KeyPair ",name," created successfully")
        return response

def delete_key_pair(client , name):
    
    for KeyPair in client.describe_key_pairs()["KeyPairs"]:
        
        if KeyPair["KeyName"] == name:

            response = client.delete_key_pair(KeyName=name)
            logging.info("KeyPair {name} deleted successfully")
            print("KeyPair ",name," deleted successfully")
            
            return True
            
            break

    logging.info(f"Unable to delete KeyPair {name}")
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
    
    logging.info(f'Instance {instance["Instances"][0]["InstanceId"]} created successfully')
    print(f'Instance {instance["Instances"][0]["InstanceId"]} created successfully')
    
    return instance

def get_ip(instance, instance_id):
    
    for e in instance.cursor.client.describe_instances()["Reservations"]:
        if e["Instances"][0]["InstanceId"] == instance_id:
            saida = e["Instances"][0]["PublicIpAddress"]
            
    return saida

def launch_config(client, name, image, security_group, cursor):

    return client.create_launch_configuration(LaunchConfigurationName = name,
                                      ImageId = image.id,
                                      SecurityGroups = [security_group],
                                      InstanceType = 't2.micro',
                                      KeyName = cursor.keypair["KeyName"])

def auto_scalling_group(ec2, auto_scalling, target_groupNV):
    
    z = []
    for zones in ec2.describe_availability_zones()['AvailabilityZones']:
        z.append(zones["ZoneName"])
    
    return auto_scalling.create_auto_scaling_group(
        AutoScalingGroupName= "as_name",
        LaunchConfigurationName= "launch_config",
        MinSize=1,
        MaxSize = 3,
        TargetGroupARNs = [target_groupNV.arn],
        AvailabilityZones = z
    )

def delete_launch_config(client, name):
    return client.delete_launch_configuration(LaunchConfigurationName = name)

def delete_as_group(client, name):
    
    return client.delete_auto_scaling_group(AutoScalingGroupName=name,
                                    ForceDelete = True)

def create_auto_scaling_policy(client, auto_scaling_group_name, load_balancer, target_group):
    return client.put_scaling_policy(
        AutoScalingGroupName=auto_scaling_group_name,
        PolicyName='TargetTrackingScaling',
        PolicyType='TargetTrackingScaling',
        TargetTrackingConfiguration={
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ALBRequestCountPerTarget',
                'ResourceLabel': f'{load_balancer.arn[load_balancer.arn.find("app"):]}/{target_group.arn[target_group.arn.find("targetgroup"):]}'
            },
            'TargetValue': 30
        }
    )

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
            logging.info("Operation canceled")
            print("Operation canceled")
            
    def get_vpc_id(self):
        return self.client.describe_vpcs()['Vpcs'][0]['VpcId']

class Instance():
    
    def __init__(self, cursor, region):
        
        self.cursor = cursor
        self.counter = 0
        self.region = region
        
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
            logging.info("Set the instance hardware!")
            print("Set the instance hardware!")
            
        if self.os == None:
            logging.info("Set the instance operational system!")
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
        
    def delete_instance(self, force_delete = False):
        
        response = input(f"Are you sure you want to delete the instance {self.id} from {self.cursor.region}? (y/n)")
        
        if response == 'y' or response == "yes" or force_delete:
            
            response = self.cursor.client.terminate_instances(InstanceIds=[self.id])
            
            waiter = self.cursor.client.get_waiter('instance_terminated')
    
            waiter.wait(InstanceIds=[self.id])
            
            logging.info(f"Instance {self.id}deleted successfully")
            print("Instance ",self.id," deleted successfully")
            
        else: 
            logging.info("Operation canceled")
            print("Operation canceled")
        
    def create_security_group(self, permissions_config):
       
        self.vpc_id = self.cursor.client.describe_vpcs()["Vpcs"][0]["VpcId"]
        
        self.security_group_name = f'security-group-{str(time.time())[-3:]}'
        
        self.security_group = self.cursor.client.create_security_group(GroupName = self.security_group_name,
                                                                       Description = 'Security Group of instance')
        
        self.cursor.client.authorize_security_group_ingress(GroupId = self.security_group['GroupId'],
                                                            IpPermissions = permissions_config)
        logging.info(f"Security Group {self.security_group_name} created successfully")
        print("Security Group ",self.security_group_name," created successfully")
        
        self.counter += 1
        
    def delete_security_group(self):
        response = input(f"Are you sure you want to delete the security group {self.security_group['GroupId']} from {self.cursor.region}? (y/n)")
        
        if response == 'y' or response == "yes":
            for e in cursorOH.client.describe_security_groups()["SecurityGroups"]:
            
                if e["GroupName"] == self.security_group_name:
                    
                    r = self.cursor.client.delete_security_group(GroupName=e["GroupName"], GroupId=e["GroupId"])
                    logging.info(f"Security Group {self.security_group['GroupId'] }deleted successfully")
                    print("Security Group ",self.security_group['GroupId']," deleted successfully")    

# Imagem

def create_image(instance):
    
    response = instance.cursor.client.create_image(InstanceId=instance.id, Name=f'{instance.cursor.region}-image')
    image_waiter = instance.cursor.client.get_waiter("image_available")
    image_waiter.wait(ImageIds=response["ImageId"])
    return response["ImageId"]
    
def delete_image_function(client, image_id):

    for image in client.describe_images():
        
        if image["ImageId"] == image_id:
            client.deregister_image(ImageId = image_id)
            logging.info(f"Image {image_id} deleted successfuly")
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

# Load Balancer

class LoadBalancer():

    # cliente do load balancer e security group
    def __init__(self, client, instance):
        self.name = f"load-balancer-{instance.security_group_name}"
        self.client = client
        self.security_group = instance.security_group
        
    def create(self, client):
        
        l = []
        for subnet in client.describe_subnets()["Subnets"]:
            l.append(subnet['SubnetId'])
            
        logging.info("Creating Load Balancer")
        print("Creating Load Balancer")
        waiter = self.client.get_waiter('load_balancer_available')
        response = self.client.create_load_balancer(Name = self.name,
                                                    Type='application',
                                                    Subnets = l,
                                                    Scheme='internet-facing',
                                                    SecurityGroups = [self.security_group["GroupId"]],
                                                    IpAddressType = "ipv4")
        
        logging.info("Load Balancer created successfuly")
        print("Load Balancer created successfuly")
        logging.info(f"DNSName {response['LoadBalancers'][0]['DNSName']}")
        print(f"DNSName {response['LoadBalancers'][0]['DNSName']}")
        logging.info(f"LoadBalancerArn {response['LoadBalancers'][0]['LoadBalancerArn']}")
        print(f"LoadBalancerArn {response['LoadBalancers'][0]['LoadBalancerArn']}")
        
        self.arn = response['LoadBalancers'][0]['LoadBalancerArn']
        
    def delete(self):
        self.client.delete_load_balancer(LoadBalancerArn=self.arn)
        
        # Criar waite do delete: waiter.wait(LoadBalancerArns=self.arn)
        logging.info(f"Load Balancer {self.name} deleted successfuly")    
        print(f"Load Balancer {self.name} deleted successfuly")        

# Target Group
    
class TargetGroup():
    
    # Client do Load Balancer!
    def __init__(self, client_load_balancer, name, protocol, port, target_type, vpc_id):
        self.client = client_load_balancer
        self.name = name
        self.protocol = protocol
        self.port = port
        self.target_type = target_type
        self.vpc_id = vpc_id
        
        response = self.client.create_target_group(Name  = self.name,
                                                   Protocol  = self.protocol,
                                                   Port  = self.port,
                                                   TargetType = self.target_type,
                                                   VpcId  = self.vpc_id,
                                                   HealthCheckPath = '/admin/',
                                                   Matcher = {
                                                                "HttpCode": "200,302"
                                                            })
        
        self.arn = response['TargetGroups'][0]['TargetGroupArn']
        
        logging.info(f"Target Group {response} created successfuly")
        print(f"Target Group {response} created successfuly")
        
    def delete_target_group(self):
        self.client.delete_target_grouop(TargetGroupArn = self.arn)
        logging.info(f'Target Group {response} deleted successfuly')
        print(f'Target Group {response} deleted successfuly')

class Listener():
    
    def __init__(self, client, load_balancer_arn, target_group_arn):
            self.load_balancer_arn = load_balancer_arn
            self.target_group_arn = target_group_arn
            self.client = client
            self.summary = self.client.create_listener(LoadBalancerArn = self.load_balancer_arn,
                                                      Protocol = 'HTTP',
                                                      Port = 80,
                                                      DefaultActions=[
                                                        {
                                                            'Type': 'forward',
                                                            'TargetGroupArn': self.target_group_arn

                                                        }
                                                      ])
            
            self.arn = self.summary['Listeners'][0]['ListenerArn']

    def delete(self):
        
        self.client.delete_listener(ListenerArn = self.arn)

# Create ec2 client conection 
ec2_ohio = create_client("us-east-2")
ec2_north_virginia = create_client("us-east-1")

# Postgres
SECURITY_GROUP_POSTGRES = [
    {
        'IpProtocol': 'tcp',
        'FromPort': 22,
        'ToPort': 22,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
        'IpProtocol': 'tcp',
        'FromPort': 5432,
        'ToPort': 5432,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    }
]

# Postgres user data
USER_DATA_POSTGRES = """
#cloud-config
runcmd:
- cd /
- sudo apt update -y
- sudo apt install postgresql postgresql-contrib -y
- sudo su - postgres
- sudo -u postgres psql -c "CREATE USER cloud WITH PASSWORD 'cloud';"
- sudo -u postgres psql -c "CREATE DATABASE tasks;"
- sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tasks TO cloud;"
- sudo echo "listen_addresses = '*'" >> /etc/postgresql/12/main/postgresql.conf
- sudo echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/12/main/pg_hba.conf
- sudo ufw allow 5432/tcp -y
- sudo systemctl restart postgresql
"""

# -------------------------------------------------------------------------------------------

cursorOH = Cursor(ec2_ohio, "us-east-2","ohio-key-pair")
cursorOH.createKeyPair()

postgresOH = Instance(cursorOH, "ohio")
postgresOH.create_security_group(SECURITY_GROUP_POSTGRES)
postgresOH.create_instance(USER_DATA_POSTGRES)

logging.info(f"Ohio Postgres Instance IP: {get_ip(postgresOH, postgresOH.id)}")
print(f"Ohio Postgres Instance IP: {get_ip(postgresOH, postgresOH.id)}")

file = open(f'C:/Users/eikis/.ssh/{postgresOH.cursor.keypair["KeyName"]}.pem', "w")
file.write(postgresOH.cursor.keypair["KeyMaterial"])
file.close()

# -------------------------------------------------------------------------------------------

# Django
SECURITY_GROUP_DJANGO = [
    {
        'IpProtocol': 'tcp',
        'FromPort': 22,
        'ToPort': 22,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
        'IpProtocol': 'tcp',
        'FromPort': 8080,
        'ToPort': 8080,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
        'IpProtocol': 'tcp',
        'FromPort': 80,
        'ToPort': 80,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    }
]

# Django user data
USER_DATA_DJANGO = f"""
#cloud-config
runcmd:
- sudo apt update
- cd /home/ubuntu 
- git clone https://github.com/EikiYamashiro/tasks.git
- cd tasks
- sed -i "s/node1/{get_ip(postgresOH, postgresOH.id)}/g" ./portfolio/settings.py
- ./install.sh
- sudo ufw allow 8080/tcp -y
- sudo reboot
"""

cursorNV = Cursor(ec2_north_virginia, "us-east-1","north-virginia-key-pair")
cursorNV.createKeyPair()

djangoNV = Instance(cursorNV, "north-virginia")
djangoNV.create_security_group(SECURITY_GROUP_DJANGO)
djangoNV.create_instance(USER_DATA_DJANGO)

logging.info(f"North Virginia Django Instance IP: {get_ip(djangoNV, djangoNV.id)}")
print(f"North Virginia Django Instance IP: {get_ip(djangoNV, djangoNV.id)}")

file = open(f'C:/Users/eikis/.ssh/{djangoNV.cursor.keypair["KeyName"]}.pem', "w")
file.write(djangoNV.cursor.keypair["KeyMaterial"])
file.close()

client_load_balancer = create_client("us-east-1", "elbv2")
client_auto_scalling = create_client("us-east-1", "autoscaling")

imageNV = Image(djangoNV)

logging.info(f"Image {imageNV.id} created")
print(f"Image {imageNV.id} created")

djangoNV.delete_instance(force_delete = True)
logging.info(f"Instance {djangoNV.id} (Django) from {djangoNV.region} deleted")
print(f"Instance {djangoNV.id} (Django) from {djangoNV.region} deleted")

target_groupNV = TargetGroup(client_load_balancer, "target-group-NV", 'HTTP', 8080, 'instance', cursorNV.get_vpc_id())
logging.info(f"Target Group {target_groupNV.name} created")
print(f"Target Group {target_groupNV.name} created")

load_balancerNV = LoadBalancer(client_load_balancer, djangoNV)
load_balancerNV.create(ec2_north_virginia)
logging.info(f"Load Balancer {load_balancerNV.name} created")
print(f"Load Balancer {load_balancerNV.name} created")

launch_config(client_auto_scalling, "launch_config", imageNV, djangoNV.security_group["GroupId"], cursorNV)
logging.info("Launch Configuration Created")
print("Launch Configuration Created")

as_group = auto_scalling_group(ec2_north_virginia, client_auto_scalling, target_groupNV)
logging.info("Auto Scaling Group created")
print("Auto Scaling Group created")

attach = client_auto_scalling.attach_load_balancer_target_groups(
        AutoScalingGroupName="as_name",
        TargetGroupARNs=[
            target_groupNV.arn,
        ]
    )
logging.info(f"Load Balancer {load_balancerNV.name} attached to Target Group {target_groupNV.name}")
print(f"Load Balancer {load_balancerNV.name} attached to Target Group {target_groupNV.name}")
listener = Listener(client_load_balancer, load_balancerNV.arn, target_groupNV.arn)
logging.info("Listener created")
print("Listener created")
auto_scaling_policy = create_auto_scaling_policy(client_auto_scalling, "as_name", load_balancerNV, target_groupNV)
logging.info("Auto Scaling Poolicy created")
print("Auto Scaling Poolicy created")

flag = True
while flag:
    print(" ")
    print("--------------------------MANAGER-MENU--------------------------")
    print("Select a action:")
    response = input("(1) Stop and Delete\n(2) Save data")
    
    if response == "1":
        cursorOH.deleteKeyPair()
        postgresOH.delete_instance()
        postgresOH.delete_security_group()

        cursorNV.deleteKeyPair()
        djangoNV.delete_security_group()

        imageNV.cursor.client.deregister_image(ImageId = imageNV.id)
        logging.info(f"Image {imageNV.id} deleted")

        load_balancerNV.delete()

        time.sleep(30)

        target_groupNV.client.delete_target_group(TargetGroupArn = target_groupNV.arn)
        logging.info(f"Target Group {target_groupNV.name} deleted")

        time.sleep(10)

        delete_as_group(client_auto_scalling, "as_name")
        logging.info("Auto Scaling Group deleted")

        time.sleep(10)

        delete_launch_config(client_auto_scalling, "launch_config")
        logging.info("Launch Config deleted")
        
        delete_flag = True
        while delete_flag:
            print("--------------------------MANAGER-MENU--------------------------")
            print("Select a action:")
            response = input("(1) Deploy\n(2) Exit")
            if response == "1":
                delete_flag = False
            elif response == "2":
                delete_flag = False
                flag = False
            
        
    elif response == "2":
        print("Data saved!")
        
    else:
        pass




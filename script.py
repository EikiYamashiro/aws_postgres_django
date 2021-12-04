# eikily@al.insper.edu.br

import sys
import boto3
import time
OHIO_NAME = "ohio_key_pair"
NORTH_VIRGINIA_NAME = "north_virginia_key_pair"
from functions import *
from cursor import *
from instance import *
from image import *

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
    }
]

# Django user data
USER_DATA_DJANGO = f"""
#cloud-config
runcmd:
- cd /home/ubuntu 
- sudo apt update -y
- git clone https://github.com/raulikeda/tasks
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

print(f"North Virginia Django Instance IP: {get_ip(djangoNV, djangoNV.id)}")

file = open(f'C:/Users/eikis/.ssh/{djangoNV.cursor.keypair["KeyName"]}.pem', "w")
file.write(djangoNV.cursor.keypair["KeyMaterial"])
file.close()
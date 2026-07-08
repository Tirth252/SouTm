import boto3
from botocore.exceptions import ClientError
import time
import paramiko
from .rcon_service import execute_rcon_cmd
import valve.source.a2s
privkey = paramiko.RSAKey.from_private_key_file("<REDACTED_PRIVATE_KEY_PATH>")
host = '<REDACTED_SSH_USER>'
password = '<REDACTED_SSH_PASSWORD>'
port = 22
# import json


Running_Instances_Id=[]
# Running_Instances_Name=[]
Stopped_Instances_Id=[]
# Stopped_Instances_Name=[]

ec2 = boto3.client('ec2')
ec2r = boto3.resource('ec2')

ec2_data = ec2.describe_instances()
instance_id = []
instance_id.clear()


for i in ec2_data['Reservations']:
    # print(i,end="\n\n\n\n\n\n\n\n")
    for j in i['Instances']:
    
        if j['State']['Code'] == 16:
            Running_Instances_Id.append(j['InstanceId'])
            #Running_Instances_Name.append(j['Tags'][0]['Value'])
        if j['State']['Code'] == 80:
            Stopped_Instances_Id.append(j['InstanceId'])
            #Stopped_Instances_Name.append(j['Tags'][0]['Value'])

# print(Running_Instances_Id,Stopped_Instances_Id)
def Start(instance_id):
    try:
        ec2.start_instances(InstanceIds=[instance_id],DryRun = True)
    except ClientError as e:
        if 'DryRunOperation' not in str(e):
            raise
    try:
        response = ec2.start_instances(InstanceIds=[instance_id],DryRun = False)
        print(response)
    except ClientError as e:
        print(e)


def Stop(instance_id):
    try:
        ec2.stop_instances(InstanceIds=[instance_id],DryRun = True)
    except ClientError as e:
        if 'DryRunOperation' not in str(e):
            raise
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id],DryRun = False)
        print(response)
    except ClientError as e:
        print(e)

def Terminate(instance_id):
    try:
        ec2.terminate_instances(InstanceIds=[instance_id],DryRun = True)
    except ClientError as e:
        if 'DryRunOperation' not in str(e):
            raise
    try:
        response = ec2.terminate_instances(InstanceIds=[instance_id],DryRun = False)
        print(response)
    except ClientError as e:
        print(e)

def StartAserver(temp):

    Start(temp)
    instance = ec2r.Instance(temp)
    instance.wait_until_running()
    publicIp = instance.public_ip_address

    return f'Server started successfully!'



def StopAserver(Id):

    instance = ec2r.Instance(Id)
    Stop(Id)
    
    instance.wait_until_stopped()

    return f'Server stopped successfully!'


def CreateServers(servers,port = 27015):
    data = []
    try:
        servers = ec2r.create_instances(ImageId = 'ami-0252cd2abfc64e91e',MaxCount = servers,MinCount = servers,InstanceType = 't2.micro',KeyName='Testkey1',SecurityGroupIds=['sg-0a1fa41aa4a15bf19'])
        
        print(servers)
        for temp in servers:
            temp.wait_until_running()
            instance = ec2r.Instance(temp.instance_id)
            Running_Instances_Id.append(instance.instance_id)
            publicIp = instance.public_ip_address
            instance.create_tags(Tags = [{"Key":"Name", "Value":"test"}])
            instanceName = instance.tags[0]['Value']
            data.append({'instance':instance.id, 'ip':f'{publicIp}:{port}'})
    except ClientError as e:
        print(e)
    return data


def ServerState(aws_id):
    instance = ec2r.Instance(aws_id)
    print('wasd')
    try:
        print(instance.state)
        if instance.state:
            return instance.state['Name']
    except AttributeError:
        return "Terminated"



def Connection_close(ssh):
    ssh.close()
    print('Session Closed')


def Start_cs(ip):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, port, host, password)
    print('Session opened')
    stdin, stdout, stderr = ssh.exec_command('./csgoserver start')
    time.sleep(5)
    temp = stdout.readlines()
    Connection_close(ssh)
    return temp[0]


def Stop_cs(ip):
    ssh = paramiko.SSHClient()  
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, port, host, password)
    print('Session opened')
    stdin, stdout, stderr = ssh.exec_command('./csgoserver stop')
    time.sleep(5)
    temp = stdout.readlines()
    Connection_close(ssh)
    return temp[0]
    

def Command_to_server(ip,command):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())   
        ssh.connect(ip, port, host, password)
        print('Session opened')
        time.sleep(5)
        stdin, stdout, stderr = ssh.exec_command(command)
        time.sleep(5)
        Connection_close(ssh)
 
    except paramiko.ssh_exception.NoValidConnectionsError:
        Command_to_server(ip,command)

    return stdout.readlines()
    

def get_rcon(ip):
    try:
        lines = Command_to_server(ip,"./csgoserver dt")
        return lines[51][27:-1]
    except IndexError:
        get_rcon(ip)


def CScommand(ip,command):
    resp = execute_rcon_cmd(command,(ip,27015),get_rcon(ip))
    return resp


def Csstatus(ip):
    print(ip)
    
    lines = Command_to_server(ip,'./csgoserver dt')
    try:
        print(lines[-2][18:-5])
        return lines[-2][18:-5] 
    except IndexError:
        pass

    
    



def CurrentPlayerCount(ip):
    SERVER_ADDRESS = (ip,27015)
    try:
        with valve.source.a2s.ServerQuerier(SERVER_ADDRESS) as server:
            info = server.info()
            players = server.players()
    
        return("{player_count}/{max_players}".format(**info))
    except valve.source.NoResponseError:
        return None

    



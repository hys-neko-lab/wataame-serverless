import tempfile
from api import serverless_pb2
from api import serverless_pb2_grpc
from kubernetes import client, config, utils
import docker
import string, os

class Serverless(serverless_pb2_grpc.ServerlessServicer):
    registry_host = None
    registry_port = None
    def __init__(self, registry_host, registry_port):
        # Docker関係
        self.docker_client = docker.from_env()
        self.registry_host=registry_host
        self.registry_port=registry_port
        # Kubernetes関係
        config.load_kube_config()
        self.k8s_api = client.CoreV1Api()
        self.k8s_client = client.ApiClient()
    
    def createServerless(self, request, context):
        if self.k8s_api == None:
            message = "CoreV1Api failed."
            return serverless_pb2.CreateReply(message=message)

        if self.k8s_client == None:
            message = "ApiClient failed."
            return serverless_pb2.CreateReply(message=message)

        # ユーザーが書いた関数をHandler.pyとして作成
        handler = 'templates/docker/work/Handler.py'
        if(os.path.isfile(handler)):
            os.remove(handler)
        with open('templates/docker/work/Handler.py', 'w') as h:
            print(request.source, file=h)

        # Dockerイメージをビルド
        tag = self.registry_host+':'+self.registry_port+'/'+request.name
        self.docker_client.images.build(
            path='templates/docker',
            nocache=True,
            tag=tag
        )

        # Kubernetesからpullできるようにプライベートレジストリにpushする
        self.docker_client.images.push(tag)
        os.remove(handler)

        # Kubernetes名前空間以下を作成するyamlを書き換え
        with open('templates/serverless.yaml') as f:
            t = string.Template(f.read())
        yaml = t.substitute(
            name=request.name,
            registry_host=self.registry_host,
            registry_port=self.registry_port
        )
        print(yaml)
        
        # yamlをファイルとして実体化してからクラスタ作成
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml') as temp:
            print(yaml, file=temp)
            temp.flush()
            obj = utils.create_from_yaml(self.k8s_client, temp.name, verbose=True)
            print(obj)
            
        service = self.k8s_api.read_namespaced_service(
            name=request.name + '-svc',
            namespace=request.name + '-ns'
        )
        message = "NAME:" + request.name + " created."
        return serverless_pb2.CreateReply(message=service.spec.cluster_ip)

    def deleteServerless(self, request, context):
        if self.k8s_api == None:
            message = "CoreV1Api failed."
            return serverless_pb2.DeleteReply(message=message)
        
        obj = self.k8s_api.delete_namespace(
            name=request.name + '-ns'
        )
        if obj == None:
            message = "Delete service failed."
            return serverless_pb2.DeleteReply(message=message)
        
        message = "NAME:" + request.name + " deleted."
        return serverless_pb2.DeleteReply(message=message)
    
    def getPorts(self, request, context):
        if self.k8s_api == None:
            message = "CoreV1Api failed."
            return serverless_pb2.PortsReply(message=message)

        service = self.k8s_api.read_namespaced_service(
            name=request.name + '-svc',
            namespace=request.name + '-ns'
        )

        # ノードのポートを取得(念の為複数ある場合を想定)
        message = ''
        for port in service.spec.ports:
            message += (str(port.node_port) + ',')
        
        return serverless_pb2.PortsReply(message=message)
from concurrent import futures
import grpc
import sys
from api import serverless_pb2_grpc
import serverless

def run(host, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    serverless_pb2_grpc.add_ServerlessServicer_to_server(
        serverless.Serverless(registry_host=host, registry_port=port),
        server
    )
    server.add_insecure_port('[::]:8084')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    args = sys.argv
    if len(args) == 3:
        run(args[1], args[2])
    else:
        print("Usage: python3 {} [hostname or ip] [hostpath]".format(args[0]))
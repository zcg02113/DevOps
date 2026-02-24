from channels.generic.websocket import WebsocketConsumer
from threading import Thread
from kubernetes import client
from DevOps import k8s

# 多线程
class K8sStreamThread(Thread):
    def __init__(self, websocket, conn_stream):
        Thread.__init__(self)
        self.websocket = websocket
        self.stream = conn_stream

    def run(self):
        for line in self.stream:
            # 读取流的输出，发送到websocket（前端）
            self.websocket.send(line.decode())
        else:
            self.websocket.close()

# 继承WebsocketConsumer 类，并修改下面几个方法，主要连接到容器
class StreamLogConsumer(WebsocketConsumer):
    def connect(self):
        # self.scope 请求头信息
        self.namespace = self.scope["url_route"]["kwargs"]["namespace"]
        self.pod_name = self.scope["url_route"]["kwargs"]["pod_name"]
        self.container = self.scope["url_route"]["kwargs"]["container"]

        k8s_auth = self.scope["query_string"].decode()  # b'auth_type=kubeconfig&token=7402e616e80cc5d9debe66f31b7a8ed6'
        auth_type = k8s_auth.split('&')[0].split('=')[1]
        token = k8s_auth.split('&')[1].split('=')[1]

        k8s.load_auth_config(auth_type, token)
        core_api = client.CoreV1Api()

        try:
            self.conn_stream = core_api.read_namespaced_pod_log(name=self.pod_name,
                                                                namespace=self.namespace,
                                                                follow = True,
                                                                _preload_content=False
                                                                ).stream()
            kube_stream = K8sStreamThread(self, self.conn_stream)
            kube_stream.start()
        except Exception as e:
            status = getattr(e, "status")
            if status == 403:
                msg = "没有访问容器日志权限！"
            else:
                msg = "访问容器异常！"
        self.accept()
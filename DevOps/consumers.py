#版本不同整个更改
from channels.generic.websocket import AsyncWebsocketConsumer
from kubernetes.stream import stream
from asgiref.sync import sync_to_async
from threading import Thread
from kubernetes import client
from DevOps import k8s
import asyncio
import time


# 多线程处理容器流
class K8sStreamThread(Thread):
    def __init__(self, websocket, container_stream, loop):
        Thread.__init__(self)
        self.websocket = websocket      #
        self.stream = container_stream  # 统一使用 self.stream,数据发给谁
        self.loop = loop                #异步事件
#检查容器的输出流发送给浏览器
    def run(self):
        # 只要流还开着，就持续读取
        while self.stream.is_open():
            # 1. 读取标准输出
            if self.stream.peek_stdout():
                stdout = self.stream.read_stdout()      #读取容器的标志输出有没有新内容
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(text_data=stdout),  #读取的新内容发给浏览器
                    self.loop
                )

            # 2. 读取标准错误
            if self.stream.peek_stderr():
                stderr = self.stream.read_stderr()      #读取容器的标志错误有没有新内容
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(text_data=stderr),
                    self.loop
                )

            # 3. 稍微休眠，防止死循环导致 CPU 飙升
            time.sleep(0.01)
        else:
            # 容器连接关闭后，通知前端关闭 WebSocket
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)


class StreamConsumer(AsyncWebsocketConsumer):

    def _setup_kubernetes_stream(self, loop):
        try:
            k8s.load_auth_config(self.auth_type, self.token)    #通过connect获取验证类型和token跟api交互认证
            core_api = client.CoreV1Api()                       #资源接口实例化

            # 终端初始化命令
            exec_command = [
                "/bin/sh",
                "-c",
                'TERM=xterm-256color; export TERM; [ -x /bin/bash ] '
                '&& ([ -x /usr/bin/script ] '
                '&& /usr/bin/script -q -c "/bin/bash" /dev/null || exec /bin/bash) '
                '|| exec /bin/sh']

            # 建立 K8s Stream
            self.conn_stream = stream(core_api.connect_get_namespaced_pod_exec,
                                      name=self.pod_name,
                                      namespace=self.namespace,
                                      command=exec_command,
                                      container=self.container,
                                      stderr=True, stdin=True,
                                      stdout=True, tty=True,
                                      _preload_content=False)

            # 启动读取线程
            kube_stream = K8sStreamThread(self, self.conn_stream, loop)
            kube_stream.start()
            return True, ""
        except Exception as e:
            print(f"K8s Stream Error: {e}")
            status = getattr(e, "status", None)
            msg = "你没有权限或参数错误！" if status == 403 else "连接容器错误！"
            return False, msg

    async def connect(self):
        # 获取路由参数
        self.namespace = self.scope["url_route"]["kwargs"]["namespace"]
        self.pod_name = self.scope["url_route"]["kwargs"]["pod_name"]
        self.container = self.scope["url_route"]["kwargs"]["container"]
        print(self.scope)
        # 获取认证参数
        query_params = self.scope["query_string"].decode()
        # 建议更健壮的解析方式
        params = dict(p.split('=') for p in query_params.split('&'))
        print(params)
        self.auth_type = params.get('auth_type', 'kubeconfig')      #获取验证类型
        self.token = params.get('token', '')                        #获取token

        # 获取 loop 并异步执行阻塞操作
        loop = asyncio.get_running_loop()
        success, message = await sync_to_async(self._setup_kubernetes_stream)(loop)

        if success:
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'conn_stream') and self.conn_stream:
            try:
                # 尝试优雅退出
                await sync_to_async(self.conn_stream.write_stdin)('exit\r')
                self.conn_stream.close()
            except:
                pass
        print("WebSocket 连接已断开")

    async def receive(self, text_data):     #text_data:为用户输入的信息
        # 接收前端输入并传给容器
        if hasattr(self, 'conn_stream'):
            await sync_to_async(self.conn_stream.write_stdin)(text_data)    #数据通过self.conn_stream.write_stdin被写入


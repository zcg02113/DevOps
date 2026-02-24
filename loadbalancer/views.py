from django.shortcuts import render
from kubernetes import client, config
from DevOps import k8s
from django.http import JsonResponse,QueryDict
import re
# Create your views here.
def service(request):
    return render(request, 'loadbalancer/service.html')
def service_api(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()
    if request.method == 'GET':
        # 调用k8s_api
        data =[]
        search_key = request.GET.get("search_key")
        namespace = request.GET.get("namespace")
        try:
            for svc in core_api.list_namespaced_service(namespace=namespace).items:
                name = svc.metadata.name
                namespace = svc.metadata.namespace
                labels = svc.metadata.labels
                type = svc.spec.type
                cluster_ip = svc.spec.cluster_ip
                ports = []
                for p in svc.spec.ports:  # 不是序列，不能直接返回
                    port_name = p.name
                    port = p.port
                    target_port = p.target_port
                    protocol = p.protocol
                    node_port = ""
                    if type == "NodePort":
                        node_port = " <br> NodePort: %s" % p.node_port
                    port = {'port_name': port_name, 'port': port, 'protocol': protocol, 'target_port': target_port,
                            'node_port': node_port}
                    ports.append(port)

                selector = svc.spec.selector
                create_time = svc.metadata.creation_timestamp

                # 确认是否关联Pod
                endpoint = ""
                for ep in core_api.list_namespaced_endpoints(namespace=namespace).items:
                    if ep.metadata.name == name and ep.subsets is None:
                        endpoint = "未关联"
                    else:
                        endpoint = "已关联"
                svc = {"name": name, "namespace": namespace, "type": type,
                       "cluster_ip": cluster_ip, "ports": ports, "labels": labels,
                       "selector": selector, "endpoint": endpoint, "create_time": create_time}
                if search_key:
                    if search_key in name:
                        data.append(svc)
                else:
                    data.append(svc)
            code = 0
            msg = '查询成功'
        except Exception as e:
            code = 1
            msg = '查询失败'
        #分页
        count = len(data)
        if request.GET.get('page'):  # 如果为真则数据表格带有分页
            page = int(request.GET.get('page'))
            limit = int(request.GET.get('limit'))
            # data = data[0:10]
            start = (page - 1) * limit  # 切片的起始值
            end = page * limit  # 切片的末值
            data = data[start:end]  # 返回指定数据范围
        result = {'code': code, 'msg': msg, 'data': data, 'count': count}
        return JsonResponse(result)
    elif request.method == 'DELETE':
        request_data = QueryDict(request.body)
        name = request_data.get("name")
        namespace = request_data.get("namespace")
        try:
            core_api.delete_namespaced_service(namespace=namespace, name=name)
            code = 0
            msg = "删除Service成功!"
        except Exception as e:
            status = getattr(e, 'status')
            if status == 403:
                msg = "没有权限！"
            else:
                msg = "删除Service失败！"
            code = 1
        result = {'code': code, 'msg': msg}
        return JsonResponse(result)

    elif request.method == 'POST':
            post_data = request.POST
            print(post_data)
            name = post_data.get("name")
            namespace = post_data.get("namespace")
            service_type = post_data.get("serviceType")
            # 1. 解析 labels
            labels = {}
            try:
                for l in request.POST.get("labels", None).split(","):
                    k = l.split("=")[0]
                    v = l.split("=")[1]
                    labels[k] = v
            except Exception as e:
                res = {"code": 1, "msg": "标签格式错误！"}
                return JsonResponse(res)

            # 2. 动态解析所有端口数据
            # 我们将解析 ports[0][port], ports[0][targetPort] ... 这样的数据
            # 并将其存入一个字典，键为索引(0, 1, ...)，值为另一个包含端口信息的字典
            ports_map = {}
            port_pattern = re.compile(r'ports\[(\d+)\]\[(\w+)\]')
            for key, value in post_data.items():
                match = port_pattern.match(key)     #通过正则表达式匹配获取ports[0-n][port_name]
                if match and value:  # 确保值不为空
                    index = int(match.group(1))     #获取ports[0-n][port_name]中的0-n
                    prop = match.group(2)           #获取ports[0-n][port_name]中的port_name的值
                    if index not in ports_map:
                        ports_map[index] = {}
                    ports_map[index][prop] = value
                    #组成新的字典: {
                                #     0: {
                                #         'port': '80',
                                #         'targetPort': '8080',
                                #         'protocol': 'TCP'
                                #     },
                                #     1: {
                                #         'port': '443',
                                #         'targetPort': '8443',
                                #         'protocol': 'TCP',
                                #         'nodePort': '30443'
                                #     }
                                # }
            # 将解析出的字典转换为按索引排序的列表
            ports_list = [ports_map[i] for i in sorted(ports_map.keys())]
            print(ports_list)
            # 3. 构建 V1ServicePort 对象列表
            node_port_str = request.POST.get('nodePort')
            service_port_objects = []
            for i, p_dict in enumerate(ports_list):
                # 处理 target_port：尝试转为 int，失败则保留 string (端口名)
                t_port = p_dict['targetPort']   #获取容器端口
                if t_port.isdigit():
                    t_port = int(t_port)

                service_port = client.V1ServicePort(
                    port=int(p_dict['port']),
                    target_port=t_port,
                    protocol=p_dict.get('protocol', 'TCP'),
                    name=p_dict.get('port_name') or f"port-{i}"
                )
                # 重点：修正 NodePort 重复赋值逻辑
                # 只有在 NodePort 类型下，且用户输入了值时赋值
                # 注意：如果定义了多个端口，只有第一个端口会获得该 NodePort，
                # 或者你需要修改前端让每个端口行都有独立的 NodePort 输入框。
                if service_type == 'NodePort' and node_port_str and i == 0:
                    try:
                        service_port.node_port = int(node_port_str)
                        print(service_port.node_port)
                    except ValueError:
                        return JsonResponse({"code": 1, "msg": "NodePort 必须是 30000-32767 之间的数字"})
                service_port_objects.append(service_port)


            if not service_port_objects:
                return JsonResponse({"code": 1, "msg": "必须提供至少一个端口配置！"})



            # 4. 构建完整的 Service Body 并提交
            try:
                body = client.V1Service(
                    api_version="v1",
                    kind="Service",
                    metadata=client.V1ObjectMeta(
                        name=name,
                        labels=labels  # 将 labels 放在 metadata 中是更常见的做法
                    ),
                    spec=client.V1ServiceSpec(
                        selector=labels,  # selector 使用与 Pod 匹配的标签
                        ports=service_port_objects,  # <-- 使用我们动态创建的对象列表
                        type=service_type
                    )
                )

                core_api.create_namespaced_service(namespace=namespace, body=body)
                result = {'code': 0, 'msg': '创建成功'}

            except Exception as e:
                # 捕获k8s api可能返回的异常
                result = {'code': 1, 'msg': f'创建失败: {getattr(e, "body", str(e))}'}

            return JsonResponse(result)

        # 如果是GET请求，返回你的HTML页面
        # return render(request, 'your_template.html')


def ingress(request):
    return render(request, 'loadbalancer/ingress.html')
def ingress_api(request):
    # 获取当前用户登录凭据，调用k8s api操作命名空间
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    networking_api =  client.NetworkingV1Api()

    if request.method == "GET":
        data = []
        search_key = request.GET.get("search_key")
        namespace = request.GET.get("namespace")
        try:
            for ing in networking_api.list_namespaced_ingress(namespace=namespace).items:
                name = ing.metadata.name
                namespace = ing.metadata.namespace
                labels = ing.metadata.labels
                service = "None"
                http_hosts = "None"
                for h in ing.spec.rules:
                    host = h.host
                    path = ("/" if h.http.paths[0].path is None else h.http.paths[0].path)
                    service_name = h.http.paths[0].backend.service.name
                    service_port = h.http.paths[0].backend.service.port.number
                    http_hosts = {'host': host, 'path': path, 'name': service_name,
                                  'service_port': service_port}

                https_hosts = "None"
                if ing.spec.tls is None:
                    https_hosts = ing.spec.tls
                else:
                    for tls in ing.spec.tls:
                        host = tls.hosts[0]
                        secret_name = tls.secret_name
                        https_hosts = {'host': host, 'secret_name': secret_name}

                create_time = ing.metadata.creation_timestamp

                ing = {"name": name, "namespace": namespace, "labels": labels, "http_hosts": http_hosts,
                       "https_hosts": https_hosts, "service": service, "create_time": create_time}
                print(ing)
                # 根据查询关键字返回数据
                if search_key:
                    if search_key in name:
                        data.append(ing)
                else:
                    data.append(ing)
            code = 0
            msg = "查询成功."
        except Exception as e:
            print(e)
            status = getattr(e, 'status')
            if status == 403:
                msg = "没有访问权限！"
            else:
                msg = "查询失败！"
            code = 1

        # 分页
        count = len(data)  # 要在切片之前获取总数

        page = int(request.GET.get('page'))
        limit = int(request.GET.get('limit'))
        # data = data[0:10]
        start = (page - 1) * limit  # 切片的起始值
        end = page * limit  # 切片的末值
        data = data[start:end]  # 返回指定数据范围

        result = {'code': code, 'msg': msg, 'data': data, 'count': count}
        return JsonResponse(result)

    elif request.method == "DELETE":
        request_data = QueryDict(request.body)
        name = request_data.get("name")
        namespace = request_data.get("namespace")
        print(request_data)
        try:
            networking_api.delete_namespaced_ingress(namespace=namespace, name=name)
            code = 0
            msg = "删除成功."
        except Exception as e:
            status = getattr(e, 'status')
            if status == 403:
                msg = "没有访问权限！"
            else:
                msg = "删除失败！"
            code = 1

        result = {'code': code, 'msg': msg}
        return JsonResponse(result)


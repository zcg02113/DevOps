import kubernetes
import prom
import yaml
from django.db.models.expressions import result
from django.http import JsonResponse
from django.shortcuts import render, redirect
from DevOps import k8s
from dashboard.models import User ,Script
from kubernetes import client, config
from django.conf.urls.static import static
# Create your views here.
from dashboard import node_data
from prometheus_api_client import PrometheusConnect
@k8s.self_login_required
def index(request):
    return render(request,'home.html')
#登录界面
def login(request):
    if request.method == 'GET':
        return render(request,'login.html')
    elif request.method == 'POST':
        token = request.POST.get('token')
        if token:
            if k8s.auth_check('token',token):      #k8s.auth_check为自建的函数用于登录验证
                request.session['is_login'] = True
                request.session['auth_type'] = 'token' #用于后期前端调用django,django拿这个信息去请求k8s-api
                request.session['token'] = token
                code = 0
                msg = '登录成功'
            else:
                code = 1
                msg = '登录失败'
        else:
            file = request.FILES.get('file')        #获取文件
            try:
                context = file.read().decode()  #转换比特类型为str
                import random
                token_random = str(random.random()).split('.')[1]  #生成一个随机的token
                User.objects.create(            #增加数据
                    auth_type = 'kubeconfig',
                    token =token_random,
                    content = context
                )
            except Exception :
                code = 1
            if   k8s.auth_check('kubeconfig', token_random):
                request.session['is_login'] = True
                request.session['auth_type'] = 'kubeconfig'
                request.session['token'] = token_random
                code = 0
                msg = '登录成功'
            else:
                User.objects.get(token=token_random).delete()
                code = 1
                msg = 'kubeconfig文件无效'
        result = {'code': code, 'msg': msg}
        return JsonResponse(result)

def logout(request):        #退出
    request.session.flush()
    return redirect(login)

from django.views.decorators.clickjacking import xframe_options_exempt
@xframe_options_exempt
def ace_editor(request):
    data= {}                                    #点击yaml按钮获取数据
    namespace = request.GET.get('namespace')    #获取命名空间
    name = request.GET.get('name')              #获取名称
    resource = request.GET.get('resource')      #获取类型:pod,node,deployment...
    id = request.GET.get('id')
    data['id'] = id
    data['namespace'] = namespace
    data['name'] = name
    data['resource'] = resource
    return render(request,'aec_editor.html',{'data':data})
def b_to_yaml(content):             #将二进制转换为yaml
    import json,yaml
    s = content.decode()  # 转换为字符串
    json_obj = json.loads(s)  # 转换成json
    y = yaml.safe_dump(json_obj)  # json转yaml
    return y
def export_resource_api(request):       #获取yaml信息进行输出
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    networking_api = client.NetworkingV1Api()  # ingress
    namespace = request.GET.get('namespace')
    resource = request.GET.get('resource')
    name = request.GET.get('name')
    id = request.GET.get('id')
    code = 0
    msg = '获取成功'
    if resource == 'namespace':
        content = core_api.read_namespace(name=name).read()  #读取命名空间的yaml,数据为字节格式通过b_to_yaml转换为yaml格式
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == 'deployment':
        content = apps_api.read_namespaced_deployment(name=name,namespace=namespace,_preload_content=False).read()
            #默认有预返回的实例,就无法使用read()进行读取,将_preload_content=False关闭就会返回另一种形式
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == 'pod':
        content = core_api.read_namespaced_pod(name=name,namespace=namespace,_preload_content=False).read()
            #默认有预返回的实例,就无法使用read()进行读取,将_preload_content=False关闭就会返回另一种形式
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == 'statefulset':
        content = apps_api.read_namespaced_stateful_set(name=name, namespace=namespace, _preload_content=False).read()
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == 'node':
        content = core_api.read_node(name=name, _preload_content=False).read()
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == 'service':
        content = core_api.read_namespaced_service(name=name, namespace=namespace, _preload_content=False).read()
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == "ingress":
        content = networking_api.read_namespaced_ingress(name=name, namespace=namespace, _preload_content=False).read()
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == "pvc":
        content = core_api.read_namespaced_persistent_volume_claim(name=name, namespace=namespace, _preload_content=False).read()
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == "configmap":
        content = core_api.read_namespaced_config_map(name=name, namespace=namespace, _preload_content=False).read()
        res = {'code': code, 'msg': msg,'data': b_to_yaml(content)}
        return JsonResponse(res)
    elif resource == "script":
        script = Script.objects.get(id=id)
        content =  script.content
        res = {'code': code, 'msg': msg, 'data': content}
        return JsonResponse(res)
    elif resource == "daemonset":
        content = apps_api.read_namespaced_daemon_set(name=name, namespace=namespace, _preload_content=False).read()
        res = {'code': code, 'msg': msg, 'data': b_to_yaml(content)}
        return JsonResponse(res)
def apply_yaml(request):            #更改yaml信息
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    networking_api = client.NetworkingV1beta1Api()  # ingress
    storage_api = client.StorageV1Api()  # storage_class
    yaml_content = request.POST.get('yaml_content')
    content = yaml.safe_load(yaml_content) #yaml转成字典
    kind = content['kind']
    namespace = content['metadata']['namespace']
    name = content['metadata']['name']
    code = 0
    msg = '应用yaml成功'
    if kind == "PersistentVolume":
        core_api.patch_persistent_volume(body=content, name=name)
    elif kind == "Deployment":
        apps_api.patch_namespaced_deployment(body=content, namespace=namespace, name=name)
    elif kind == "DaemonSet":
        apps_api.patch_namespaced_daemon_set(body=content, namespace=namespace, name=name)
    elif kind == "Service":
        core_api.patch_namespaced_service(body=content, namespace=namespace, name=name)
    elif kind == "DaemonSet":
        apps_api.patch_namespaced_daemon_set(body=content, namespace=namespace, name=name)
    elif kind == "StatefulSet":
        apps_api.patch_namespaced_stateful_set(body=content, namespace=namespace, name=name)
    elif kind == "Pod":
        core_api.patch_namespaced_pod(body=content, namespace=namespace, name=name)
    elif kind == "Ingress":
        networking_api.patch_namespaced_ingress(body=content, namespace=namespace, name=name)
    elif kind == "PersistentVolumeClaim":
        core_api.patch_namespaced_persistent_volume_claim(body=content, namespace=namespace, name=name)
    elif kind == "ConfigMap":
        core_api.patch_namespaced_config_map(body=content, namespace=namespace, name=name)
    elif kind == "Secret":
        core_api.patch_namespaced_secret(body=content, namespace=namespace, name=name)
    else:
        code = 1
        msg = "暂不支持该资源类型更新！"
    res = {'code': code, 'msg': msg}
    return JsonResponse(res)
def node_resource(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()

    result = node_data.node_resource(core_api)
    return JsonResponse(result)
PROMETHEUS_URL = 'http://192.168.37.143:31224'  #prometheus的ip地址
import datetime
from datetime import timedelta, datetime

def memory(request):
    #连接prometheus
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    #查询语句
    query = 'sort_desc(sum(container_memory_working_set_bytes{image!=""}) by (pod))'
    #执行查询
    metric_data = prom.custom_query(query=query)
    pod_data = []
    for item in metric_data:
        pod_data.append({'name': item['metric']['pod'],
                         'memory_bytes': int(item['value'][1])})    #获取下标为1的值

    pod_data.sort(key=lambda item: item['memory_bytes'], reverse=True)   #通过key的值进行排序,reverse=True表示从大到小排序
    pod_top5 = pod_data[:5]         #列表切片取前五个元素
    for pod in pod_top5:
        pod['memory_mb'] = round(pod['memory_bytes'] / (1024 * 1024), 2)
    code =0
    msg = '查询成功'
    result = {'code': code, 'msg': msg,'data':pod_top5}
    return JsonResponse(result)
#Echar
# uPlot
#     all_pod_names = []
#     for i in metric_data:
#         all_pod_names.append(i['metric']['pod'])
# # 2. 获取前5个名字，并使用一个有意义的变量名
#     top_5_names_list = all_pod_names[:5]
# # 3. 生成查询字符串
#     pod_match_str = '|'.join(top_5_names_list)
#     #查询使用前五的内存使用量
#     history_query = f'sum(container_memory_working_set_bytes{{pod=~"{pod_match_str}"}}) by (pod)'
#     end_time = datetime.now()           #结束的时间
#     start_time = end_time - timedelta(minutes=30)       #开始的时间
#     #执行查询三十分钟内的内存数据(60s显示一次数据)
#     metric_data_history = prom.custom_query_range(query=history_query, start_time=start_time, end_time=end_time,step='60s')
#     grouped_data = {}
#     all_time = set()  #定义集合去重,用于唯一时间戳
#     for metric in metric_data_history:
#         pod_name = metric['metric']['pod']
#         value = metric['values']
#         if pod_name not in grouped_data:
#             grouped_data[pod_name] = {}
#         for val in value:
#             timestamp = int(val[0])     #时间戳
#             memory_mb = round(int(val[1])/(1024*1024),2 )  #具体数值
#             grouped_data[pod_name][timestamp] = memory_mb  #{{pod_name}
#             all_time.add(timestamp)         #记录时间戳
    #数据整理(uPlot)
    # sorted_time = sorted(list(all_time))      #时间
    # y_series_data = []
    # for name in top_5_names_list:
    #     series_for_pod = [grouped_data.get(name, {}).get(ts, None) for ts in sorted_time]
    #     y_series_data.append(series_for_pod)
    # uplot_data = [sorted_time] + y_series_data
    # #准备uPlot的series options(图例,颜色等)
    # colors = ["#3498db", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6"]
    # series_options = []
    # for i ,name in enumerate(top_5_names_list):
    #     series_options.append({'label': name, 'stroke': colors[i % len(colors)],'width':1})
    # chart_data = {
    #     'data': uplot_data,
    #     'series_options': series_options,
    # }
    return JsonResponse({'success': True, 'data': chart_data})
def cpu(request):
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    # 查询语句
    query = '(sum(rate(container_cpu_usage_seconds_total{image!="",pod!=""}[1m])) by(pod))/(sum(container_spec_cpu_quota{image!="", pod!=""}) by(pod) / 100000) * 100'

    # 执行查询
    metric_data = prom.custom_query(query=query)
    pod_data = []
    for item in metric_data:
        pod_data.append({'name': item['metric']['pod'],
                         'cpu': float(item['value'][1])})  # 获取下标为1的值
    pod_data.sort(key=lambda item: item['cpu'], reverse=True)
    pod_top5 = pod_data[:5]
    code = 0
    msg = '查询成功'
    result = {'code': code, 'msg': msg, 'data': pod_top5}
    return JsonResponse(result)
def io(request):
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    """
    一个API视图，用于获取指定节点的磁盘和网络指标
    """
    # 从前端获取节点名称，例如 'node-1'
    # 为了演示，这里硬编码一个值，实际应用中应从 request.GET.get('node') 获取
    node_name = request.GET.get('node') # 请替换为你的一个节点名
    # 定义时间范围（例如：过去一小时）
    end_time = datetime.now()                       #当前时间
    start_time = end_time - timedelta(hours=1)      #创建一个小时的间隔

    # --- 1. 磁盘 I/O 查询 (Bytes/sec) ---
    # 使用 rate() 函数计算每秒的变化率
    # node_disk_read_bytes_total 和 node_disk_written_bytes_total 是 node-exporter 提供的指标
    disk_read_query = f'rate(node_disk_read_bytes_total{{instance=~"{node_name}.*"}}[5m])'
    disk_write_query = f'rate(node_disk_written_bytes_total{{instance=~"{node_name}.*"}}[5m])'
    # --- 2. 网络流量查询 (Bytes/sec) ---
    # device!~"lo" 排除了本地环回设备
    net_receive_query = f'rate(node_network_receive_bytes_total{{instance=~"{node_name}.*", device!~"lo"}}[5m])'
    net_transmit_query = f'rate(node_network_transmit_bytes_total{{instance=~"{node_name}.*", device!~"lo"}}[5m])'

    try:
        # 执行范围查询
        disk_read_data = prom.custom_query_range(query=disk_read_query, start_time=start_time, end_time=end_time, step='60s')
        disk_write_data = prom.custom_query_range(query=disk_write_query, start_time=start_time, end_time=end_time,step='60s')
        net_receive_data = prom.custom_query_range(query=net_receive_query, start_time=start_time, end_time=end_time, step='60s')
        net_transmit_data = prom.custom_query_range(query=net_transmit_query, start_time=start_time, end_time=end_time, step='60s')


        # 将数据格式化为 ECharts 需要的格式 [[timestamp, value], ...]
        def format_data(prom_data):
            if prom_data:
                # 多个设备/磁盘的数据会在这里，我们简单地取第一个
                # 实际中你可能需要聚合(sum)它们
                return [[int(i[0]), round(float(i[1]), 2)] for i in prom_data[0]['values']]
            return []

        response_data = {
            "disk_io": {
                "read": format_data(disk_read_data),
                "write": format_data(disk_write_data),
            },
            "network": {
                "receive": format_data(net_receive_data),
                "transmit": format_data(net_transmit_data),
            }
        }
        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)







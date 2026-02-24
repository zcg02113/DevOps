import re
from itertools import count
from re import search

from django.http import JsonResponse, QueryDict, HttpResponse
from django.shortcuts import render
from kubernetes import client, config
from DevOps import k8s
from dashboard import node_data

# Create your views here.
@k8s.self_login_required
def home(request):
    #计算资源:准备一个计算资源的接口,ajax访问整个接口获取数据 动态渲染
    return render(request, 'home.html')


@k8s.self_login_required
def node(request):
    return render(request, 'k8s/node.html')
@k8s.self_login_required
def namespace(request):
    return render(request, 'k8s/namespace.html')
@k8s.self_login_required
def namespace_api(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)   #验证
    core_api = client.CoreV1Api()
    if request.method == 'GET':
        data =[]
        search_key = request.GET.get("search_key")   #

        try:
            #调用k8s获取命名空间
            for ns in core_api.list_namespace().items:  # items返回一个对象，类LIST（[{命名空间属性},{命名空间属性}] ），每个元素是一个类字典（命名空间属性），操作类字典
                name = ns.metadata.name
                labels = ns.metadata.labels
                create_time = ns.metadata.creation_timestamp
                namespace = {"name": name, "labels": labels, "create_time": create_time}
                if search_key :
                    if search_key in name:
                        data.append(namespace)
                else:
                    data.append(namespace)
            code =0
            msg = '查询成功'
        except Exception :
            code = 1
            msg = '查询失败'
        count = len(data)
        if request.GET.get('page'):     #如果为真则数据表格带有分页
            page = int(request.GET.get('page'))
            limit = int(request.GET.get('limit'))
            # data = data[0:10]
            start = (page - 1) * limit  # 切片的起始值
            end = page * limit  # 切片的末值
            data = data[start:end]  # 返回指定数据范围
        result = {'code': code, 'msg':msg,'data': data,'count':count}
        return JsonResponse(result)
    elif request.method == 'POST':
        ns_name = request.POST.get('name')
        for ns in core_api.list_namespace().items:
            if ns_name == ns.metadata.name:
                result = {'code':1,'msg':'命名空间已经存在'}
                return JsonResponse(result)
        body = client.V1Namespace(
            api_version="v1",
            kind="Namespace",
            metadata=client.V1ObjectMeta(
                name=ns_name
            )
        )
        try:
            core_api.create_namespace(body=body)
            code = 0
            msg = '创建成功,请刷新页面'
        except Exception as e:
            code = 1
            msg = '创建失败'
        result = {'code': code, 'msg': msg}
        return JsonResponse(result)
    elif request.method == 'DELETE':
        #django对于GET和POST请求进行了封装,即可以通过request.GET/POST获取里面的值
        #对于PUT和DELETE并没有封装,所有需要自己封装,从request.body里获取
        request_data = QueryDict(request.body)
        name = request_data.get("name")
        if name == 'default':
            code = 1
            msg = '此命名空间不可删除'
            result = {'code': code, 'msg': msg}
            return JsonResponse(result)
        # 调用k8s_api删除命名空间
        try:
            core_api.delete_namespace(name=name)
            code = 0
            msg = '删除命名空间成功'
        except Exception as e:
            status = getattr(e,'status')
            if status == 403:
                msg = '没有访问命名空间权限'
            else:
                msg = '删除命名空间失败'
            code = 1
        result = {'code': code, 'msg': msg}
        return JsonResponse(result)

@k8s.self_login_required
def node_api(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()
    data = []
    search_key = request.GET.get("search_key")
    if request.method == 'GET':
        try:
            for node in core_api.list_node_with_http_info()[0].items:  # items返回一个对象，类LIST（[{命名空间属性},{命名空间属性}] ），每个元素是一个类字典（命名空间属性），操作类字典
                name = node.metadata.name
                labels = node.metadata.labels
                status1 = node.status.conditions[-1].status
                if status1 == 'True':
                    status = "Reday"
                else:
                    status = "NoRedy"
                scheduler = ("是" if node.spec.unschedulable is None else "否")
                cpu = node.status.capacity['cpu']
                memory_ki_str = node.status.capacity.get('memory', '0Ki')  # 使用 .get() 避免节点没内存信息时报错
                if memory_ki_str.endswith('Ki'):
                    memory_ki = int(memory_ki_str[:-2])  # 去掉 'Ki' 并转为整数
                    memory_gb = memory_ki / (1024 * 1024)  # 计算GB
                    memory = f"{memory_gb:.1f}G"  # 格式化为一位小数的字符串，如 "3.8G"
                else:
                    memory = memory_ki_str  # 如果单位不是Ki，直接显示原始值
                kebelet_version = node.status.node_info.kubelet_version
                cri_version = node.status.node_info.container_runtime_version
                create_time = node.metadata.creation_timestamp
                node = {"name": name, "labels": labels, "status": status,
                        "scheduler": scheduler, "cpu": cpu, "memory": memory,
                        "kebelet_version": kebelet_version, "cri_version": cri_version,
                        "create_time": create_time}
                if search_key:
                    if search_key in name:
                        data.append(node)
                else:
                    data.append(node)
            code = 0
            msg = '查询成功'
        except Exception:
            code = 1
            msg = '查询失败'
        count = len(data)  # 要在切片之前获取总数
        if request.GET.get('page'):  # 如果为真则数据表格带有分页
            page = int(request.GET.get('page'))
            limit = int(request.GET.get('limit'))
            # data = data[0:10]
            start = (page - 1) * limit  # 切片的起始值
            end = page * limit  # 切片的末值
            data = data[start:end]  # 返回指定数据范围
        result = {'code': code, 'msg': msg, 'data': data, 'count': count}
        return JsonResponse(result)
@k8s.self_login_required
def pv(request):
    return render(request, 'k8s/pv.html')
def pv_api(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()
    data = []
    search_key = request.GET.get("search_key")
    if request.method == "GET" :
        try:
            for pv in core_api.list_persistent_volume().items:
                name = pv.metadata.name
                capacity = pv.spec.capacity["storage"]
                access_modes = pv.spec.access_modes
                reclaim_policy = pv.spec.persistent_volume_reclaim_policy
                status = pv.status.phase
                if pv.spec.claim_ref is not None:
                    pvc_ns = pv.spec.claim_ref.namespace
                    pvc_name = pv.spec.claim_ref.name
                    pvc = "%s / %s" % (pvc_ns, pvc_name)
                else:
                    pvc = "未绑定"
                storage_class = pv.spec.storage_class_name
                create_time = pv.metadata.creation_timestamp
                pv = {"name": name, "capacity": capacity, "access_modes": access_modes,
                      "reclaim_policy": reclaim_policy, "status": status, "pvc": pvc,
                      "storage_class": storage_class, "create_time": create_time}
                if search_key:
                    if search_key in name:
                        data.append(pv)
                else:
                    data.append(pv)
            code = 0
            msg = '查询成功'
        except Exception:
            code = 1
            msg = '查询失败'

        count = len(data)  # 要在切片之前获取总数
        if request.GET.get('page'):     #如果为真则数据表格带有分页
            page = int(request.GET.get('page'))
            limit = int(request.GET.get('limit'))
            # data = data[0:10]
            start = (page - 1) * limit  # 切片的起始值
            end = page * limit  # 切片的末值
            data = data[start:end]  # 返回指定数据范围
        result = {'code': code, 'msg':msg,'data': data,'count':count}
        return JsonResponse(result)
    elif request.method == "POST":
        name = request.POST.get("name", None)
        capacity = request.POST.get("capacity", None)
        access_mode = request.POST.get("access_mode", None)
        storage_type = request.POST.get("storage_type", None)
        server_ip = request.POST.get("server_ip", None)
        mount_path = request.POST.get("mount_path", None)
        body = client.V1PersistentVolume(
            api_version="v1",
            kind="PersistentVolume",
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PersistentVolumeSpec(
                capacity={'storage': capacity},
                access_modes=[access_mode],
                nfs=client.V1NFSVolumeSource(
                    server=server_ip,
                    path="/ifs/kubernetes/%s" % mount_path
                )
            )
        )
        try:
            core_api.create_persistent_volume(body=body)
            code = 0
            msg  = '创建PV成功'
        except Exception:
            code = 1
            msg = '创建PV失败'
        result = {'code': code, 'msg': msg, 'data': data}
        return JsonResponse(result)
    elif request.method == "DELETE":
        request_data = QueryDict(request.body)
        name = request_data.get("name")
        try:
            core_api.delete_persistent_volume(name=name)
            code = 0
            msg = '删除命名空间成功'
        except Exception as e:
            code = 1
            status = getattr(e, 'status')
            if status == 403:
                msg = '没有访问命名空间权限'
            else:
                msg = '删除命名空间失败'
        result = {'code': code, 'msg': msg}
        return JsonResponse(result)

@k8s.self_login_required
def pv_create(request):
    return render(request, 'pv_create.html')
@k8s.self_login_required
def node_detail(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()

    node_name = request.GET.get("name")
    #根据节点名称获取对应资源,再渲染到模板里
    n_r = node_data.node_resource(core_api, node_name)
    n_i =node_data.node_info(core_api, node_name)
    print(n_i)
    print(node_name)
    return render(request, 'node_details.html', {'node': node_name, 'node_resouces': n_r, 'node_info': n_i})
def deployment_details(request):
    auth_type = request.session.get("auth_type")
    token = request.session.get("token")
    k8s.load_auth_config(auth_type, token)
    core_api = client.CoreV1Api()

    deployment_name = request.GET.get("namespace")
    print(deployment_name)
    return  render(request,'deployment_details.html',{'namespace':namespace})
from dashboard.models import *
def script(request):
    return render(request,'script.html')
def script_api(request):
    if request.method == "GET":
        data = []
        for i in Script.objects.all():
            id = i.id
            name = i.name
            content = i.content
            description = i.description
            i = {'id':id ,'name': name,  'description': description,'content':content}
            data.append(i)
        code = 0
        msg = '查询成功'
        count = len(data)  # 要在切片之前获取总数
        if request.GET.get('page'):  # 如果为真则数据表格带有分页
            page = int(request.GET.get('page'))
            limit = int(request.GET.get('limit'))
            # data = data[0:10]
            start = (page - 1) * limit  # 切片的起始值
            end = page * limit  # 切片的末值
            data = data[start:end]  # 返回指定数据范围
        result = {'code': code, 'msg': msg, 'data': data, 'count': count}
        return JsonResponse(result)

    elif request.method == "POST":
        is_run_check = request.POST.get("run") == '1'
        is_create_new = not is_run_check and "name" in request.POST
        is_execute_run = not is_run_check and "run_mode" in request.POST or "script_type" == 'YAML'

        # --- 意图 1: 检查脚本类型（当用户打开运行弹窗时）---
        if is_run_check:
            content = request.POST.get("content", "")
            is_valid, message = k8s.classify_and_validate_script(content)
            if is_valid:
                return JsonResponse({'code': 0, 'message': message})
            else:
                return JsonResponse({'code': 1, 'msg': f'脚本内容校验失败: {message}'})

        # --- 意图 2: 执行运行操作 ---
        elif is_execute_run:
            content = request.POST.get("content")
            namespace = request.POST.get("namespace")
            script_type = request.POST.get("script_type")  # 前端必须传递这个

            if not all([namespace, content, script_type]):
                return JsonResponse({'code': 1, 'msg': '缺少命名空间、脚本内容或类型，无法运行。'})

            # 加载 K8S 凭证
            try:
                auth_type = request.session.get("auth_type")
                token = request.session.get("token")
                k8s.load_auth_config(auth_type, token)
            except Exception as e:
                return JsonResponse({'code': 1, 'msg': f'加载K8s配置失败: {e}'})

            # 根据脚本类型调用不同的运行器
            if script_type == 'YAML':
                success, message = k8s.apply_yaml(namespace, content)
            elif script_type == 'Shell':
                run_mode = request.POST.get("run_mode")
                if run_mode == 'Job':
                    script_name_for_job = request.POST.get("script_name", "unnamed-script").replace("_", "-").lower()
                    success, message = k8s.run_shell_as_job(namespace, script_name_for_job, content)
                else:
                    success, message = False, "Shell 脚本仅支持以 Job 方式运行。"
            else:
                success, message = False, f"未知的脚本类型: {script_type}"

            return JsonResponse({'code': 0 if success else 1, 'msg': message})

        # --- 意图 3: 创建新脚本到数据库 ---
        elif is_create_new:
            content = request.POST.get("content")
            name = request.POST.get("name")
            description = request.POST.get("script_description")

            is_valid, message = k8s.classify_and_validate_script(content)
            if not is_valid:
                return JsonResponse({'code': 1, 'msg': f'脚本校验失败: {message}'})

            if Script.objects.filter(name=name).exists():
                return JsonResponse({'code': 1, 'msg': '脚本名称已存在。'})

            try:
                Script.objects.create(name=name, content=content, description=description)
                return JsonResponse({'code': 0, 'msg': f'脚本创建成功！格式: {message}'})
            except Exception as e:
                return JsonResponse({'code': 2, 'msg': f'数据库保存失败: {e}'})

        # 如果以上意图都未匹配
        return JsonResponse({'code': 1, 'msg': '无法识别的 POST 请求。'})
    elif request.method == "DELETE":
        request_data = QueryDict(request.body)
        id = request_data.get("id")
        Script.objects.get(id=id).delete()
        code = 0
        msg = "删除脚本成功."
        result = {'code': code, 'msg': msg}
        return JsonResponse(result)












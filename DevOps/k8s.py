#验证token或者kubeconfig是否有效
from kubernetes import client, config
import os
from dashboard.models import User
from kubernetes.client import ApiException
import yaml
from django.shortcuts import redirect
#验证tonken和kubeconfig
def auth_check(auth_type,token):
    if auth_type == 'token':        #进行
        configuration = client.Configuration()
        configuration.host = "https://192.168.37.200:6443"  # APISERVER地址
        # ca_file = os.path.join(os.getcwd(), "ca.crt")  # K8s集群CA证书（/etc/kubernetes/pki/ca.crt）
        # configuration.ssl_ca_cert = ca_file
        configuration.verify_ssl = False  # 关闭证书验证
        # token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImdlQlFUM3..."  # 指定Token字符串，下面方式获取
        configuration.api_key = {"authorization": "Bearer " + token}
        client.Configuration.set_default(configuration)
        try:
            core_api = client.CoreApi()
            core_api.get_api_versions()     #查看api的版本
            return True
        except ApiException as e:
            return False
    elif auth_type == 'kubeconfig':
        user =User.objects.get(token=token)
        content = user.content
        yaml_content = yaml.load(content,Loader=yaml.FullLoader)   #将yaml文件转换成json
        try:
            config.load_kube_config_from_dict(yaml_content)
            core_api = client.CoreApi()     #资源接口实例化
            core_api.get_api_versions()     #查看api的版本
            return True
        except ApiException as e:
            return False


#登录认证装饰器
def self_login_required(func):
    def inner(request):
        is_login = request.session.get('is_login')
        if is_login :
            return func(request)
        else:
            return redirect('/login')
    return inner
#命名空间
def load_auth_config(auth_type,token):
    if auth_type == 'token':
        configuration = client.Configuration()
        configuration.host = "https://192.168.37.200:6443"  # APISERVER地址
        configuration.verify_ssl = False  # 关闭证书验证
        configuration.api_key = {"authorization": "Bearer " + token}
        client.Configuration.set_default(configuration)
    elif auth_type == 'kubeconfig':
        user = User.objects.get(token=token)
        content = user.content
        yaml_content = yaml.load(content, Loader=yaml.FullLoader)
        config.load_kube_config_from_dict(yaml_content)
#资源创建时间
from datetime import date,timedelta
def timestamp_format(timestamp):
    c = timestamp + timedelta(hours=8)
    t = date.strftime(c,'%Y-%m-%d %H:%M:%S')
    return t
#自动化脚本检验格式
import yaml

def classify_and_validate_script(content: str):
    """
    校验脚本内容的格式。
    :param content: 脚本内容的字符串
    :return: (is_valid, message) 元组
    """
    if not isinstance(content, str) or not content.strip():
        return (False, "脚本内容不能为空！")

    # --- 1. 尝试作为 YAML 解析 ---
    try:
        # safe_load 可以解析 YAML
        data = yaml.safe_load(content)
        # 增加一个严格判断：我们期望的 YAML 是一个结构（字典或列表），
        # 而不是一个普通的字符串，比如 "hello world" 也会被 yaml 解析为字符串 "hello world"
        if isinstance(data, (dict, list)):
            return (True, "YAML")
    except yaml.YAMLError:
        # 如果解析 YAML 出错，说明它肯定不是一个合法的 YAML，进入下一步判断
        pass

    # --- 2. 尝试判断是否为 Shell 脚本 ---
    # 最可靠的标志是 shebang
    if content.strip().startswith('#!/'):
        return (True, "Shell")

    # --- 3. 如果都不是，则格式不正确 ---
    error_message = "格式无法识别。请确保内容是有效的YAML结构，或是以 `#!/bin/sh` 或 `#!/bin/bash` 等开头的Shell脚本。"
    return (False, error_message)

def apply_yaml(namespace, yaml_content):
    """
    动态解析 YAML 内容, 根据 'kind' 来创建相应的 K8s 资源。
    Mimics `kubectl apply`.
    """
    # 获取不同 API 组的客户端
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    batch_v1 = client.BatchV1Api()
    # ... 根据需要可以添加更多, 如 rbac_v1, networking_v1 等

    try:
        # 1. 使用 pyyaml 解析 YAML 内容
        body = yaml.safe_load(yaml_content)         #解析yaml内容为字典
        print(body)
        kind = body.get("kind")

        if not kind:
            return False, "YAML 文件中缺少 'kind' 字段。"

        # 2. 根据 'kind' 路由到正确的创建函数
        #    这是核心逻辑
        if kind == "Deployment":
            apps_v1.create_namespaced_deployment(namespace=namespace, body=body)
        elif kind == "ConfigMap":
            core_v1.create_namespaced_config_map(namespace=namespace, body=body)
        elif kind == "Job":
            batch_v1.create_namespaced_job(namespace=namespace, body=body)
        elif kind == "Pod":
            core_v1.create_namespaced_pod(namespace=namespace, body=body)
        else:
            return False, f"不支持的资源类型 (kind): '{kind}'"

        resource_name = body.get("metadata", {}).get("name", "未知")
        return True, f"资源 '{resource_name}' (类型: {kind}) 在命名空间 '{namespace}' 中创建成功。"

    except ApiException as e:
        if e.status == 409: # 资源已存在
            return False, f"创建失败：资源已存在。"
        return False, f"Kubernetes API 错误: {e.reason}"
    except yaml.YAMLError as e:
        return False, f"YAML 格式错误: {e}"
    except Exception as e:
        # 捕获其他可能的错误, 如 'kind' 不存在等
        return False, f"处理 YAML 时发生未知错误: {str(e)}"
def run_shell_as_job(namespace, script_name, shell_content):
    """
    将 Shell 脚本包装在 ConfigMap 中，并创建一个 Job 来运行它。
    """
    import  uuid
    # 为本次运行生成唯一的后缀，避免资源命名冲突
    unique_suffix = uuid.uuid4().hex[:6]
    cm_name = f"{script_name}-shell-cm-{unique_suffix}"
    job_name = f"{script_name}-job-{unique_suffix}"
    script_filename = "run.sh"
    core_v1 = client.CoreV1Api()
    batch_v1 = client.BatchV1Api()

    # --- 步骤 1: 创建用于存放 Shell 脚本的 ConfigMap ---
    cm_body = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name=cm_name, namespace=namespace),
        data={script_filename: shell_content}
    )

    try:
        core_v1.create_namespaced_config_map(namespace=namespace, body=cm_body)
    except ApiException as e:
        return False, f"为 Job 创建临时 ConfigMap 失败: {e.reason}"

    # --- 步骤 2: 创建 Job 来挂载并执行 ConfigMap 中的脚本 ---
    container = client.V1Container(
        name="script-runner",
        image="busybox",  # 使用一个包含 shell 的轻量级镜像
        command=["/bin/sh", "-c", f"/scripts/{script_filename}"],
        volume_mounts=[client.V1VolumeMount(
            name="script-volume",
            mount_path="/scripts"
        )]
    )

    volume = client.V1Volume(
        name="script-volume",
        config_map=client.V1ConfigMapVolumeSource(
            name=cm_name,
            # 关键：设置文件权限为可执行 (0755)
            default_mode=0o755
        )
    )

    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "shell-runner"}),
        spec=client.V1PodSpec(
            restart_policy="Never",  # Job 的 Pod 失败后不自动重启
            containers=[container],
            volumes=[volume]
        )
    )

    job_spec = client.V1JobSpec(
        template=pod_template,
        backoff_limit=2, # 失败后重试次数
        ttl_seconds_after_finished=300 # Job 结束后 300 秒自动清理
    )

    job_body = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name, namespace=namespace),
        spec=job_spec
    )

    try:
        batch_v1.create_namespaced_job(namespace=namespace, body=job_body)
        return True, f"Job '{job_name}' 已成功启动，开始执行 Shell 脚本。"
    except ApiException as e:
        return False, f"创建 Job 失败: {e.reason}"



## 项目简介


此项目是一个基于python开发的Kubernetes后台管理平台

>  本项目使用python开发，使用django+Layui开发
## 内置功能
1.集群资源的增删改查

2.prometheus数据展示

3.容器日志实时查看

4.交互式容器终端
## 准备工作
```bash
  channels==4.3.2
  Django==6.0.1
  kubernetes==35.0.0
  PyMySQL==1.1.2
```
## 前端 
```bash
# 安装依赖
pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
# 安装与配置uwsgi
pip3 install uwsgi -i https://mirrors.aliyun.com/pypi/simple
mkdir /root/DevOps/uwsgi/
vim /root/DevOps/uwsgi/uwsgi.ini
[uwsgi]
# vi /opt/devops/uwsgi/uwsgi.ini 
# 1. 项目与环境
# ========================
# 项目目录
chdir           = /root/DevOps/
# Django 的 wsgi 入口
module          = DevOps.wsgi:application
# 虚拟环境的路径
virtualenv      = /root/DevOps/venv/

# 2. 运行模式 
# ========================
# 注释掉 socket 模式，因为它需要 Nginx 配合
# socket          = /root/DevOps/uwsgi/uwsgi.sock
# 启用 http 模式，让浏览器可以直接访问
http            = 0.0.0.0:8080

# 3. 进程与日志
# ========================
# 进程个数
processes       = 4 
# 进程pid文件
pidfile         = /root/DevOps/uwsgi/uwsgi.pid
# 以守护进程模式运行，并记录日志
daemonize       = /root/DevOps/uwsgi/uwsgi.log

vi /usr/lib/systemd/system/uwsgi.service 
[Unit]
Description=HTTP Interface Server

[Service]
Type=forking
ExecStart=/root/DevOps/venv/bin/uwsgi --ini /root/DevOps/uwsgi/uwsgi.ini
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target


systemctl daemon-reload
systemctl start uwsgi
systemctl enable uwsgi

# 4. 静态文件 
# ========================
# uwsgi 
static-map      = /static=/root/DevOps/static
```
## 后端 
```bash
#/root/DevOps/DevOps/settings.py修改本地数据库
  DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'devops',
        'USER': 'devops',
        'PASSWORD': '123456',
        'HOST': '127.0.0.1',  
        'PORT': '3306',
    }
}
导入数据表
mysql -u 用户名 -p 数据库名 < devops.sql
```
##反向代理
```
yum install epel-release –y
yum install nginx –y
vi /etc/nginx/nginx.conf
…
    server {
        listen       80 default_server;
        server_name  _;

        location / {
           include     uwsgi_params;  # 导入模块用于与uwsgi通信
           uwsgi_pass unix:/opt/devops/uwsgi/uwsgi.sock; 
        }
        # 静态文件目录
        location /static {
           alias /opt/devops/static;
        }
}
```
##项目访问
http://127.0.0.1:8080/

<img width="1858" height="854" alt="image" src="https://github.com/user-attachments/assets/94d4efce-de61-4ac1-b7ae-f2f1604e2549" />
<img width="1876" height="826" alt="image" src="https://github.com/user-attachments/assets/1a009812-b705-4441-8b76-1004728df765" />
<img width="1863" height="872" alt="image" src="https://github.com/user-attachments/assets/1e2d27ba-dfad-48e9-b8ea-97fb9b286996" />
<img width="1838" height="827" alt="image" src="https://github.com/user-attachments/assets/f8f83b8b-4d23-465d-9667-c00d85b3147e" />
<img width="1678" height="756" alt="image" src="https://github.com/user-attachments/assets/6c7d19a2-abf1-4e6c-b46a-fc1f10125a26" />

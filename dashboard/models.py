from django.db import models

# Create your models here.


class User(models.Model):       #创建数据库用于存储登录信息
    auth_type = models.CharField(max_length = 30)
    token = models.CharField(max_length = 100)
    content = models.TextField()
    datetime = models.DateTimeField(auto_now=True)
class Script(models.Model):
    name = models.CharField(max_length=100, verbose_name="脚本名称")
    content = models.TextField(verbose_name="脚本内容")
    description = models.TextField(blank=True, null=True, verbose_name="脚本描述")
    class Meta:
        db_table = 'script'
    def __str__(self):
        return self.name

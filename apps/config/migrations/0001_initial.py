"""Initial migration for Config app"""
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='配置项的唯一标识', max_length=255, unique=True, verbose_name='配置键')),
                ('value', models.TextField(help_text='配置项的具体值', verbose_name='配置值')),
                ('description', models.CharField(blank=True, default='', help_text='配置项的简要说明', max_length=500, verbose_name='配置描述')),
                ('value_type', models.CharField(choices=[('string', '字符串'), ('integer', '整数'), ('float', '浮点数'), ('boolean', '布尔值'), ('json', 'JSON')], default='string', help_text='配置值的数据类型', max_length=50, verbose_name='值类型')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '系统配置',
                'verbose_name_plural': '系统配置',
                'db_table': 'config_config',
                'ordering': ['key'],
            },
        ),
    ]

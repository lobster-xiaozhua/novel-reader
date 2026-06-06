"""Config Admin - manage system settings via Django admin interface"""
from django.contrib import admin
from django import forms
from .models import Config, ConfigManager


class ConfigForm(forms.ModelForm):
    """配置管理表单，提供更好的编辑体验"""

    class Meta:
        model = Config
        fields = ['key', 'value', 'value_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 为不同类型提供更好的编辑控件
        if self.instance and self.instance.pk:
            if self.instance.value_type == 'json':
                self.fields['value'].widget = forms.Textarea(attrs={'rows': 8, 'class': 'vLargeTextField'})
            elif self.instance.value_type == 'boolean':
                # 对于布尔值，使用 checkbox 显示当前值（但实际还是存储字符串）
                self.fields['value'].help_text = '请输入 true/false, yes/no, 1/0 等'


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    """配置管理界面"""
    list_display = ['key', 'short_value', 'value_type', 'description', 'updated_at']
    list_filter = ['value_type', 'created_at', 'updated_at']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['key']
    form = ConfigForm
    actions = ['initialize_defaults']

    def short_value(self, obj):
        """显示截断的配置值"""
        value = str(obj.value)
        if len(value) > 50:
            return f'{value[:47]}...'
        return value
    short_value.short_description = '配置值'

    @admin.action(description='初始化默认配置')
    def initialize_defaults(self, request, queryset):
        """初始化默认配置操作"""
        count = ConfigManager.initialize_defaults()
        self.message_user(request, f'成功初始化 {count} 个默认配置')


# 提供一个便捷的初始化函数，用于应用启动时自动初始化
def auto_initialize_configs():
    """自动初始化默认配置（可以在 AppConfig.ready 中调用）"""
    try:
        ConfigManager.initialize_defaults()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Failed to auto-initialize configs: {e}')

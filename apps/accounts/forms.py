from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={"class": "input", "placeholder": "请输入用户名"})
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input", "placeholder": "请输入密码"}))


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=False, widget=forms.EmailInput(attrs={"class": "input", "placeholder": "邮箱（可选）"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "input", "placeholder": "用户名"})
        self.fields["password1"].widget.attrs.update({"class": "input", "placeholder": "密码"})
        self.fields["password2"].widget.attrs.update({"class": "input", "placeholder": "确认密码"})

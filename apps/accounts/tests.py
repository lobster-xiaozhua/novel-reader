from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class AccountsViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_login_view_get(self):
        """测试登录页面GET请求"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_view_post_valid(self):
        """测试有效凭据登录"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_view_post_invalid(self):
        """测试无效凭据登录失败"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)

    def test_login_view_redirect_when_authenticated(self):
        """测试已登录用户访问登录页重定向"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('home'))

    def test_login_view_with_next_param(self):
        """测试登录后重定向到next参数指定页面"""
        response = self.client.post(
            reverse('login') + '?next=/books/',
            {'username': 'testuser', 'password': 'testpass123'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/books/')

    def test_login_view_with_invalid_next(self):
        """测试登录后无效next参数的安全处理"""
        response = self.client.post(
            reverse('login') + '?next=http://evil.com',
            {'username': 'testuser', 'password': 'testpass123'}
        )
        self.assertRedirects(response, reverse('home'))

    def test_register_view_get(self):
        """测试注册页面GET请求"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_register_view_post_valid(self):
        """测试有效数据注册"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'email': 'new@example.com'
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_view_post_invalid_password_mismatch(self):
        """测试密码不匹配注册失败"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'pass123',
            'password2': 'pass456'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_register_view_redirect_when_authenticated(self):
        """测试已登录用户访问注册页重定向"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('home'))

    def test_logout_view(self):
        """测试登出功能"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_logout_view_requires_post(self):
        """测试登出只接受POST请求"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)


class LoginFormTest(TestCase):
    def test_login_form_valid(self):
        """测试登录表单验证"""
        from .forms import LoginForm
        form = LoginForm(data={'username': 'testuser', 'password': 'testpass'})
        self.assertTrue(form.is_valid())

    def test_login_form_empty(self):
        """测试空登录表单"""
        from .forms import LoginForm
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())


class RegisterFormTest(TestCase):
    def test_register_form_valid(self):
        """测试注册表单验证"""
        from .forms import RegisterForm
        form = RegisterForm(data={
            'username': 'newuser',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'email': 'test@example.com'
        })
        self.assertTrue(form.is_valid())

    def test_register_form_weak_password(self):
        """测试弱密码注册表单"""
        from .forms import RegisterForm
        form = RegisterForm(data={
            'username': 'newuser',
            'password1': '123',
            'password2': '123'
        })
        self.assertFalse(form.is_valid())

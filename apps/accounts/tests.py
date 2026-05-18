from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import django.test.client


# Monkey patch store_rendered_templates to be a no-op to prevent copy errors
def no_op_store_rendered_templates(*args, **kwargs):
    pass


django.test.client.store_rendered_templates = no_op_store_rendered_templates


class AccountsViewsTest(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_view_post_valid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_view_post_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_register_view_post_valid(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

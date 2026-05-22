from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


@require_POST
def login_view(request):
    username = request.POST.get('username') or request.json().get('username')
    password = request.POST.get('password') or request.json().get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
            }
        })
    return JsonResponse({'success': False, 'error': '用户名或密码错误'}, status=401)


@require_POST
def register_view(request):
    from django.contrib.auth.models import User
    username = request.POST.get('username') or request.json().get('username')
    password = request.POST.get('password') or request.json().get('password')
    email = request.POST.get('email') or request.json().get('email', '')

    if not username or not password:
        return JsonResponse({'success': False, 'error': '用户名和密码不能为空'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'success': False, 'error': '用户名已存在'}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    login(request, user)
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
        }
    })


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'success': True})

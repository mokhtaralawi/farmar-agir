"""
Accounts Views - Login, Logout, Profile, and User Management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Role


def login_view(request):
    if request.user.is_authenticated:
        return redirect('reports:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('reports:dashboard')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
    
    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_username':
            new_username = request.POST.get('username', '').strip()
            if not new_username:
                messages.error(request, 'يرجى إدخال اسم مستخدم')
            elif new_username == request.user.username:
                messages.warning(request, 'هذا اسم المستخدم الحالي')
            elif User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                messages.error(request, 'اسم المستخدم موجود مسبقاً')
            else:
                request.user.username = new_username
                request.user.save()
                messages.success(request, 'تم تغيير اسم المستخدم بنجاح')
        elif action == 'change_password':
            current = request.POST.get('current_password', '')
            new_pass = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')
            if not request.user.check_password(current):
                messages.error(request, 'كلمة المرور الحالية غير صحيحة')
            elif len(new_pass) < 8:
                messages.error(request, 'كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل')
            elif new_pass != confirm:
                messages.error(request, 'كلمة المرور الجديدة وتأكيدها غير متطابقين')
            else:
                request.user.set_password(new_pass)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'تم تغيير كلمة المرور بنجاح')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html')


@login_required
def users_list(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول إلى هذه الصفحة')
        return redirect('reports:dashboard')
    users = User.objects.all().order_by('-created_at')
    return render(request, 'accounts/users_list.html', {'users': users})


@login_required
def user_create(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول إلى هذه الصفحة')
        return redirect('reports:dashboard')
    roles = Role.objects.filter(is_active=True)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '')
        password = request.POST.get('password', '')
        role_ids = request.POST.getlist('roles')

        if not username:
            messages.error(request, 'اسم المستخدم مطلوب')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'اسم المستخدم موجود مسبقاً')
        elif len(password) < 8:
            messages.error(request, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل')
        else:
            user = User.objects.create(
                username=username,
                full_name=full_name or username,
                phone=phone,
                is_staff=True,
            )
            user.set_password(password)
            if role_ids:
                user.roles.set(role_ids)
            user.save()
            messages.success(request, f'تم إنشاء المستخدم {username} بنجاح')
            return redirect('accounts:users_list')
    return render(request, 'accounts/user_form.html', {'roles': roles, 'mode': 'create', 'user_role_ids': []})


@login_required
def user_edit(request, pk):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية الوصول إلى هذه الصفحة')
        return redirect('reports:dashboard')
    user = get_object_or_404(User, id=pk)
    if user.is_superuser and user.id != request.user.id:
        messages.error(request, 'لا يمكن تعديل المستخدم المدير العام')
        return redirect('accounts:users_list')
    roles = Role.objects.filter(is_active=True)
    if request.method == 'POST':
        user.full_name = request.POST.get('full_name', '').strip() or user.username
        user.phone = request.POST.get('phone', '')
        user.is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password', '')
        role_ids = request.POST.getlist('roles')
        user.roles.set(role_ids)
        if password:
            if len(password) < 8:
                messages.error(request, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل')
                return render(request, 'accounts/user_form.html', {'u': user, 'roles': roles, 'mode': 'edit', 'user_role_ids': list(user.roles.values_list('id', flat=True))})
            user.set_password(password)
        user.save()
        messages.success(request, 'تم تحديث المستخدم بنجاح')
        return redirect('accounts:users_list')
    return render(request, 'accounts/user_form.html', {'u': user, 'roles': roles, 'mode': 'edit', 'user_role_ids': list(user.roles.values_list('id', flat=True))})


@login_required
def user_toggle_active(request, pk):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('reports:dashboard')
    user = get_object_or_404(User, id=pk)
    if user.is_superuser and user.id != request.user.id:
        messages.error(request, 'لا يمكن تعطيل المستخدم المدير العام')
    else:
        user.is_active = not user.is_active
        user.save()
        status = 'تفعيل' if user.is_active else 'تعطيل'
        messages.success(request, f'تم {status} المستخدم بنجاح')
    return redirect('accounts:users_list')

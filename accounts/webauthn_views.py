"""
WebAuthn Views - Biometric authentication (fingerprint/face)
"""

import json
import base64
import hashlib
import os

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import User

# In-memory challenge store (in production use cache or DB)
from django.core.cache import cache


def _base64url_encode(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _base64url_decode(data):
    return base64.urlsafe_b64decode(data + '===')


def _get_origin():
    return settings.CSRF_TRUSTED_ORIGINS[0] if settings.CSRF_TRUSTED_ORIGINS else 'http://localhost:8000'


def _get_rp_id():
    from urllib.parse import urlparse
    origin = _get_origin()
    return urlparse(origin).hostname or 'localhost'


@login_required
def begin_registration(request):
    """Start WebAuthn credential registration"""
    challenge = os.urandom(32)
    challenge_b64 = _base64url_encode(challenge)
    cache.set(f'webauthn_challenge_{request.user.id}', challenge_b64, timeout=120)

    user_id_b64 = _base64url_encode(str(request.user.id))
    user_name = request.user.username
    user_display = request.user.full_name or request.user.username

    rp_id = _get_rp_id()
    origin = _get_origin()

    creation_options = {
        'challenge': challenge_b64,
        'rp': {'name': 'نظام المجابرة', 'id': rp_id},
        'user': {'id': user_id_b64, 'name': user_name, 'displayName': user_display},
        'pubKeyCredParams': [{'alg': -7, 'type': 'public-key'}],
        'timeout': 60000,
        'attestation': 'none',
    }

    return JsonResponse(creation_options)


@login_required
@require_POST
@csrf_exempt
def finish_registration(request):
    """Finish WebAuthn registration"""
    try:
        body = json.loads(request.body)
        stored_challenge = cache.get(f'webauthn_challenge_{request.user.id}')
        if not stored_challenge:
            return JsonResponse({'error': 'انتهت صلاحية الطلب. حاول مرة أخرى.'}, status=400)

        credential_id = body.get('id')
        raw_id = body.get('rawId')

        response_data = body.get('response', {})
        client_data_json_b64 = response_data.get('clientDataJSON')
        attestation_object_b64 = response_data.get('attestationObject')

        if not all([credential_id, client_data_json_b64, attestation_object_b64]):
            return JsonResponse({'error': 'بيانات غير كاملة'}, status=400)

        # Decode and verify client data JSON
        client_data = json.loads(_base64url_decode(client_data_json_b64))
        if client_data.get('type') != 'webauthn.create':
            return JsonResponse({'error': 'نوع الطلب غير صحيح'}, status=400)

        # Store credential data
        user = request.user
        user.webauthn_credential_id = credential_id
        user.webauthn_public_key = attestation_object_b64
        user.webauthn_enabled = True
        user.save()

        cache.delete(f'webauthn_challenge_{request.user.id}')

        return JsonResponse({'success': True, 'message': 'تم ربط البصمة بنجاح'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def begin_login(request):
    """Start WebAuthn login (no auth required)"""
    try:
        body = json.loads(request.body)
        username = body.get('username', '').strip()

        if not username:
            return JsonResponse({'error': 'اسم المستخدم مطلوب'}, status=400)

        try:
            user = User.objects.get(username=username, webauthn_enabled=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'المستخدم غير موجود أو البصمة غير مفعلة'}, status=404)

        if not user.webauthn_credential_id:
            return JsonResponse({'error': 'لا توجد بصمة مسجلة'}, status=400)

        challenge = os.urandom(32)
        challenge_b64 = _base64url_encode(challenge)
        cache.set(f'webauthn_challenge_login_{user.id}', challenge_b64, timeout=120)

        rp_id = _get_rp_id()

        get_options = {
            'challenge': challenge_b64,
            'rpId': rp_id,
            'allowCredentials': [{'id': user.webauthn_credential_id, 'type': 'public-key'}],
            'timeout': 60000,
            'userVerification': 'preferred',
        }

        return JsonResponse(get_options)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def finish_login(request):
    """Finish WebAuthn login (no auth required)"""
    try:
        body = json.loads(request.body)
        username = body.get('username', '').strip()

        if not username:
            return JsonResponse({'error': 'اسم المستخدم مطلوب'}, status=400)

        try:
            user = User.objects.get(username=username, webauthn_enabled=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'المستخدم غير موجود'}, status=404)

        stored_challenge = cache.get(f'webauthn_challenge_login_{user.id}')
        if not stored_challenge:
            return JsonResponse({'error': 'انتهت صلاحية الطلب. حاول مرة أخرى.'}, status=400)

        response_data = body.get('response', {})
        client_data_json_b64 = response_data.get('clientDataJSON')

        if not client_data_json_b64:
            return JsonResponse({'error': 'بيانات غير كاملة'}, status=400)

        # Verify the client data
        client_data = json.loads(_base64url_decode(client_data_json_b64))
        if client_data.get('type') != 'webauthn.get':
            return JsonResponse({'error': 'نوع الطلب غير صحيح'}, status=400)

        cache.delete(f'webauthn_challenge_login_{user.id}')

        # Login the user
        authenticate(request=request, username=user.username)
        login(request, user)

        # Keep session if they asked for it
        if not body.get('remember_me'):
            request.session.set_expiry(0)

        return JsonResponse({'success': True, 'redirect': '/'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
@csrf_exempt
def disable_webauthn(request):
    """Disable WebAuthn for the current user"""
    user = request.user
    user.webauthn_credential_id = None
    user.webauthn_public_key = None
    user.webauthn_enabled = False
    user.save()
    return JsonResponse({'success': True, 'message': 'تم تعطيل البصمة'})


@login_required
def status(request):
    """Check if WebAuthn is available"""
    return JsonResponse({
        'enabled': request.user.webauthn_enabled,
        'has_credential': bool(request.user.webauthn_credential_id),
        'browser_supported': True,
    })

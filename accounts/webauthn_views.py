"""
WebAuthn Views - Biometric authentication (fingerprint/face)
"""

import json
import base64
import hashlib
import struct
import os
import time

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.signing import Signer, BadSignature

from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA, EllipticCurvePublicNumbers, SECP256R1
)
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives import hashes

import cbor2

from .models import User

_signer = Signer('webauthn')


def _base64url_encode(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _base64url_decode(data):
    return base64.urlsafe_b64decode(data + '===')


def _get_origin(request):
    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    return f'{scheme}://{host}'


def _get_rp_id(request):
    return request.get_host().split(':')[0]


def _extract_cose_public_key(attestation_object_bytes):
    att_obj = cbor2.loads(attestation_object_bytes)
    auth_data = att_obj['authData']

    flags = auth_data[32]

    if not (flags & 0x40):
        return None

    attested_data = auth_data[37:]
    cred_id_len = struct.unpack('>H', attested_data[16:18])[0]
    cred_id = attested_data[18:18 + cred_id_len]
    cose_key = cbor2.loads(attested_data[18 + cred_id_len:])

    kty = cose_key.get(1)
    alg = cose_key.get(3)
    crv = cose_key.get(-1)

    key_data = {
        'kty': kty,
        'alg': alg,
        'crv': crv,
    }

    if kty == 2:
        x = cose_key.get(-2)
        y = cose_key.get(-3)
        if x and y:
            key_data['x'] = _base64url_encode(x)
            key_data['y'] = _base64url_encode(y)
    elif kty == 3:
        x = cose_key.get(-2)
        if x:
            key_data['x'] = _base64url_encode(x)

    return {
        'credential_id': _base64url_encode(cred_id),
        'public_key': key_data,
        'sign_count': struct.unpack('>I', auth_data[33:37])[0],
    }


def _get_public_key_object(key_data):
    kty = key_data['kty']
    x = _base64url_decode(key_data['x'])

    if kty == 2:
        y = _base64url_decode(key_data['y'])
        crv = key_data.get('crv', -7)
        if crv == -7:
            curve = SECP256R1()
            public_numbers = EllipticCurvePublicNumbers(
                x=int.from_bytes(x, 'big'),
                y=int.from_bytes(y, 'big'),
                curve=curve,
            )
            return public_numbers.public_key()

    raise ValueError(f'Unsupported key type: kty={kty}')


def _verify_signature(public_key, client_data_bytes, auth_data_bytes, signature_bytes):
    client_data_hash = hashlib.sha256(client_data_bytes).digest()
    signed_data = auth_data_bytes + client_data_hash

    alg = public_key.curve.name
    if alg == 'secp256r1':
        public_key.verify(signature_bytes, signed_data, ECDSA(Prehashed(hashes.SHA256())))
    else:
        raise ValueError(f'Unsupported algorithm: {alg}')


# ────────────────────────── Registration ──────────────────────────

@login_required
def begin_registration(request):
    """Start WebAuthn credential registration"""
    challenge = os.urandom(32)
    challenge_b64 = _base64url_encode(challenge)
    request.session['webauthn_reg_challenge'] = challenge_b64

    user_id_b64 = _base64url_encode(str(request.user.id))
    user_name = request.user.username
    user_display = request.user.full_name or request.user.username

    rp_id = _get_rp_id(request)

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
    """Finish WebAuthn registration - verify and store credential"""
    try:
        body = json.loads(request.body)
        stored_challenge = request.session.get('webauthn_reg_challenge')
        if not stored_challenge:
            return JsonResponse({'error': 'انتهت صلاحية الطلب. حاول مرة أخرى.'}, status=400)

        credential_id = body.get('id')
        response_data = body.get('response', {})
        client_data_json_b64 = response_data.get('clientDataJSON')
        attestation_object_b64 = response_data.get('attestationObject')

        if not all([credential_id, client_data_json_b64, attestation_object_b64]):
            return JsonResponse({'error': 'بيانات غير كاملة'}, status=400)

        client_data_bytes = _base64url_decode(client_data_json_b64)
        client_data = json.loads(client_data_bytes)

        if client_data.get('type') != 'webauthn.create':
            return JsonResponse({'error': 'نوع الطلب غير صحيح'}, status=400)

        if client_data.get('challenge') != stored_challenge:
            return JsonResponse({'error': 'التحدي غير مطابق'}, status=400)

        expected_origin = _get_origin(request)
        if client_data.get('origin') != expected_origin:
            return JsonResponse({'error': 'المنشأ غير صحيح'}, status=400)

        attestation_object_bytes = _base64url_decode(attestation_object_b64)
        key_info = _extract_cose_public_key(attestation_object_bytes)
        if not key_info:
            return JsonResponse({'error': 'لم يتم العثور على بيانات المفتاح'}, status=400)

        user = request.user
        user.webauthn_credential_id = key_info['credential_id']
        user.webauthn_public_key = json.dumps(key_info['public_key'])
        user.webauthn_enabled = True
        user.save()

        request.session.pop('webauthn_reg_challenge', None)

        return JsonResponse({'success': True, 'message': 'تم ربط البصمة بنجاح'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ────────────────────────── Login ──────────────────────────

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

        rp_id = _get_rp_id(request)

        get_options = {
            'challenge': challenge_b64,
            'rpId': rp_id,
            'allowCredentials': [{'id': user.webauthn_credential_id, 'type': 'public-key'}],
            'timeout': 60000,
            'userVerification': 'preferred',
        }

        response = JsonResponse(get_options)

        # Store challenge in a signed cookie (login has no session yet)
        signed_value = _signer.sign(f'{user.id}:{challenge_b64}:{int(time.time())}')
        response.set_cookie('wln_ch', signed_value, max_age=120, httponly=False, samesite='Strict')
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def finish_login(request):
    """Finish WebAuthn login - verify signature and authenticate"""
    try:
        body = json.loads(request.body)
        username = body.get('username', '').strip()

        if not username:
            return JsonResponse({'error': 'اسم المستخدم مطلوب'}, status=400)

        try:
            user = User.objects.get(username=username, webauthn_enabled=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'المستخدم غير موجود'}, status=404)

        # Retrieve challenge from signed cookie
        signed_cookie = request.COOKIES.get('wln_ch')
        if not signed_cookie:
            return JsonResponse({'error': 'انتهت صلاحية الطلب. حاول مرة أخرى.'}, status=400)

        try:
            unsigned = _signer.unsign(signed_cookie)
        except BadSignature:
            return JsonResponse({'error': 'الطلب غير صالح.'}, status=400)

        # unsigned format: user_id:challenge_b64:timestamp
        parts = unsigned.split(':')
        stored_challenge = parts[1]

        response_data = body.get('response', {})
        client_data_json_b64 = response_data.get('clientDataJSON')
        authenticator_data_b64 = response_data.get('authenticatorData')
        signature_b64 = response_data.get('signature')

        if not all([client_data_json_b64, authenticator_data_b64, signature_b64]):
            return JsonResponse({'error': 'بيانات غير كاملة'}, status=400)

        client_data_bytes = _base64url_decode(client_data_json_b64)
        client_data = json.loads(client_data_bytes)

        if client_data.get('type') != 'webauthn.get':
            return JsonResponse({'error': 'نوع الطلب غير صحيح'}, status=400)

        if client_data.get('challenge') != stored_challenge:
            return JsonResponse({'error': 'التحدي غير مطابق'}, status=400)

        expected_origin = _get_origin(request)
        if client_data.get('origin') != expected_origin:
            return JsonResponse({'error': 'المنشأ غير صحيح'}, status=400)

        auth_data_bytes = _base64url_decode(authenticator_data_b64)

        rp_id_hash = hashlib.sha256(_get_rp_id(request).encode()).digest()
        if auth_data_bytes[:32] != rp_id_hash:
            return JsonResponse({'error': 'معرف المورد غير مطابق'}, status=400)

        flags = auth_data_bytes[32]
        if not (flags & 0x01):
            return JsonResponse({'error': 'لم يتم التحقق من الحضور'}, status=400)

        if not user.webauthn_public_key:
            return JsonResponse({'error': 'لا يوجد مفتاح مسجل'}, status=400)

        key_data = json.loads(user.webauthn_public_key)
        public_key = _get_public_key_object(key_data)

        signature_bytes = _base64url_decode(signature_b64)
        try:
            _verify_signature(public_key, client_data_bytes, auth_data_bytes, signature_bytes)
        except Exception:
            return JsonResponse({'error': 'التوقيع غير صحيح'}, status=400)

        # Login the user
        login(request, user)

        if not body.get('remember_me'):
            request.session.set_expiry(0)

        response = JsonResponse({'success': True, 'redirect': '/'})
        response.delete_cookie('wln_ch')
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ────────────────────────── Status / Disable ──────────────────────────

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

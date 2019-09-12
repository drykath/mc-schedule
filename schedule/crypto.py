import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, b64_decode, dumps, loads

TOKEN_SALT_PREFIX = getattr(settings, 'SCHEDULE_TOKEN_SALT_PREFIX', 'mcfc_schedule_')

def create_token(user):
    """
    Create a signed token from a user object. Return an empty string if
    the current user isn't actually an authenticated user.
    """

    if user.is_authenticated:
        salt = TOKEN_SALT_PREFIX + user.password
        return dumps(user.username, salt=salt)
    else:
        return ''

def parse_token(token):
    """
    Pull apart a signed token and try to obtain a user. Returns the user
    object if it is a Valid, Existing, Signature-Verified token.
    Otherwise returns None.
    """
    try:
        username = json.loads(b64_decode(token.split(':')[0].encode()).decode())
    # Quite a few things could go wrong here; catch all at once for now
    except:
        return

    UserModel = get_user_model()

    try:
        user = UserModel.objects.get(username=username)
    except UserModel.DoesNotExist:
        return

    # Double check the signature is valid given the salt based on the
    # user's password hash.
    salt = TOKEN_SALT_PREFIX + user.password
    try:
        username = loads(token, salt=salt)
    except SignatureExpired:
        return
    except BadSignature:
        return

    # Should be good if we got this far, but...
    if user.username == username:
        return user
    else:
        return

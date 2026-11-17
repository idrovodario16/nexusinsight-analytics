"""Service credentials scoped to one organization and explicit capabilities."""
import hashlib
import json
import secrets
from uuid import UUID


class AccessDenied(Exception):
    def __init__(self, status):
        self.status = status


class IntegrationAccess:
    def __init__(self, env):
        if 'INTEGRATION_CREDENTIALS' in env:
            try:
                credentials = json.loads(env['INTEGRATION_CREDENTIALS'])
                if not isinstance(credentials, list) or not credentials:
                    raise ValueError()
                for item in credentials:
                    if not isinstance(item, dict) or set(item) != {'key_sha256', 'organization_id', 'permissions'}:
                        raise ValueError()
                    digest = item['key_sha256']
                    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                        raise ValueError()
                    if str(UUID(item['organization_id'])) != item['organization_id']:
                        raise ValueError()
                    permissions = item['permissions']
                    if not isinstance(permissions, list) or not permissions or any(p not in ('read', 'write') for p in permissions):
                        raise ValueError()
                if len({c['key_sha256'] for c in credentials}) != len(credentials):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise RuntimeError('Invalid INTEGRATION_CREDENTIALS configuration') from None
        else:
            key = env.get('API_KEY', '')
            if len(key) < 32:
                raise RuntimeError('API_KEY must contain at least 32 characters')
            credentials = [dict(key_sha256=hashlib.sha256(key.encode()).hexdigest(),
                                organization_id=str(UUID(env['ORGANIZATION_ID'])), permissions=['read', 'write'])]
        self.credentials = credentials

    def authorize(self, authorization, organization, permission):
        if not authorization.startswith('Bearer ') or len(authorization) > 4096 or len(authorization[7:]) < 32:
            raise AccessDenied(401)
        digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
        match = next((c for c in self.credentials if secrets.compare_digest(digest, c['key_sha256'])), None)
        if match is None:
            raise AccessDenied(401)
        if organization != match['organization_id'] or permission not in match['permissions']:
            raise AccessDenied(403)
        return UUID(match['organization_id'])

# Peticiones a APIs externas (servidor).

import json
import urllib.error
import urllib.request

_USER_AGENT = 'KanbanTFG/1.0'
_TIMEOUT = 6


def _fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_advice():
    """Consejo aleatorio desde api.adviceslip.com."""
    try:
        data = _fetch_json('https://api.adviceslip.com/advice')
        return (data.get('slip') or {}).get('advice', '')
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return ''


def fetch_random_users(count=3):
    """Avatares de colaboradores desde randomuser.me."""
    try:
        url = f'https://randomuser.me/api/?results={count}&nat=es'
        data = _fetch_json(url)
        members = []
        for user in data.get('results', []):
            name = user.get('name', {})
            full = f"{name.get('first', '')} {name.get('last', '')}".strip()
            picture = (user.get('picture') or {}).get('thumbnail', '')
            if full and picture:
                members.append({'name': full, 'picture': picture})
        return members
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return []

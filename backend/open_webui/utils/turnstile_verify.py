import asyncio
from datetime import datetime

import aiohttp

from open_webui.env import TURNSTILE_ENABLE, TURNSTILE_SECRET_KEY,TURNSTILE_CACHE_EXPIRE,TURNSTILE_MAX_USE_COUNT

# user_id -> (token, datetime, use_count)
turnstile_token_cache: dict[str, tuple[str, datetime, int]] = {}

user_locks: dict[str, asyncio.Lock] = {}


async def site_verify(client_ip: str, user_id: str, token: str):
    if not TURNSTILE_ENABLE:
        return True

    if not token or len(token) > 2048:
        return False

    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    async with user_locks[user_id]:

        if user_id in turnstile_token_cache:
            cache_token, dt, use_count = turnstile_token_cache[user_id]

            if token == cache_token:
                if (datetime.now() - dt).seconds > TURNSTILE_CACHE_EXPIRE:
                    return False

                if use_count >= TURNSTILE_MAX_USE_COUNT:
                    return False

                turnstile_token_cache[user_id] = (token, dt, use_count + 1)
                return True

        url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        payload = {
            'secret': TURNSTILE_SECRET_KEY,
            'response': token,
            'remoteip': client_ip
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                success = data.get('success', False)
                if not success:
                    return False

                action = data.get('action', '')
                if action != 'chat':
                    return False

                cdata = data.get('cdata', '')
                if cdata != user_id:
                    return False

                turnstile_token_cache[user_id] = (token, datetime.now(), 0)
                return True

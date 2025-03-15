from open_webui.env import TURNSTILE_ENABLE, TURNSTILE_SECRET_KEY
import aiohttp

async def site_verify(client_ip:str,user_id:int,token:str):
    if not TURNSTILE_ENABLE:
        return True

    if not token or len(token) > 2048:
        return False

    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    payload = {
      'secret': TURNSTILE_SECRET_KEY,
      'response': token,
      'remoteip': client_ip
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url,json=payload) as resp:
            data = await resp.json()
            success = data.get('success',False)
            if not success:
                return False

            action = data.get('action','')
            if action != 'chat':
                return False

            cdata = data.get('cdata','')
            if cdata != str(user_id):
                return False

            return True



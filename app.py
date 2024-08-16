from email import header
import os
import asyncio
import httpx
import random
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from telethon import TelegramClient, utils
from telethon.types import UpdateNewMessage
from telethon.events import NewMessage

TIMEOUT_CODE = 120
DELAY = 30

if not os.getenv('API_ID') or not os.getenv('API_HASH'):
    raise ValueError('API_ID or API_HASH variable empty')

async def sleep():
    await asyncio.sleep(random.uniform(0.5, 3))

def write_apis(api_id, api_hash):
    local_file = f'apis/{datetime.now().strftime("%d_%m_%Y_%H_%M")}.csv'
    geral_file = 'apis.csv'

    if os.path.exists('apis'):
        os.makedirs('apis')

    if not os.path.exists(local_file):
        with open (local_file, 'w') as f:
            f.write('api_id,api_hash\n')

    if not os.path.exists(geral_file):
        with open (geral_file, 'w') as f:
            f.write('api_id,api_hash\n')

    with open (local_file, 'a') as f:
        csv_writer = csv.writer(f, delimiter=',')
        csv_writer.writerow([api_id, api_hash])

    with open (geral_file, 'a') as f:
        csv_writer = csv.writer(f, delimiter=',')
        csv_writer.writerow([api_id, api_hash])


class ReceiveCode:
    def __init__(self, phone):
        self.client = TelegramClient(f'sessions/{phone}', os.getenv('API_ID'), os.getenv('API_HASH'))
        self.code = ''
        self.name = phone
        self.phone = phone

    async def start(self):
        await self.client.connect()
        me  = await self.client.get_me()
        if me:
            self.phone = me.phone
            self.name = utils.get_display_name(me)
            print(f'Starting fetching api_id for: {self.name} {me.phone}')
            self.client.add_event_handler(self.callback_code, NewMessage(chats=[777000]))
            return True

        print('Error in connect to session')
        if self.client.is_connected():
            await self.client.disconnect()

    async def callback_code(self, event:UpdateNewMessage):
        msg = event.message.text.replace('*', '')

        await asyncio.sleep(0.1)
        code_match = re.search(r"login code:\s*([\w\-]+)", msg, flags=re.IGNORECASE)
        if code_match:
            self.code = code_match.group(1).strip()

        else:
            code_match = re.search(r"de login:\s*([\w\-]+)", msg, flags=re.IGNORECASE)
            if code_match:
                self.code = code_match.group(1).strip()

        if self.code:
            print(f'Found code {self.code}')

    async def get_code(self):
        print(f'Listening code for {self.name}')

        async def search_code():
            while True:
                if self.code:
                    return self.code
                await asyncio.sleep(0.2)

        try:
            await asyncio.wait_for(search_code(), timeout=TIMEOUT_CODE)
            await sleep()
        except asyncio.Timeout:
            pass
        finally:
            if self.client.is_connected():
                await self.client.disconnect()

            return self.code


async def request_tg_code_get_random_hash(session, phone):
    """ await httpx Login Code
    and returns a random_hash
    which is used in STEP TWO """

    request_url = "https://my.telegram.org/auth/send_password"
    request_data = {"phone": phone}
    response = await session.post(request_url, data=request_data)
    await sleep()

    if response.status_code == 429 or 'too many request' in response.text:
        print('Flood Alert...')

    elif response.status_code == 200:
        json_response = response.json()
        return json_response["random_hash"]

    else:
        print(f'Erro in get_random_hash: {response.text}')


async def login_step_get_stel_cookie(session, phone, tg_random_hash, tg_cloud_password):
    """Logins to my.telegram.org and returns the cookie,
    or False in case of failure"""

    request_url = "https://my.telegram.org/auth/login"
    request_data = {"phone": phone,"random_hash": tg_random_hash,"password": tg_cloud_password}
    response = await session.post(request_url, data=request_data)
    await sleep()
    
    if response.text == "true":
        return response.headers.get("Set-Cookie")
    else:
        print(f'Error in login to my.telegram.org: {response.text}')


async def scarp_tg_existing_app(session, stel_token):
    """scraps the web page using the provided cookie,
    returns True or False appropriately"""

    request_url = "https://my.telegram.org/apps"
    custom_header = {"Cookie": stel_token}
    response = await session.get(request_url, headers=custom_header)
    response_text = response.text
    await sleep()

    soup = BeautifulSoup(response_text, features="html.parser")
    title_of_page = soup.title.string

    re_dict_vals = {}
    re_status_id = None

    if "configuration" in title_of_page:
        g_inputs = soup.find_all("span", {"class": "input-xlarge"})

        app_id = g_inputs[0].string
        api_hash = g_inputs[1].string
        test_configuration = g_inputs[4].string
        production_configuration = g_inputs[5].string
        _a = "It is forbidden to pass this value to third parties."
        hi_inputs = soup.find_all("p", {"class": "help-block"})
        test_dc = hi_inputs[-2].text.strip()
        production_dc = hi_inputs[-1].text.strip()

        re_dict_vals = {
            "App Configuration": {"app_id": app_id,"api_hash": api_hash},
            "Available MTProto Servers": {
                "test_configuration": {"IP": test_configuration,"DC": test_dc},
                "production_configuration": {"IP": production_configuration,"DC": production_dc}
                },
            "Disclaimer": _a
        }

        re_status_id = True
    else:
        tg_app_hash = soup.find("input", {"name": "hash"}).get("value")
        re_dict_vals = {"tg_app_hash": tg_app_hash}
        re_status_id = False

    return re_status_id, re_dict_vals


async def create_new_tg_app(session, tg_app_hash, app_title, app_shortname, app_url, app_platform, app_desc):

    """ creates a new my.telegram.org/apps
    using the provided parameters """

    request_url = "https://my.telegram.org/apps/create"
    request_data = {
        "hash": tg_app_hash,
        "app_title": app_title,
        "app_shortname": app_shortname,
        "app_url": app_url,
        "app_platform": app_platform,
        "app_desc": app_desc
    }
    return await session.post(request_url, data=request_data)


async def create_api(phone, receiver):

    async with httpx.AsyncClient() as session:
        random_hash = await request_tg_code_get_random_hash(session, phone)
        if random_hash:
            provided_code = await receiver.get_code()
            if provided_code:

                cookie = await login_step_get_stel_cookie(session, phone, random_hash, provided_code)
                if cookie:
                    status, response = await scarp_tg_existing_app(session, cookie)
                    if not status:
                        await create_new_tg_app(
                            session,
                            response.get("tg_app_hash"),
                            f"mybot",
                            f"mybotapp{random.randint(3,99999)}",
                            "",
                            "android",
                            ""
                        )
                        await sleep()

                    status, response = await scarp_tg_existing_app(session, cookie)
                    if status:
                        api_id = response["App Configuration"]["app_id"]
                        api_hash = response["App Configuration"]["api_hash"]
                        print(f'{phone}\napi_id: {api_id}\napi_hash: {api_hash}')
                        write_apis(api_id, api_hash)

                    else:
                        print(f"creating APP ID caused error {response}")

async def main():
    sessions = [
        session.replace('.session', '') 
        for session in os.listdir('sessions') 
        if session.endswith('.session')
    ]
    if not sessions:
        raise ValueError ('Fouder sessions empty')

    for session in sessions:
        
        try:
            phone = utils.parse_phone(session)
            print(f'creating api for {phone}')
            receiver = ReceiveCode(phone)
            if await receiver.start():
                await create_api(receiver.phone, receiver)

        except Exception as e:
            print(f'Error in api create for {phone}: {e}')
            raise e

        print(f'Waiting {DELAY}s seconds...')
        await asyncio.sleep(DELAY)

if __name__ == "__main__":
    asyncio.run(main())
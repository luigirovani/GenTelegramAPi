## Create credencials (api_id and api_hash) massively using sessions telethon.

1. Clone this repository
2. Installs all dependencies specified in the requirements.txt file
3. Set your api_id and api_hash (only to login with sessions files) in env vars
4. put your sessions file in 'sessions' folder
5. Set your proxy in PROXY var (optional)
6. Execute app.py file.

Your credentials will be written to the apis.csv file and the apis folder.

```bash
git clone https://github.com/luigirovani/GenTelegramAPi
cd GenTelegramAPi
pip install -r requirements.txt
set API_ID=12345
set API_HASH=0123456789abcdef0123456789abcdef
python app.py
```

#### Aditional note:
- If you wish to use proxies, configure them in the format required by httpx. Remember to use proxies from the same country as the accounts for which you want to create credentials.
Example:
```
PROXY = {
  "http://": "http://localhost:8080",
  "https://": "http://localhost:8080"
}
```
Read httpx documentation for more information about proxies.

#### Disclaimer:
- Use this script at your own risk and responsibility.

from pprint import pprint

import requests


'''
    curl -s http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"<login>","password":"<pass>"}'
    '''

# метод для получения токена
def get_token_by_auth(login: str, password: str | int) -> dict[str, str]:
    url = 'http://127.0.0.1:8000/api/token/'
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        'username': login,
        'password': password
    }
    resp = requests.post(url=url, json=data, headers=headers)
    if resp.status_code == 200:
        print('Успешный статус кода')
        return resp.json()
    raise Exception(f'Ошибка статуса кода: {resp.status_code}')


def check_refresh(token: str | None) -> dict | None | str:
    url = 'http://127.0.0.1:8000/api/v1/me/'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url=url, headers=headers)
    if response.status_code == 200:
        print('Успешный статус кода')
        return response.json()
    raise Exception(f'Ошибка статуса кода: {response.status_code}')

tok = get_token_by_auth('root', 1234).get('access')
pprint(tok)
pprint(check_refresh(tok))
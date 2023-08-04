from typing import Dict, Generator, Optional

from httpx import URL, Auth, Cookies, get, post
from httpx._models import Request, Response


def parse_cookies_str_to_dict(cookies: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in cookies.split(';'):
        item = item.strip()
        if not item:
            continue
        if '=' not in item:
            result[item] = ''
            continue
        name, value = item.split('=', 1)
        result[name] = value
    return result


class vManageAuth(Auth):
    requires_request_body = True

    @staticmethod
    def get_jsessionid(base_url: str, username: str, password: str) -> str:
        security_payload = {
            'j_username': username,
            'j_password': password,
        }
        url = base_url + '/j_security_check'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response: Response = post(
            url=url, headers=headers, data=security_payload, verify=False
        )
        cookies_string = response.headers.get('set-cookie', '')
        return parse_cookies_str_to_dict(cookies_string).get('JSESSIONID')

    @staticmethod
    def get_xsrftoken(base_url: str, jsessionid: str) -> str:
        url = base_url + '/dataservice/client/token'
        headers = {'Content-Type': 'application/json'}
        response: Response = get(
            url=url,
            cookies=Cookies({'JSESSIONID': jsessionid}),
            headers=headers,
            verify=False,
        )
        return response.text

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.jsessionid: Optional[str] = None
        self.xsrftoken: Optional[str] = None

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        if self.jsessionid is None or self.xsrftoken is None:
            self.authenticate(request)
        Cookies({'JSESSIONID': self.jsessionid}).set_cookie_header(request)
        request.headers['x-xsrf-token'] = self.xsrftoken
        yield request

    def authenticate(self, request: Request):
        base_url = str(URL(scheme=request.url.scheme, netloc=request.url.netloc))
        print(
            f'Authenticating {self.username} {self.password} session using: {base_url}'
        )
        self.jsessionid = self.get_jsessionid(base_url, self.username, self.password)
        print(f'Obtained JSESSIONID={self.jsessionid}')
        self.xsrftoken = self.get_xsrftoken(base_url, self.jsessionid)
        print(f'Obtained token={self.xsrftoken}')

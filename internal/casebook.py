import dataclasses
import datetime
import json
import time

import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


@dataclasses.dataclass
class CaseBookCache:
    login_data: dict


@dataclasses.dataclass
class Side:
    name: str
    inn: str
    ogrn: str


@dataclasses.dataclass
class Case:
    plaintiff: Side
    respondent: Side
    court: str
    url: str
    number: str
    reg_date: datetime.date
    _type: dict


class Casebook:
    def __init__(self, cache: CaseBookCache):
        self.auth_email = None
        self.auth_token = None
        self.login = cache.login_data['login']
        self.password = cache.login_data['password']
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.selenium_driver = webdriver.Chrome(options=options)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/118.0.5993.2470 YaBrowser/23.11.0.2470 Yowser/2.5 Safari/537.36'
        self.http_client = urllib3.PoolManager()
        auth_result = self.headless_auth(self.login, self.password)
        self.headers = {
            'cookie': f'.AuthToken={auth_result["token"]};'
                      f' .AuthEmail={auth_result["email"]}',
            'user-agent': self.user_agent,
            'content-type': 'application/json'
        }
        time.sleep(4)
        self.filters = None
        self.get_filters()

    def headless_auth(self, login: str, password: str):
        self.selenium_driver.get("https://casebook.ru/login")
        email_field = self.selenium_driver.find_element(By.NAME, "UserName")
        email_field.clear()
        email_field.send_keys(login)

        password_field = self.selenium_driver.find_element(By.NAME, "Password")
        password_field.clear()
        password_field.send_keys(password)

        self.selenium_driver.find_element(By.CLASS_NAME, "ui-button").click()

        time.sleep(6)

        cookie = self.selenium_driver.get_cookies()

        for i in cookie:
            if i['name'] == '.AuthToken':
                auth_token = i['value']
                self.auth_token = auth_token
            elif i['name'] == '.AuthEmail':
                auth_email = i['value']
                self.auth_email = auth_email

        return {'email': self.auth_email,
                'token': self.auth_token}

    def get_filters(self):
        response = self.http_client.request('GET', 'https://casebook.ru/ms/UserData/SavedSearch/List',
                                            headers=self.headers)
        serialized = json.loads(response.data)
        self.filters = [
            {"name": filter_['name'], "id": filter_["id"], "filter": json.loads(filter_['serializedRequest'])}
            for filter_ in serialized['result']]

    def get_info_about_case(self):
        pass

    def get_cases(self, filter_):
        query = f'{filter_}, "page":1,"count":30,"isNeedStat":true'
        response = self.http_client.request('POST', 'https://casebook.ru/ms/Search/Cases/Search',
                                            body=query.replace('None', 'null'),
                                            headers=self.headers)
        serialized = json.loads(response.data)
        pages = serialized['result']['pagesCount']
        cases = []
        result = []
        for i in range(1, pages + 1):
            query = f'{filter_}, "page":{i}, "count":30,"isNeedStat":true'
            response = self.http_client.request('POST', 'https://casebook.ru/ms/Search/Cases/Search',
                                                body=query.replace('None', 'null'),
                                                headers=self.headers)

            serialized = json.loads(response.data)
            for case in serialized['result']['items']:
                cases.append(case)
        for case in cases:
            for side in case['sides']:
                have_stopword = False
                from stopwords import stopwords
                for stopword in stopwords:
                    if stopword.upper() in side['name'].upper():
                        continue
                if side['typeEnum'] == "Plaintiff":
                    plaintiff = Side(
                            name=side['name'],
                            inn=side['inn'],
                            ogrn=side['ogrn'],
                        )
                elif side['typeEnum'] == "Respondent":
                    respondent = Side(
                        name=side['name'],
                        inn=side['inn'],
                        ogrn=side['ogrn'],
                    )
            if have_stopword:
                continue
            else:
                case_ = Case(
                    plaintiff=plaintiff,
                    respondent=respondent,
                    court=case['instancesInternal'][0]['court'],
                    url=f'https://casebook.ru/card/case/{case["caseId"]}',
                    number=case['caseNumber'],
                    reg_date=datetime.datetime.fromisoformat(case['startDate']).date(),
                    _type={
                        "caseTypeM": case['caseTypeMCode'],
                        "caseTypeENG": case['caseType']
                    }
                )
                result.append(case_)
        for i in result:
            print(i)
        return cases

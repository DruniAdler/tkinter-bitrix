import dataclasses
import datetime
import json
import time

import urllib3
from postgrest import APIError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from supabase._sync.client import SyncClient


class GetOutOfLoop(Exception):
    pass


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
    sum_: float
    plaintiff: Side
    respondent: Side
    court: str
    url: str
    number: str
    reg_date: datetime.date
    _type: dict
    contacts_info: dict = dataclasses.field(default_factory=dict)
    error: str = None


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

    def headless_auth(self, login: str = None, password: str = None):
        if not login:
            login = self.login
            password = self.password
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

        self.headers = {
            'cookie': f'.AuthToken={self.auth_token};'
                      f' .AuthEmail={self.auth_email}',
            'user-agent': self.user_agent,
            'content-type': 'application/json'
        }

        return {'email': self.auth_email,
                'token': self.auth_token}

    def get_filters(self):
        response = self.http_client.request('GET', 'https://casebook.ru/ms/UserData/SavedSearch/List',
                                            headers=self.headers)
        try:
            serialized = json.loads(response.data)
        except json.decoder.JSONDecodeError:
            time.sleep(5)
            self.headless_auth()
        self.filters = [
            {"name": filter_['name'], "id": filter_["id"], "filter": json.loads(filter_['serializedRequest'])}
            for filter_ in serialized['result']]

    def get_info_about_case(self):
        pass

    def get_cases(self, filter_source: dict, timedelta, supabase: SyncClient):
        serialized = None
        i = 0
        filter_ = filter_source
        for filter__ in filter_['items']:
            try:
                if filter__['filter']['type'] == 'CaseStartDate':
                    filter_['items'][i]['filter']['value'] = {
                        'from': (datetime.datetime.now().date() - datetime.timedelta(days=timedelta)).strftime(
                            '%Y-%m-%d'),
                        'to': datetime.datetime.now().date().strftime('%Y-%m-%d')
                    }
                else:
                    i += 1
            except KeyError:
                i += 1
        query = filter_
        query['page'] = 1
        query['count'] = 30
        query['isNeedStat'] = True
        query = str(query)
        response = self.http_client.request('POST', 'https://casebook.ru/ms/Search/Cases/Search',
                                            body=query.replace('None', 'null')
                                            .replace("'", '"')
                                            .replace('True', 'true')
                                            .replace('False', 'false'),
                                            headers=self.headers)
        serialized = json.loads(response.data)
        pages = serialized['result']['pagesCount']
        cases = []
        result = []
        for page in range(1, pages + 1):
            serialized_page = None
            curr_query = filter_
            curr_query['page'] = page
            curr_query['count'] = 30
            curr_query['isNeedStat'] = True
            curr_query = str(curr_query)
            response = self.http_client.request('POST', 'https://casebook.ru/ms/Search/Cases/Search',
                                                body=curr_query.replace('None', 'null')
                                                .replace("'", '"')
                                                .replace('True', 'true')
                                                .replace('False', 'false'),
                                                headers=self.headers)
            serialized_page = json.loads(response.data)
            for case in serialized_page['result']['items']:
                cases.append(case)
        for case in cases:
            if len(case['sides']) > 2:
                _respondent = 0
                _plaintiff = 0
                _other = 0
                for side in case['sides']:
                    if side['nSideTypeEnum'] == 'Other':
                        _other += 1
                    elif side['nSideTypeEnum'] == 'Plaintiff':
                        _plaintiff += 1
                    elif side['nSideTypeEnum'] == 'Respondent':
                        _respondent += 1
                    else:
                        _other += 1
                try:
                    if _respondent > 1:
                        supabase.table('processed_cases').insert({
                            'processed_date': datetime.datetime.now().date().isoformat(),
                            'case_id': case['caseNumber'],
                            'is_success': False,
                            'error': 'больше одного ответчика, отфильтровано'
                        }).execute()
                        cases.remove(case)
                        continue
                except APIError as e:
                    if e.code == '23505':
                        pass
                    else:
                        print(e.code, e.message)
        for case in cases:
            try:
                for side in case['sides']:
                    from stopwords import stopwords
                    if side['nSideTypeEnum'] == 'Respondent' or side['nSideTypeEnum'] == 'OtherRespondent':
                        for stopword in stopwords:
                            if stopword.upper() in side['name'].upper():
                                try:
                                    supabase.table('processed_cases').insert({
                                        'processed_date': datetime.datetime.now().date().isoformat(),
                                        'case_id': case['caseNumber'],
                                        'is_success': False,
                                        'error': f'Встретилось стоп-слово, отфильстровано. (PS -> {stopword})'
                                    }).execute()
                                except APIError as e:
                                    if e.code == '23505':
                                        pass
                                    else:
                                        print(e.code, e.message)
                                raise GetOutOfLoop
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
                    date = datetime.datetime.fromisoformat(case['startDate']).date()
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
                        },
                        sum_=case['claimSum']
                    )
                    result.append(case_)
            except GetOutOfLoop:
                pass
        print(len(result))
        return result

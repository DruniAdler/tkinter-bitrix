import datetime
from typing import Tuple, List, Any

import requests
import re
from bs4 import BeautifulSoup


def find_phone(text):
    lines = text.split('\n')
    for line in lines:
        if "+7" in line:
            return line


def find_mail(text):
    lines = text.split('\n')
    for line in lines:
        if "@" in line:
            return line


def process_string(input_string, number_list):
    try:
        pattern = re.compile(r'\+7\s\d{3}\s\d{3}-\d{2}-\d{2}|\+8\s\d{3}\s\d{3}-\d{2}-\d{2}')
        matches = pattern.findall(input_string)
        for match in matches:
            number_list.append(match)
        return number_list
    except Exception as e:
        pass


def process_email_string(input_string, email_list):
    try:
        if not isinstance(input_string, str):
            input_string = str(input_string)
        domain_pattern = re.compile(r'([^\s]+?\.(com|ru|net|org|gov|edu|int|mil|co|uk|de|fr|es|it|nl|ca|au|jp|us))')
        matches = domain_pattern.findall(input_string)
        email = [f"{match[0]}" for match in matches]
        email_list.extend(email)
        return email_list
    except Exception as e:
        pass


def remove_duplicates(input_list):
    try:
        unique_list = list(set(input_list))
        return unique_list
    except Exception as e:
        pass


def process_two(ogrn):
    url2 = "https://checko.ru/company/" + ogrn
    headers = {
        'User-Agent': 'Mozila/5.0(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response_two_0 = requests.get(url2, headers=headers)
        soup2 = BeautifulSoup(response_two_0.text, "html.parser")
        info_two = soup2.find("div", class_="uk-container uk-container-xlarge x-container").find("section",
                                                                                                 id="contacts")
        return info_two.text
        # await process_string(find_phone(info_two.text), number_list)
        # await process_email_string(find_mail(info_two.text), email_list)
    except Exception as e:
        pass


def process_three(ogrn):
    url3 = "https://companium.ru/id/" + ogrn
    headers = {
        'User-Agent': 'Mozila/5.0(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response_three_0 = requests.get(url3, headers=headers)
        soup3 = BeautifulSoup(response_three_0.text, "html.parser")
        info_three = soup3.find("div", class_="row gy-3 gx-5")
        return info_three.text
        # await process_string(find_phone(info_three.text), number_list)
        # await process_email_string(find_mail(info_three.text), email_list)
    except Exception as e:
        pass


def process_four(ogrn):
    url4 = "https://vbankcenter.ru/contragent/" + ogrn
    headers = {
        'User-Agent': 'Mozila/5.0(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response_four_0 = requests.get(url4, headers=headers)
        soup4 = BeautifulSoup(response_four_0.text, "html.parser")
        info_four = soup4.find("div", class_="requisites-ul-item grid items-start gap-y-4 gap-x-12")
        info_four = info_four.find_all("section")
        return info_four
        # await process_string(find_phone(info_four[3].find("gweb-copy",
        #                                                   class_="gweb-copy relative inline-block mb-0 py-0 copy-available "
        #                                                          "z-10 cursor-pointer copy-right-padding").text),
        #                      number_list)
        # await process_email_string(find_mail(info_four[3].find("a").text), email_list)
    except Exception as e:
        pass


def get_contacts(inn, ogrn):
    number_list = []
    email_list = []

    second_res = process_two(ogrn)
    three_res = process_three(ogrn)
    # four_res = process_four(ogrn)

    try:
        process_string(find_phone(second_res), number_list)
    except Exception as e:
        pass
    try:
        process_email_string(find_mail(second_res), email_list)
    except Exception as e:
        pass
    try:
        process_string(find_phone(three_res), number_list)
    except Exception as e:
        pass
    try:
        process_email_string(find_mail(three_res), email_list)
    except Exception as e:
        pass

    number_list = list(set(number_list))
    email_list = list(set(email_list))

    return {'numbers': number_list,
            'emails': email_list}

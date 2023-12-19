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
    pattern = re.compile(r'\+7\s\d{3}\s\d{3}-\d{2}-\d{2}|\+8\s\d{3}\s\d{3}-\d{2}-\d{2}')
    matches = pattern.findall(input_string)
    for match in matches:
        number_list.append(match)
    return number_list


def process_email_string(input_string, email_list):
    if not isinstance(input_string, str):
        input_string = str(input_string)
    domain_pattern = re.compile(r'([^\s]+?\.(com|ru|net|org|gov|edu|int|mil|co|uk|de|fr|es|it|nl|ca|au|jp|us))')
    matches = domain_pattern.findall(input_string)
    email = [f"{match[0]}" for match in matches]
    email_list.extend(email)
    return email_list


def remove_duplicates(input_list):
    unique_list = list(set(input_list))
    return unique_list


def get_contacts(inn, ogrn) -> Exception | tuple[list[Any], list[Any]]:
    number_list = []
    email_list = []

    url1 = "https://www.list-org.com/search?type=inn&val=" + inn
    url2 = "https://checko.ru/company/" + ogrn
    url3 = "https://companium.ru/id/" + ogrn
    url4 = "https://vbankcenter.ru/contragent/" + ogrn

    headers = {
        'User-Agent': 'Mozila/5.0(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response_one_0 = requests.get(url1, headers=headers)
    try:
        soup = BeautifulSoup(response_one_0.text, "html.parser")
        link = soup.find("div", class_='card w-100 p-1 p-lg-3 mt-1').find("div", class_="org_list").find("p").find("a")[
            "href"]
        get_link_one = "https://www.list-org.com/" + link
        response_one_1 = requests.get(get_link_one, headers=headers)
        soup = BeautifulSoup(response_one_1.text, "html.parser")
        info_one = soup.find('div', class_="card w-100 p-1 p-lg-3 mt-2")
        process_string(find_phone(info_one.text), number_list)
        process_email_string(find_mail(info_one.text), email_list)
    except Exception as e:
        return e

    try:
        response_two_0 = requests.get(url2, headers=headers)

        soup2 = BeautifulSoup(response_two_0.text, "html.parser")

        info_two = soup2.find("div", class_="uk-container uk-container-xlarge x-container").find("section",
                                                                                                 id="contacts")

        process_string(find_phone(info_two.text), number_list)
        process_email_string(find_mail(info_two.text), email_list)
    except Exception as e:
        return e

    try:
        response_three_0 = requests.get(url3, headers=headers)

        soup3 = BeautifulSoup(response_three_0.text, "html.parser")
        info_three = soup3.find("div", class_="row gy-3 gx-5")
        process_string(find_phone(info_three.text), number_list)
        process_email_string(find_mail(info_three.text), email_list)
    except Exception as e:
        return e

    try:
        response_four_0 = requests.get(url4, headers=headers)

        soup4 = BeautifulSoup(response_four_0.text, "html.parser")
        info_four = soup4.find("div", class_="requisites-ul-item grid items-start gap-y-4 gap-x-12")
        info_four = info_four.find_all("section")
        process_string(find_phone(info_four[3].find("gweb-copy",
                                                    class_="gweb-copy relative inline-block mb-0 py-0 copy-available "
                                                           "z-10 cursor-pointer copy-right-padding").text), number_list)
        process_email_string(find_mail(info_four[3].find("a").text), email_list)
    except Exception as e:
        return e
    number_list = list(set(number_list))
    email_list = list(set(email_list))
    return number_list, email_list

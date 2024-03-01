import asyncio
import dataclasses
import json
import os
import time
from datetime import datetime

import customtkinter
import tkinter
import tkinter.messagebox

import postgrest.exceptions
from fast_bitrix24.server_response import ErrorInServerResponseException
from supabase import create_client

from internal.bitrix import BitrixConnect
from internal.casebook import CaseBookCache, Casebook
from internal.contacts import get_contacts_via_export_base

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


@dataclasses.dataclass
class BitrixCache:
    login_data: dict


@dataclasses.dataclass
class Cache:
    bitrix_cache: BitrixCache
    casebook_cache: CaseBookCache


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.rights = False
        self.selected_timedelta = 1
        self.work = False

        # configure window
        self.title("Битрикс Парсер")
        self.geometry(f"{400}x{580}")
        self.resizable(width=False, height=False)

        self.status = tkinter.StringVar()
        self.status.set('Старт')

        self.delay = tkinter.StringVar()
        self.delay.set('20')

        self.without_contacts_: tkinter.Variable = tkinter.IntVar()

        # configure grid layout (4x4)
        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)

        self.textbox = customtkinter.CTkTextbox(self, width=360, height=150, state='disabled')
        self.textbox.grid(row=0, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.log('Старт приложения')

        self.supabase = create_client(supabase_url='https://nebvfbgddtwwyesuclkg.supabase.co',
                                      supabase_key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5lYnZmYmdkZHR3d3llc3VjbGtnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDI5MTkxOTQsImV4cCI6MjAxODQ5NTE5NH0.3d-TbkiCuNYDF9FZYnuE24RW7txH2fBcjA9aJK3jOwI')

        creds = self.supabase.table('credentionals').select('*').execute()
        for data in creds.data:
            if data['name'] == 'bitrix':
                self.bitrix_data = data
            elif data['name'] == 'casebook':
                self.casebook_data = data
            elif data['name'] == 'exportbase':
                self.exportbase_data = data

        self.casebook = Casebook(cache=CaseBookCache(login_data=self.casebook_data))

        self.day = datetime.now()

        self.log("Авторизация Casebook успешно...")

        self.bitrix = BitrixConnect(webhook=self.bitrix_data['login'])

        self.config_group = customtkinter.CTkFrame(self, height=50)
        self.config_group.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.config_label = customtkinter.CTkLabel(self.config_group, text="Конфигурация")
        self.config_label.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.period_label = customtkinter.CTkLabel(self.config_group, text="Период сканирования")
        self.period_label.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.update_period = customtkinter.CTkOptionMenu(self.config_group, height=10,
                                                         values=['1 день', '3 дня', '1 неделя', '2 недели', 'месяц'],
                                                         command=self.change_time_delta)
        self.update_period.grid(row=2, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.data_set = customtkinter.CTkLabel(self.config_group, text="Источник данных")
        self.data_set.grid(row=3, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.update_data_set = customtkinter.CTkOptionMenu(self.config_group, height=10,
                                                           values=[filter_['name'] for filter_ in
                                                                   self.casebook.filters],
                                                           command=self.change_filter)
        self.selected_filter = self.casebook.filters[0]
        self.update_data_set.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.period_label = customtkinter.CTkLabel(self.config_group, text="Пауза между \n прогонами в минутах")
        self.period_label.grid(row=4, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.work_interval = customtkinter.CTkEntry(self.config_group, textvariable=self.delay)
        self.work_interval.grid(row=4, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # self.without_contacts_label = customtkinter.CTkLabel(self.config_group, text="Загружать без \n контактов")
        # self.without_contacts_label.grid(row=5, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.without_contacts = customtkinter.CTkCheckBox(self.config_group, variable=self.without_contacts_,
                                                          text='Загружать без контактов')

        self.without_contacts.grid(row=5, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew", columnspan=2)

        self.start_button = customtkinter.CTkButton(self, textvariable=self.status, command=self.start_stop,
                                                    fg_color='blue', hover_color='blue')
        self.start_button.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

    def change_filter(self, choice):
        self.selected_filter = list(filter(lambda x: x.get('name') == choice, self.casebook.filters))[0]
        if self.selected_filter.get('id') == 558875:
            self.log('СПОРЫ ПО ТОВАРНЫМ ЗНАКАМ!')
            self.rights = True
        else:
            self.rights = False

    def change_time_delta(self, choice):
        if choice == '1 день':
            self.selected_timedelta = 1
        elif choice == '3 дня':
            self.selected_timedelta = 3
        elif choice == '1 неделя':
            self.selected_timedelta = 7
        elif choice == '2 недели':
            self.selected_timedelta = 14
        elif choice == 'месяц':
            self.selected_timedelta = 30

    def start_stop(self):
        if self.status.get() == 'Старт':
            self.start_button.configure(fg_color='red', hover_color='red')
            self.work = True
            self.log('Начало работы... Подготовка...')
            success = self.scan()
            if not success:
                self.casebook = Casebook(cache=CaseBookCache(login_data=self.casebook_data))
                self.scan()
                success = False
            self.status.set('Стоп')
        elif self.status.get() == 'Стоп':
            self.status.set('Старт')
            self.work = False
            self.log('Завершение работы...')
            self.start_button.configure(fg_color='blue', hover_color='blue')

    def scan(self):
        if self.day != datetime.now():
            self.casebook = Casebook(cache=CaseBookCache(login_data=self.casebook_data))

        if self.work:
            self.log('Начало сканирования...')
            try:
                cases = self.casebook.get_cases(self.selected_filter['filter'], self.selected_timedelta, self.supabase)
            except json.decoder.JSONDecodeError:
                self.log('Ошибка авторизации, получение нового токена')
                self.casebook.headless_auth()
                cases = self.casebook.get_cases(self.selected_filter['filter'], self.selected_timedelta, self.supabase)
            if cases:
                self.log('Получаем контакты...')
                processed_cases = []
                for case in cases:
                    if not self.supabase.table('processed_cases').select('*').eq('case_id', str(case.number)).execute().data:
                        from internal.contacts import get_contacts
                        if 'индивидуальный предприниматель'.upper() in case.respondent.name.upper():
                            case.contacts_info = get_contacts_via_export_base(
                                ogrn=case.respondent.ogrn,
                                key=self.exportbase_data['password'])
                        else:
                            case.contacts_info = get_contacts(inn=case.respondent.inn, ogrn=case.respondent.ogrn)
                        processed_cases.append(case)
                cases = processed_cases
                print(cases)
                if self.without_contacts_.get() == 0:
                    for case in cases:
                        if case.contacts_info.get('emails') == [] and case.contacts_info.get('numbers') == []:
                            case.contacts_info = get_contacts_via_export_base(
                                ogrn=case.respondent.ogrn,
                                key=self.exportbase_data['password'])
                self.log('Формируем лиды...')
                print('лиды')
                for case in cases:
                    try:
                        if self.rights:
                            err = self.bitrix.create_lead(case, rights=False)
                        else:
                            err = self.bitrix.create_lead(case, rights=True)
                        if err:
                            raise err
                        else:
                            self.supabase.table('processed_cases').insert({
                                'processed_date': datetime.now().date().isoformat(),
                                'case_id': case.number,
                                'is_success': True,
                            }).execute()
                    except ErrorInServerResponseException as e:
                        self.supabase.table('processed_cases').insert({
                            'processed_date': datetime.now().date().isoformat(),
                            'case_id': case.number,
                            'is_success': False,
                            'error': f'Ошибка в контактных данных  {case.contacts_info}'
                        }).execute()
                        self.log(f'{case.number} не удалось записать в Б24')
                    except postgrest.exceptions.APIError as e:
                        print(case.number, ' <-- проконтролировать \n', e)
            else:
                self.log('Не найдено новых кейсов.')
            self.after(int(self.delay.get()) * 1000 * 60, self.scan)
            self.log(f'Цикл завершен, задача поставлена в \n очередь через {self.delay.get()} минут')
        else:
            self.after(10000, self.scan)
        return True

    def log(self, info):
        self.textbox.configure(state='normal')
        self.textbox.insert('end', f'[{datetime.now().time().strftime("%H:%M:%S")}] -> {str(info)} \n')
        self.textbox.configure(state='disabled')


if __name__ == "__main__":
    app = App()
    app.mainloop()

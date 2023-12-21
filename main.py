import asyncio
import dataclasses
import json
import os
from datetime import datetime

import customtkinter
import tkinter
import tkinter.messagebox

from supabase import create_client

from internal.bitrix import BitrixConnect
from internal.casebook import CaseBookCache, Casebook

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

        self.selected_timedelta = 1
        self.work = False

        # configure window
        self.title("Битрикс Парсер")
        self.geometry(f"{400}x{580}")
        self.resizable(width=False, height=False)

        self.status = tkinter.StringVar()
        self.status.set('Старт')

        # configure grid layout (4x4)
        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)

        self.textbox = customtkinter.CTkTextbox(self, width=360, height=150)
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

        self.casebook = Casebook(cache=CaseBookCache(login_data=self.casebook_data))

        self.log("Авторизация Casebook успешно...")

        self.bitrix = BitrixConnect(webhook=self.bitrix_data['login'])

        self.config_group = customtkinter.CTkFrame(self, height=50)
        self.config_group.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.config_label = customtkinter.CTkLabel(self.config_group, text="Конфигурация")
        self.config_label.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.period_label = customtkinter.CTkLabel(self.config_group, text="Период сканирования")
        self.period_label.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.update_period = customtkinter.CTkOptionMenu(self.config_group, height=10,
                                                         values=['1 день', '3 дня', '1 неделя', '2 недели', 'месяц',
                                                                 '<!тест!>'],
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

        self.start_button = customtkinter.CTkButton(self, textvariable=self.status, command=self.start_stop,
                                                    fg_color='blue', hover_color='blue')
        self.start_button.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

    def change_filter(self, choice):
        self.selected_filter = list(filter(lambda x: x.get('name') == choice, self.casebook.filters))[0]
        print(self.selected_filter)

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
        elif choice == '<!тест!>':
            self.selected_timedelta = (datetime.now().date() - datetime.strptime("09-11-2023", '%d-%m-%Y').date()).days
            self.log("[ВНИМАНИЕ] Выбрана тестовая выборка...")

    def start_stop(self):
        if self.status.get() == 'Старт':
            self.start_button.configure(fg_color='red', hover_color='red')
            self.work = True
            self.log('Начало работы... Подготовка...')
            self.scan()
            self.status.set('Стоп')
        elif self.status.get() == 'Стоп':
            self.status.set('Старт')
            self.work = False
            self.log('Завершение работы...')
            self.start_button.configure(fg_color='blue', hover_color='blue')

    def scan(self):
        if self.work:
            self.log('Начало сканирования...')
            try:
                cases = self.casebook.get_cases(self.selected_filter['filter'], self.selected_timedelta)
            except json.decoder.JSONDecodeError:
                self.log('Ошибка авторизации, получение нового токена')
                self.casebook.headless_auth()
            if cases:
                self.log('Получаем контакты...')
                for case in cases:
                    if (self.supabase.table('processed_cases').select().eq('case_id', str(case.number)).execute()).data:
                        cases.remove(case)
                        continue
                    from internal.contacts import get_contacts
                    case.contacts_info = get_contacts(inn=case.respondent.inn, ogrn=case.respondent.ogrn)
                    print(case.contacts_info)
                for case in cases:
                    if case.contacts_info['emails'] == [] and case.contacts_info['numbers'] == []:
                        cases.remove(case)
                [print(case) for case in cases]
                self.log('Формируем лиды...')
                for case in cases:
                    err = self.bitrix.create_lead(case)
                    if not err:
                        self.supabase.table('processed_cases').insert({
                            'processed_date': datetime.now().date(),
                            'case_id': case.number
                        })
                    else:
                        self.log(f'{case.number} не удалось записать в Б24')
            else:
                self.log('Не найдено новых кейсов.')
            self.after(600000, self.scan)
            self.log('Цикл завершен, задача поставлена в \n очередь через 10 минут')
        else:
            self.after(10000, self.scan)
        pass

    def log(self, info):
        self.textbox.insert('end', f'[{datetime.now().time().strftime("%H:%M:%S")}] -> {str(info)} \n')


if __name__ == "__main__":
    app = App()
    app.mainloop()

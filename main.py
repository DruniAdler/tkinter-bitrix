import dataclasses
import json
import os
from datetime import datetime

import customtkinter
import tkinter
import tkinter.messagebox

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

        self.work = False
        if os.path.isfile('cache.json'):
            with os.open('cache.json', os.O_RDWR) as f:
                cache = json.load(f)


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

        # prod
        # casebook = Casebook(cache=cache.casebook_cache)
        # test
        self.casebook = Casebook(cache=CaseBookCache(login_data={
            'login': "director@yk-cfo.ru",
            'password': "ykcfo3132",
        }))

        self.log("Авторизация Casebook успешно...")

        self.config_group = customtkinter.CTkFrame(self, height=50)
        self.config_group.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.config_label = customtkinter.CTkLabel(self.config_group, text="Конфигурация")
        self.config_label.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.period_label = customtkinter.CTkLabel(self.config_group, text="Период сканирования")
        self.period_label.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.update_period = customtkinter.CTkOptionMenu(self.config_group, height=10,
                                                         values=['1 день', '3 дня', '1 неделя', '2 недели', 'месяц'])
        self.update_period.grid(row=2, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.data_set = customtkinter.CTkLabel(self.config_group, text="Источник данных")
        self.data_set.grid(row=3, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.update_data_set = customtkinter.CTkOptionMenu(self.config_group, height=10,
                                                           values=[filter_['name'] for filter_ in self.casebook.filters],
                                                           command=self.change_filter)
        self.selected_filter = self.casebook.filters[0]
        self.update_data_set.grid(row=3, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.start_button = customtkinter.CTkButton(self, textvariable=self.status, command=self.start_stop,
                                                    fg_color='blue', hover_color='blue')
        self.start_button.grid(row=2, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")

    def change_filter(self, choice):
        self.selected_filter = list(filter(lambda x: x.get('name') == choice, self.casebook.filters))[0]
        print(self.selected_filter)

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
            self.casebook.get_cases(self.selected_filter['filter'])
        else:
            self.after(10000, self.scan())
        pass

    def log(self, info):
        self.textbox.insert('end', f'[{datetime.now().time().strftime("%H:%M:%S")}] -> {str(info)} \n')


if __name__ == "__main__":
    app = App()
    app.mainloop()

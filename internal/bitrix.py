from fast_bitrix24 import Bitrix


class BitrixConnect:
    def __init__(self, webhook='https://crm.yk-cfo.ru/rest/1690/eruxj0nx7ria5j0q/'):
        self.bitrix = Bitrix(webhook)

    def create_lead(self):
        pass

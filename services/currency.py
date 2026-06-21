from datetime import datetime
import random

class CurrencyRates:
    def __init__(self):
        self.rates = {
            "BTC": {"price": 900000000, "min": 700000000, "max": 1000000000, "avg": 900000000},
            "WETcoin": {"price": 290000000, "min": 250000000, "max": 350000000, "avg": 290000000},
            "NotCoin": {"price": 15000000, "min": 10000000, "max": 30000000, "avg": 15000000}
        }
        self.last_update = datetime.now()
    
    def update_rates(self):
        if (datetime.now() - self.last_update).total_seconds() < 300:
            return
        self._do_update()
    
    def force_update(self):
        self._do_update()
    
    def _do_update(self):
        for currency in self.rates:
            rand = random.random()
            if rand < 0.005:
                new_price = self.rates[currency]["min"]
            elif rand < 0.055:
                new_price = self.rates[currency]["max"]
            else:
                new_price = self.rates[currency]["avg"] * random.uniform(0.95, 1.05)
            
            self.rates[currency]["price"] = max(1, round(new_price))
        
        self.last_update = datetime.now()
    
    def get_time_until_update(self):
        elapsed = (datetime.now() - self.last_update).total_seconds()
        remaining = max(0, 300 - elapsed)
        return int(remaining)

currency_rates = CurrencyRates()

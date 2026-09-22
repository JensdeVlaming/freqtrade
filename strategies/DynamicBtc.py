import math
import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, CategoricalParameter

class DynamicBtc(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1h'
    startup_candle_count = 721
    can_short = False
    stoploss = -0.15
    minimal_roi = {}
    trailing_stop = False
    position_adjustment_enable = False
    process_only_new_candles = True
    use_exit_signal = True
    entry_window = CategoricalParameter([72, 168, 336], default=168, space='buy',optimize=False,load=False)
    exit_window = CategoricalParameter([72, 168, 336], default=72, space='sell',optimize=False,load=False)

    @property
    def protections(self):
        return [{'method': 'CooldownPeriod', 'stop_duration_candles': 1}]

    def populate_indicators(self, dataframe, metadata):
        d = dataframe
        d['sma720'] = d.close.rolling(720, min_periods=720).mean()
        for n in [72,168,336]:
            d[f'high_{n}'] = d.high.shift(1).rolling(n, min_periods=n).max()
            d[f'low_{n}'] = d.low.shift(1).rolling(n, min_periods=n).min()
        return d

    def populate_entry_trend(self, dataframe, metadata):
        d = dataframe
        d['enter_long'] = 0
        d['enter_tag'] = None
        mask = (d.close > d[f'high_{self.entry_window.value}']) & (d.close>d.sma720) & (d.volume>0)
        d.loc[mask, 'enter_long'] = 1
        d.loc[mask, 'enter_tag'] = 'breakout'
        return d

    def populate_exit_trend(self, dataframe, metadata):
        dataframe['exit_long'] = ((dataframe.close<dataframe[f'low_{self.exit_window.value}']) & (dataframe.volume>0)).astype(int)
        return dataframe

    def _exposure_cap(self):
        distance = -float(self.stoploss)
        if not math.isfinite(distance) or not 0 < distance < 1:
            raise ValueError('invalid effective stoploss')
        return min(1.0, 0.02 / distance)

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        try:
            equity = float(self.wallets.get_total_stake_amount())
            vals = [equity, float(current_rate), float(proposed_stake), float(max_stake), float(leverage)]
            if not all(math.isfinite(v) and v>0 for v in vals) or leverage != 1 or side != 'long' or pair != 'BTC/USDT':
                return 0.0
            minimum = 0.0 if min_stake is None else float(min_stake)
            if not math.isfinite(minimum) or minimum<0:
                return 0.0
            stake = min(equity*self._exposure_cap(), float(max_stake), float(proposed_stake))
            return stake if math.isfinite(stake) and stake>0 and stake>=minimum else 0.0
        except Exception:
            return 0.0

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs):
        try:
            equity = float(self.wallets.get_total_stake_amount())
            amount, rate = float(amount), float(rate)
            if pair != 'BTC/USDT' or side != 'long' or kwargs.get('leverage', 1) != 1:
                return False
            if not all(math.isfinite(v) and v > 0 for v in [equity, amount, rate]):
                return False
            return amount * rate <= equity * self._exposure_cap()
        except Exception:
            return False

class BaselineBtc(DynamicBtc):
    entry_window = CategoricalParameter([72,168,336],default=168,space='buy',optimize=False,load=False)
    exit_window = CategoricalParameter([72,168,336],default=72,space='sell',optimize=False,load=False)

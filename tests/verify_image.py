"""Offline deployment checks: packaged public config, strategy and persistence."""
import json
from pathlib import Path

from freqtrade.configuration.config_validation import validate_config_consistency
from freqtrade.enums import RunMode
from freqtrade.resolvers import StrategyResolver

config = json.loads(Path('/opt/btc/config/paper.json').read_text())
assert all(config['api_server'][key] == '' for key in
           ['username', 'password', 'jwt_secret_key', 'ws_token'])
# Stand in for the required Portainer environment values; never real credentials.
config['api_server'].update({
    'username': 'offline-test',
    'password': 'offline-test-only-not-a-secret',
    'jwt_secret_key': 'offline-test-only-not-a-secret-32-bytes',
    'ws_token': 'offline-test-only-not-a-secret-32-bytes',
})
config.update({
    'strategy': 'DynamicBtc',
    'strategy_path': '/opt/btc/strategies',
    'user_data_dir': Path('/freqtrade/user_data'),
    'runmode': RunMode.DRY_RUN,
})
strategy = StrategyResolver.load_strategy(config)
validate_config_consistency(config)
assert config['dry_run'] is True
assert config['exchange']['key'] == config['exchange']['secret'] == ''
assert config['exchange']['pair_whitelist'] == ['BTC/USDT']
assert strategy.entry_window.value == 168 and strategy.exit_window.value == 72
assert strategy.stoploss == -0.15 and strategy.startup_candle_count == 721
assert strategy.position_adjustment_enable is False and strategy.can_short is False
assert strategy.protections == [{'method': 'CooldownPeriod', 'stop_duration_candles': 1}]
assert abs(strategy._exposure_cap() - 2 / 15) < 1e-12
assert Path('/freqtrade/freqtrade/rpc/api_server/ui/installed/index.html').is_file()
probe = Path('/freqtrade/user_data/logs/.write-probe')
probe.write_text('persistence permissions OK')
probe.unlink()
print('PASS: packaged V5, native config validation, FreqUI and non-root storage permissions')

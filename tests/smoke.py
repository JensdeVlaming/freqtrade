"""Optional local smoke test; briefly runs an isolated paper bot against Binance.

Requires a locally built btc-paper:verify image. Uses throwaway credentials,
an anonymous data volume and no published ports. Removes only its own container
and anonymous volume, even on failure. Never run this against a real account.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

root = Path(__file__).resolve().parents[1]
env = dict(os.environ, UI_PASSWORD='smoke-test-only-not-a-secret',
           JWT_SECRET='smoke-test-only-not-a-secret-32-bytes',
           WS_TOKEN='smoke-test-only-not-a-secret-32-bytes')
rendered = subprocess.check_output(
    ['docker', 'compose', 'config', '--format', 'json'], cwd=root, env=env)
service = json.loads(rendered)['services']['freqtrade']
assert '--dry-run' in service['command']
name = 'btc-paper-smoke-' + uuid.uuid4().hex[:12]
args = ['docker', 'run', '--detach', '--name', name,
        '--mount', 'type=volume,target=/freqtrade/user_data']
for key, value in service['environment'].items():
    args += ['--env', f'{key}={value}']
args += ['btc-paper:verify', *service['command']]
try:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        logs = subprocess.check_output(['docker', 'logs', name], stderr=subprocess.STDOUT).decode()
        running = subprocess.check_output(
            ['docker', 'inspect', '--format', '{{.State.Running}}', name]).strip()
        if running != b'true':
            raise RuntimeError('Paper bot exited during startup:\n' + logs[-8000:])
        if "Changing state to: RUNNING" in logs and 'Bot heartbeat.' in logs:
            subprocess.run(['docker', 'exec', name, *service['healthcheck']['test'][1:]], check=True)
            subprocess.run(['docker', 'exec', name, 'python', '-c',
                "from pathlib import Path; assert Path('/freqtrade/user_data/tradesv3.paper.sqlite').is_file()"], check=True)
            print('PASS: isolated dry-run startup, RUNNING heartbeat, API health and SQLite creation')
            break
        time.sleep(2)
    else:
        raise RuntimeError('Startup timed out (check Binance reachability):\n' + logs[-8000:])
finally:
    subprocess.run(['docker', 'stop', '--time', '30', name], stdout=subprocess.DEVNULL, check=False)
    subprocess.run(['docker', 'rm', '--volumes', name], stdout=subprocess.DEVNULL, check=False)

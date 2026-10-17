"""Compile the independent EU profile via the real remote consumer path."""
import base64
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--config-only',action='store_true',help='Validate merged config before expensive builds; default still compiles firmware')
args=parser.parse_args()
class Loader(yaml.SafeLoader):
    pass
Loader.add_multi_constructor('!', lambda loader, tag, node:
    loader.construct_scalar(node) if isinstance(node,yaml.ScalarNode) else
    loader.construct_sequence(node) if isinstance(node,yaml.SequenceNode) else loader.construct_mapping(node))

with tempfile.TemporaryDirectory(prefix='standalone-consumer-') as temp:
    config=Path(temp)
    ref=os.environ.get('GITHUB_SHA','main')
    if ref!='main' and not re.fullmatch('[0-9a-f]{40}',ref):
        raise RuntimeError('Expected exact tested commit')
    text=(ROOT/'esphome/nspanel-alarm-standalone-example.yaml').read_text()
    text=text.replace('ref: main','ref: '+ref).replace(
        'http://homeassistant.local:8123/local/nspanel_alarm_eu.tft','http://example.invalid/clock.tft')
    path=config/'device.yaml'
    path.write_text(text)
    (config/'secrets.yaml').write_text(yaml.safe_dump(dict(
        wifi_ssid='CI_ONLY_NO_NETWORK',wifi_password='CI_ONLY_NO_PASSWORD',
        nspanel_api_encryption_key=base64.b64encode(hashlib.sha256(b'public test key').digest()).decode(),
        local_ntp_server='0.pool.ntp.org')))
    # Leave historical generic headers in place here too.
    (config/'alarm_schedule.h').write_bytes((ROOT/'tests/fixtures/alarm_schedule_v1.h').read_bytes())
    result=subprocess.run([sys.executable,'-m','esphome','config',str(path)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    sys.stderr.write(result.stderr)
    if result.returncode: print(result.stdout)
    result.check_returncode()
    merged=yaml.load(result.stdout,Loader=Loader)
    numbers={n['name']:n for n in merged['number']}
    assert all(n in numbers for n in ['Temperature Correction','Display Brightness Sleep',
        'Display Brightness Dimdown','Timeout Dimming','Timeout Sleep','Timeout Page'])
    sensors={n.get('name'):n for n in merged['sensor']}
    assert sensors['Temperature']['device_class']=='temperature'
    assert sensors['Temperature']['unit_of_measurement']=='°C'
    assert sensors['Temperature']['accuracy_decimals']==1
    adc=next(n for n in merged['sensor'] if str(n['id'])=='wa_ntc_voltage')
    assert adc['pin']['number']==38 and adc['samples']==16
    for entity in [adc,sensors['Temperature']]:
        heartbeat=next(f['heartbeat'] for f in entity['filters'] if 'heartbeat' in f)
        assert heartbeat['optimistic'] is True, 'Temperature must publish changes immediately, not wait five minutes'
    switches={n.get('name'):n for n in merged['switch']}
    assert 'Display Settings from Blueprint' in switches and 'Sound - Notification' in switches
    assert 'wa_notification_sound' in str(merged['api']['actions'])
    assert 'wa_notification_sound' not in str(next(n for n in merged['script'] if str(n['id'])=='wa_buzzer_loop'))
    assert 'external_components' not in merged and 'nspanel_easy' not in merged
    assert len(merged['display'])==1 and merged['display'][0]['platform']=='nextion'
    assert merged['api']['reboot_timeout']=='0s' and merged['wifi']['reboot_timeout']=='0s'
    assert merged['api']['encryption']['key']
    ota=[x for x in merged['ota'] if x['platform']=='esphome']
    assert len(ota)==1 and 'encryption' in ota[0] and 'password' not in ota[0]
    assert all(x['restore_mode']=='ALWAYS_OFF' for x in merged['switch'] if str(x['id']) in ['relay_1','relay_2'])
    assert 'release_all' in str(ota[0]['on_begin'])
    upload=next(x for x in merged['button'] if x.get('name')=='Alarm Clock Upload TFT')
    assert 'has_automatic_output' in str(upload['on_press'])
    for header in merged['esphome']['includes']:
        source=Path(header)
        assert source.parent != config and source.read_bytes()==(ROOT/'esphome'/source.name).read_bytes()
    assert 'esphome.nspanel_easy' not in str(merged)
    if args.config_only:
        print('Standalone remote consumer schema and merged configuration passed; full compilation remains a separate required step.')
        sys.exit(0)
    subprocess.run([sys.executable,'-m','esphome','compile',str(path)],check=True)
    flags=(config/'.esphome/build/nspanel-alarm-example/src/esphome/core/defines.h').read_text()
    assert '#define USE_OTA_ENCRYPTION_REQUIRED' in flags and '#define USE_OTA_PASSWORD' not in flags
    print('Standalone EU remote consumer build passed without Easy component/blueprint; encrypted OTA and safe relay defaults verified.')

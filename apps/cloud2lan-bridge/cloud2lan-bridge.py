import os
import configparser
import base64
import subprocess
import hashlib
import signal
import json
import paho.mqtt.client as mqtt
import urllib.parse
import time
import ssl
import uuid
import socket
import traceback
from datetime import datetime

LOG_DEBUG = 0
LOG_INFO = 1
LOG_WARNING = 2
LOG_ERROR = 3

LOG_LEVEL = LOG_DEBUG if not not os.getenv('DEBUG') else LOG_WARNING

def log(level, message):
    if level >= LOG_LEVEL:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + message, flush=True)

def md5(input_str: str) -> str:
    return hashlib.md5(input_str.encode('utf-8')).hexdigest()

def now() -> int:
    return round(time.time() * 1000)

# ==============================================================================
# DOCUMENTED CLOUD-TO-LAN TELEMETRY RELAY & CAMERA CORE ACTIVATOR
# ==============================================================================
class Program:
    cloud_config = None
    api_config = None
    firmware_version = None
    model_id = None
    cloud_device_id = None
    lan_device_id = None
    cloud_client = None
    lan_client = None

    def __init__(self):
        self.cloud_config, self.section_name = self.get_cloud_config()
        self.api_config = self.get_api_config()
        self.firmware_version = self.get_firmware_version()
        self.model_id = self.api_config['cloud']['modelId']
        self.cloud_device_id = self.cloud_config['deviceUnionId']
        self.lan_device_id = self.get_lan_device_id()
        self.area_code = self.get_area_code()

    def get_cloud_config(self):
        config = configparser.ConfigParser()
        config.read('/userdata/app/gk/config/device.ini')
        environment = config['device'].get('env', 'prod').strip()
        zone = config['device'].get('zone', 'global').strip().lower()
        if not zone:
            zone = 'global'
        
        section_name = f'cloud_{environment}' if (zone == 'cn' or zone == 'china') else f'cloud_{zone}_{environment}'
        
        # Robust fallback logic if section name doesn't match expected formats
        if section_name not in config:
            fallback = f'cloud_{environment}'
            if fallback in config:
                section_name = fallback
            else:
                fallback_global = f'cloud_global_{environment}'
                if fallback_global in config:
                    section_name = fallback_global
                    
        return config[section_name], section_name

    def get_area_code(self) -> str:
        if 'global' in self.section_name.lower():
            return "0xFFFFFFFF"  # AREA_CODE_GLOB
        return "1"  # AREA_CODE_CN

    def get_api_config(self):
        with open('/userdata/app/gk/config/api.cfg', 'r') as f:
            return json.loads(f.read())

    def get_ssl_context(self) -> ssl.SSLContext:
        cert_path = self.cloud_config['certPath']
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.set_ciphers(('ALL:@SECLEVEL=0'),)
        if cert_path:
            ssl_context.load_cert_chain(f'{cert_path}/deviceCrt', f'{cert_path}/devicePk', None)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        if os.path.exists(f'{cert_path}/caCrt'):
            ssl_context.load_verify_locations(f'{cert_path}/caCrt')
        return ssl_context

    def get_firmware_version(self) -> str:
        with open('/useremain/dev/version', 'r') as f: 
            return f.read().strip()

    def get_lan_device_id(self) -> str:
        with open('/useremain/dev/device_id', 'r') as f: 
            return f.read().strip()

    def get_cloud_mqtt_credentials(self):
        device_key = self.cloud_config['deviceKey']
        cert_path = self.cloud_config['certPath']
        command = f'printf "{device_key}" | openssl rsautl -encrypt -inkey {cert_path}/caCrt -certin -pkcs | base64 -w 0'
        encrypted_device_key = subprocess.check_output(['sh', '-c', command]).decode('utf-8').strip()
        taco = f'{self.cloud_device_id}{encrypted_device_key}{self.cloud_device_id}'
        return (f'dev|fdm|{self.model_id}|{md5(taco)}', encrypted_device_key)

    def get_lan_mqtt_credentials(self):
        with open('/userdata/app/gk/config/device_account.json', 'r') as f:
            data = json.loads(f.read())
        return (data['username'], data['password'])

    def send_message(self, client, topic, payload):
        mode = 'cloud' if client == self.cloud_client else 'lan'
        log(LOG_DEBUG, f'[{mode}] Sent {topic} = {str(payload)}')
        client.publish(topic, json.dumps(payload))

    def on_cloud_message(self, topic, payload):
        log(LOG_DEBUG, f'[cloud] Received {topic} = {str(payload)}')
        
        # Enforce exact match against the documented server capture schema
        if isinstance(payload, dict) and payload.get('action') == 'startCapture':
            shengwang_data = payload.get('data', {}).get('shengwang', {})
            
            # Logic guard check: ignore simple trailing heartbeat acknowledgments
            if not shengwang_data:
                log(LOG_DEBUG, "[ROUTER] Dropping join status message echo.")
            else:
                log(LOG_INFO, "[ROUTER] Intercepted stream request payload. Passing core configuration signals down...")
                try:
                    # Map the local execution profile structure directly to the specified local network target 
                    local_video_payload = {
                        "type": "video",
                        "action": "startCapture",
                        "timestamp": now(),
                        "msgid": str(payload.get('msgid', uuid.uuid4())),
                        "data": None
                    }
                    
                    # Target the verified local layout structure specification explicitly
                    self.send_message(
                        self.lan_client, 
                        f"anycubic/anycubicCloud/v1/web/printer/20025/{self.lan_device_id}/video", 
                        local_video_payload
                    )
                    log(LOG_INFO, "[ROUTER] Dispatched internal camera sensor activation safely.")
                except Exception as e:
                    log(LOG_ERROR, f"[ROUTER] Internal camera bootstrap call failed: {str(e)}")

        if not topic.endswith('/response'):
            self.send_message(self.lan_client, topic.replace(self.cloud_device_id, self.lan_device_id), payload)

    def on_lan_message(self, topic, payload):
        log(LOG_DEBUG, f'[lan] Received {topic} = {str(payload)}')
        
        # Intercept the exact core info schema structure array specified by Rinkhals documentation
        if topic.endswith('/info/report') and isinstance(payload, dict):
            data_block = payload.get('data', {})
            if data_block and 'urls' in data_block:
                log(LOG_INFO, "[ROUTER] Patching video endpoint configuration mappings within system query packet.")
                # Force update the internal server URLs variable parameters precisely as stated in the notes
                local_ip = data_block.get('ip', '127.0.0.1')
                data_block['urls']['rtspUrl'] = f"http://{local_ip}:18088/flv"

        if topic.endswith('/report') or topic.endswith('/response'):
            self.send_message(self.cloud_client, topic.replace(self.lan_device_id, self.cloud_device_id), payload)

    def connect_cloud_mqtt(self):
        mqtt_broker = self.cloud_config['mqttBroker']
        mqtt_username, mqtt_password = self.get_cloud_mqtt_credentials()
        
        def mqtt_on_connect(client, userdata, connect_flags, reason_code, properties):
            log(LOG_INFO, '[cloud] Handshake established with upstream cluster endpoint.')
            self.cloud_client.subscribe(f'anycubic/anycubicCloud/v1/+/printer/{self.model_id}/{self.cloud_device_id}/#')
            
        def mqtt_on_message(client, userdata, msg):
            self.on_cloud_message(msg.topic, json.loads(msg.payload.decode("utf-8")))

        self.cloud_client = mqtt.Client(protocol=mqtt.MQTTv5, client_id=self.cloud_device_id)
        if urllib.parse.urlparse(mqtt_broker).scheme == 'ssl':
            self.cloud_client.tls_set_context(self.get_ssl_context())
            self.cloud_client.tls_insecure_set(True)
        self.cloud_client.on_connect = mqtt_on_connect
        self.cloud_client.on_message = mqtt_on_message
        self.cloud_client.username_pw_set(mqtt_username, mqtt_password)
        self.cloud_client.connect(
            urllib.parse.urlparse(mqtt_broker).hostname, 
            urllib.parse.urlparse(mqtt_broker).port or 1883
        )
        self.cloud_client.loop_start()

    def main(self):
        # Setup signal handler to ensure finally block runs on SIGTERM/SIGINT
        def sig_handler(signum, frame):
            log(LOG_INFO, f"[SYSTEM] Received signal {signum}, exiting...")
            raise SystemExit(0)
            
        signal.signal(signal.SIGTERM, sig_handler)
        signal.signal(signal.SIGINT, sig_handler)

        self.connect_cloud_mqtt()
        
        mqtt_username, mqtt_password = self.get_lan_mqtt_credentials()
        
        def mqtt_on_connect(client, userdata, connect_flags, reason_code, properties):
            log(LOG_INFO, '[lan] Handshake established with localized host execution loop.')
            self.lan_client.subscribe(f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.lan_device_id}/#')
            
            for rtype, raction in [('lastWill', 'onlineReport'), ('status', 'workReport')]:
                self.send_message(
                    self.cloud_client, 
                    f'anycubic/anycubicCloud/v1/printer/public/{self.model_id}/{self.cloud_device_id}/{rtype}/report', 
                    {
                        'type': rtype, 'action': raction, 'timestamp': now(), 
                        'msgid': str(uuid.uuid4()), 'state': 'online' if rtype=='lastWill' else 'free', 
                        'code': 200, 'msg': '', 'data': None
                    }
                )
            
        def mqtt_on_message(client, userdata, msg):
            self.on_lan_message(msg.topic, json.loads(msg.payload.decode("utf-8")))

        self.lan_client = mqtt.Client(protocol=mqtt.MQTTv5, client_id=self.lan_device_id)
        self.lan_client.tls_set_context(self.get_ssl_context())
        self.lan_client.tls_insecure_set(True)
        self.lan_client.on_connect = mqtt_on_connect
        self.lan_client.on_message = mqtt_on_message
        self.lan_client.username_pw_set(mqtt_username, mqtt_password)
        
        self.lan_client.connect('127.0.0.1', 9883)

        # Start auto_stream.sh in the background with AGORA_AREA_CODE environment variable
        script_dir = os.path.dirname(os.path.realpath(__file__))
        auto_stream_path = os.path.join(script_dir, 'auto_stream.sh')
        log(LOG_INFO, f"[SYSTEM] Launching {auto_stream_path} with AGORA_AREA_CODE={self.area_code}...")
        self.auto_stream_proc = None
        try:
            env = os.environ.copy()
            env['AGORA_AREA_CODE'] = self.area_code
            self.auto_stream_proc = subprocess.Popen(
                ['/bin/sh', auto_stream_path],
                cwd=script_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log(LOG_INFO, f"[SYSTEM] auto_stream.sh started with PID {self.auto_stream_proc.pid}")
        except Exception as e:
            log(LOG_ERROR, f"[SYSTEM] Failed to start auto_stream.sh: {str(e)}")

        try:
            self.lan_client.loop_forever()
        finally:
            if self.auto_stream_proc:
                log(LOG_INFO, "[SYSTEM] Terminating auto_stream.sh process...")
                self.auto_stream_proc.terminate()
                try:
                    self.auto_stream_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    log(LOG_WARNING, "[SYSTEM] auto_stream.sh did not terminate. Killing it...")
                    self.auto_stream_proc.kill()

if __name__ == "__main__":
    program = None
    try:
        program = Program()
        program.main()
    except Exception as e:
        log(LOG_ERROR, traceback.format_exc())
        if program and hasattr(program, 'auto_stream_proc') and program.auto_stream_proc:
            log(LOG_INFO, "[SYSTEM] Exception cleanup: Terminating auto_stream.sh...")
            program.auto_stream_proc.terminate()
            try:
                program.auto_stream_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                program.auto_stream_proc.kill()
        os.kill(os.getpid(), 9)
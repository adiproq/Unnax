from flask import Flask, request, redirect, render_template, jsonify
import requests
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import uuid


app = Flask(__name__)

# Configuración de las credenciales y endpoints
API_ID = "at1475"
REFRESH_TOKEN = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkaXByb3NwZXJvcUBnbWFpbC5jb20iLCJtZXJjaGFudF9pZCI6MTM4MywibmJmIjoxNzIzNzYxMTkwLCJpYXQiOjE3MjM3NjExOTAsImV4cCI6MTcyMzg0NzU5MCwianRpIjoiMmtpS3ZwQngwWmRsNTR5aFhSRkRxdTduamV1IiwiaXNzIjoiYXV0aC51bm5heC5jb20ifQ.vxvm16WH-Efu1QTHur2fZ9qn4XWPMqhbN-aVFAw-1qsYQ4SfOzVOhVa4TeyKcHUvyUfhQGqXvsZE0KRDWoIgnY8y9IWtOVgnrPr355vHqlxXD8PGU95XO6My4Dvu0UUaPUVEeuMl3KJJSM6YsPuiYAGUp2_KXias13LXlyJ0_oN-4QzJcAQ6gYJoJQ204NX5v3mfPkyTg4-zvZccBL0vr6frsf4U3QpYrx3UlzudTxgUVklPCkwCoCPFgDW94PRnKj5fsiaooQxq955QsxLLOJzsQ4f5XnhQHSQiAyUhMVV8uhRnBl7fOr1mEjWQ4UbuhRy79O1G2WW82I-zVPJ5AyavkCFlO-_PV_n6k0T00O5fQRHPhXVcvVsNQQb1Ke_jKeTIIQHlu96BdZIcnaw3TrHbsQG00mYncq51lHCUfXBce76lm-p08JShLUsslBMnkGlVzM2va4JABd94GZ6HUZeQIr21kN1Cc0J6xNMmSVtyGPOvx_tyR8UuFYmQ9poBy0Tg_tCLgeyX17gRf81HWTlH6GwkL7ROXoktt8BwRU1hgZ1aJY_3HEiLFMkj3mcX_kxbgX9o5_dJl9Yw0Y1KeiGe-R-FKXGy4K9Z2eFSHfQ3gd4s2GtTP6u3t7TKL1KMNpQB4ehQoWc8atffx8Q1N8LNZlo_UHQizLpyfu-J0V0"
WEBHOOK_URL = "https://0558-83-53-95-51.ngrok-free.app/webhook"  # Cambia esto al dominio donde recibirás los webhooks
UNNAX_API_URL = "https://integration.unnax.com/api/v3"
ACCESS_TOKEN = None

def log(message):
    print(message, file=sys.stderr, flush=True)

def get_access_token():
    global ACCESS_TOKEN
    log("Obteniendo el token de acceso...")
    url = f'{UNNAX_API_URL}/auth/jwt_token/refresh'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'refresh': REFRESH_TOKEN,
    }
    response = requests.post(url, json=data, headers=headers)
    ACCESS_TOKEN = response.json().get('access')
    log(f"Token de acceso obtenido: {ACCESS_TOKEN}")

def configure_webhooks():
    log("Configurando webhooks...")
    events = [
        "event_fitnance_start",
        "event_consent_signed",
        "event_aggregation_login",
        "event_reader_lockstep_complete",
        "event_reader_lockstep_cancelled",
        "event_credential_token_creation",
        "event_credential_token_login",
        "event_aggregation_status",
        "fitnance_read"
    ]
    
    for event in events:
        url = f"{UNNAX_API_URL}/webhooks"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        payload = {
            "client": "callback",
            "target": WEBHOOK_URL,
            "event": event
        }
        response = requests.post(url, headers=headers, json=payload)
        log(f"Webhook {event} configurado con estado {response.status_code}: {response.text}")

def decrypt_data(data, key, iv):
    padding_char = b'$'
    size = 16
    
    key = key.ljust(size, padding_char)[:size]
    iv = iv.ljust(size, padding_char)[:size]
    
    decoded_data = base64.b64decode(data)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted_data = decryptor.update(decoded_data) + decryptor.finalize()
    
    return decrypted_data.rstrip(padding_char).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_aggregation', methods=['POST'])
def start_aggregation():
    log("Iniciando el proceso de agregación bancaria...")
    url = f"{UNNAX_API_URL}/reader/lockstep/init"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    payload = {
        "request_code": str(uuid.uuid4()),
        "tokenization_request": False,
        "read_customers": True,
        "read_accounts": True,
        "read_account_statements": True,
        "read_cards": True,
        "read_card_statements": True,
        "read_loans": True,
        "read_n19_files": True,
        "read_n43_files": True,
        "single_bank": False,
        "all_banks": True
    }
    response = requests.post(url, headers=headers, json=payload)
    log(f"Respuesta de la API de Unnax: {response.status_code}, {response.text}")

    if response.status_code == 200:
        widget_url = response.json().get('widget_url')
        log(f"Redirigiendo al usuario al widget: {widget_url}")
        return redirect(widget_url)
    else:
        return jsonify({"error": "Error al iniciar la agregación bancaria"}), response.status_code

@app.route('/webhook', methods=['POST'])
def webhook():
    log(f"Webhook{request.json}")
    body = request.json
    triggered_event = body.get('triggered_event')
    log(f"Webhook recibido para evento: {triggered_event}")

    if triggered_event == 'fitnance_read':
        encrypted_data = body.get('data')
        key = "dwsgyfjtaslyiypydxquunhkrzhxghjm"
        iv = "at1475"
        try:
            decrypted_content = decrypt_data(encrypted_data, key.encode(), iv.encode())
            log(f"Datos desencriptados: {decrypted_content}")
        except Exception as e:
            log(f"Error desencriptando los datos: {e}")
    
    return "OK", 200

if __name__ == '__main__':
    get_access_token()  # Obtener el token de acceso al iniciar la aplicación
    configure_webhooks()  # Configurar los webhooks necesarios
    app.run(debug=True, host='0.0.0.0', port=5000)
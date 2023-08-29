from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from functools import wraps
import json
from keycloak import KeycloakOpenID
import os

with open('transaction.json', 'r') as f:
    data = json.load(f)

api = Flask(__name__)

load_dotenv()

api.config['KEYCLOAK_REALM'] = os.getenv('KEYCLOAK_REALM')
api.config['KEYCLOAK_URL'] = os.getenv('KEYCLOAK_URL')
api.config['KEYCLOAK_CLIENT_ID'] = os.getenv('KEYCLOAK_CLIENT_ID')
api.config['KEYCLOAK_CLIENT_SECRET'] = os.getenv('KEYCLOAK_CLIENT_SECRET')
api.config['KEYCLOAK_USERNAME'] = os.getenv('KEYCLOAK_USERNAME')
api.config['KEYCLOAK_PASSWORD'] = os.getenv('KEYCLOAK_PASSWORD')

keycloak_openid = KeycloakOpenID(
    server_url = api.config["KEYCLOAK_URL"],
    realm_name = api.config['KEYCLOAK_REALM'],
    client_id = api.config['KEYCLOAK_CLIENT_ID'],
    client_secret_key = api.config['KEYCLOAK_CLIENT_SECRET']
)

access_token = keycloak_openid.token(
    grant_type='client_credentials',
    client_id=api.config['KEYCLOAK_CLIENT_ID'],
    client_secret_key=api.config['KEYCLOAK_CLIENT_SECRET']
)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            token_info = keycloak_openid.introspect(token)
            current_user = token_info['username']
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@api.route('/')
def documentation():
    return render_template('index.html')

@api.route('/v1/transactions/protected')
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello {current_user}!'})

@api.route('/v1/transactions/auth', methods=['GET'])
def get_token():
    try:
        username = request.args.get('username')
        password = request.args.get('password')
        token = keycloak_openid.token(username, password)
        if token:
            return jsonify(token["access_token"])
    except Exception:
        return jsonify({
            "Message": "Incorrect username or password"
        }), 401

@api.route('/v1/transactions', methods=['GET'])
@token_required
def get_all_transactions(current_user):
    return jsonify(data)

@api.route('/v1/transactions/id', methods=['GET'])
@token_required
def get_transaction_by_id(current_user):
    id = request.args.get('id')
    for transaction in data:
        if transaction['transaction_id'] == id:
            return jsonify(transaction)
    return jsonify({
        'Message': 'Transaction not found'
    })

@api.route('/v1/transactions', methods=['POST'])
@token_required
def post_new_transaction(current_user):
    new_transaction = request.get_json()
    data.append(new_transaction)

    return jsonify({
        "Message": "Transaction has been posted"
    })

@api.route('/v1/transactions/id', methods=['DELETE'])
@token_required
def delete_transaction_by_id(current_user):
    id = request.args.get('id')
    for transaction in data:
        if transaction['transaction_id'] == id:
            data.remove(transaction)
            return jsonify({
                'Message': f"Transaction {id} has been deleted."
            })
        
    return jsonify({
        'Message': 'Transaction not found'
    })


if __name__ == '__main__':
    api.run(debug=True, host='0.0.0.0', port=5000)
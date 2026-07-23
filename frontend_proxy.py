#!/usr/bin/env python3
from flask import Flask, request, Response, send_from_directory
import requests
import os

app = Flask(__name__)
STATIC_DIR = "/var/www/html/bidding"
API_URL = "http://127.0.0.1:8090"

@app.route('/bidding/api/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def proxy_api(path):
    url = f"{API_URL}/{path}"
    headers = {k: v for k, v in request.headers if k.lower() != 'host'}
    if request.method == 'OPTIONS':
        resp = Response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp
    if request.method == 'GET':
        r = requests.get(url, headers=headers, params=request.args)
    else:
        r = requests.post(url, headers=headers, json=request.get_json())
    resp = Response(r.content, status=r.status_code)
    for k, v in r.headers.items():
        if k.lower() not in ['transfer-encoding', 'connection']:
            resp.headers[k] = v
    return resp

@app.route('/bidding/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)

@app.route('/bidding/')
def serve_index():
    return send_from_directory(STATIC_DIR, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
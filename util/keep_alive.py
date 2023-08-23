from threading import Thread

from flask import Flask
from waitress import serve

app = Flask(__name__)

@app.route('/')
def main():
	return '<h1>KEEP DISCORD BOT ALIVE<h1>'

def run():
    serve(app, host="0.0.0.0", port=8080, _quiet=True)

def keep_alive():
    server = Thread(target=run)
    server.start()
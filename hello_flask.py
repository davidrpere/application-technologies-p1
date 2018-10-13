from flask import Flask, render_template
from flask import request, jsonify, send_file
import requests
import client_interface
from multiprocessing import Value, Array
import aws_wrapper
import logging
from utils import Constants, Command

# users = Array(client_interface, 1, True)

# App config.
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441f2b6176a'

users = {}
messages = {}
downloads = {}


@app.route("/send", methods=["POST"])
def upload():
    print('User identity is ' + str(request.json['identity']))
    for key in users.keys():
        print('Key is ' + str(key))
    users[request.json['identity']].send_message(request.json['message'])
    return ''


@app.route("/download", methods=['GET'])
def query_download():
    print('User identity is ' + str(request.json['identity']) + ", begin chat")
    user = users[int(request.json['identity'])]
    url = user.s3_link
    print(url)
    r = requests.get(url)
    with app.open_instance_resource('downloaded_file', 'wb') as f:
        f.write(r.content)
    return send_file('downloaded_file')
    # return render_template('download.html');


@app.route("/end-chat", methods=['POST'])
def end_chat():
    # print(request.json)
    print('User identity is ' + str(request.json['identity']) + ", end chat")
    user = users[int(request.json['identity'])]
    user.send_message("END")
    return 'ok'


def received_message(message):
    print('Received message : ' + message['Body'])
    command = message['MessageAttributes']['Command']['StringValue']
    addressee = message['MessageAttributes']['Addressee']['StringValue']
    if command == Command.ECHO_REPLY.value:
        try:
            messages_user = messages[int(addressee)]
        except KeyError:
            messages_user = []
        messages_user.append(message['Body'])
        messages[int(addressee)] = messages_user
        # print('Appendo to messages['+str(addressee)+'] value '+message['Body'])
    elif command == Command.DOWNLOAD_URL_REPLY.value:
        downloads_user = messages['Body']
        downloads[int(addressee)] = downloads_user


@app.route('/_update', methods=['GET'])
def stuff():
    user_identity = request.values['identity']
    print('User identity is ' + str(user_identity))
    try:
        messages_user = messages[int(user_identity)]
        messages.pop(int(user_identity))
        print('Going to send something...')
        return jsonify(messages=messages_user)
    except KeyError:
        print('Not sending anything...')
        logging.info('No new messages for user ' + str(user_identity))
        return jsonify(messages='')


@app.route("/begin-chat", methods=['POST'])
def begin_chat():
    # print(request.json)
    print('User identity is ' + str(request.json['identity']) + ", begin chat")
    user = users[request.json['identity']]
    user.begin_chat()
    return 'ok'


@app.route("/", methods=['GET', 'POST'])
def index():
    sqs_manager = aws_wrapper.SqsManager()
    user = client_interface.SqsClientInterface(sqs_manager)
    user._sqs_manager.bind_to(received_message)
    user.daemon = True
    user.start()
    users[user._identity] = user
    return render_template('index.html', identity=user._identity)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, render_template, json, request, jsonify
from utils import Command
import client_interface
import aws_wrapper
import logging
import time


# App config.
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441f2b6176a'

users = {}
messages = {}


@app.route("/send", methods=["POST"])
def upload():
    print('User identity is ' + str(request.json['identity']))
    for key in users.keys():
        print('Key is ' + str(key))
    users[request.json['identity']].send_message(request.json['message'])
    return ''


@app.route("/download", methods=['GET'])
def query_download():
    user = users[int(request.values['identity'])]
    url = user.s3_link
    reply_url = {'url': url}
    return json.dumps(reply_url)


@app.route("/end-chat", methods=['POST'])
def end_chat():
    print(request.json)
    print('User identity is ' + str(request.json['identity']) + ", end chat")
    user = users[int(request.json['identity'])]
    user.send_message("END")
    time.sleep(2)
    user.upload_s3()
    return 'ok'


def received_message(message):
    logging.info('Received message : ' + str(message['Body']))
    command = str(message['MessageAttributes']['Command']['StringValue'])
    addressee = str(message['MessageAttributes']['Addressee']['StringValue'])
    if command == Command.ECHO_REPLY.value:
        try:
            messages_user = messages[int(addressee)]
        except KeyError:
            messages_user = []
        messages_user.append(message['Body'])
        messages[int(addressee)] = messages_user
    elif command == Command.DOWNLOAD_URL_REPLY.value:
        logging.info('Updated s3 link for user ' + str(addressee))


@app.route('/_update', methods=['GET'])
def stuff():
    user_identity = request.values['identity']
    try:
        logging.info('Updating chat for user ' + str(user_identity))
        messages_user = messages[int(user_identity)]
        messages.pop(int(user_identity))
        return jsonify(messages=messages_user)
    except KeyError:
        logging.info('No new messages for user ' + str(user_identity))
        return jsonify(messages='')


@app.route("/begin-chat", methods=['POST'])
def begin_chat():
    logging.info('User identity is ' + str(request.json['identity']) + ", begin chat")
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

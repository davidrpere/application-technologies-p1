from flask import Flask, render_template, json, request, jsonify
from utils import Command
import client_interface
import aws_wrapper
import logging
import time


DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441f2b6176a'

users = {}
messages = {}


@app.route("/send", methods=["POST"])
def upload():
    """ Handles a POST request to /send

    Sends a message with the content sent by the user.
    """
    try:
        logging.info('User identity is ' + str(request.json['identity']))
        for key in users.keys():
            logging.info('Key is ' + str(key))
        users[request.json['identity']].send_message(request.json['message'])
        return ''
    except KeyError:
        logging.warning('Wrong user identity.')


@app.route("/download", methods=['GET'])
def query_download():
    """ Handles a GET request to /download

    Returns a json with the URL which is handled in JavaScript.
    """
    try:
        user = users[int(request.values['identity'])]
        url = user.s3_link
        reply_url = {'url': url}
        return json.dumps(reply_url)
    except KeyError:
        logging.warning('Wrong user identity.')


@app.route("/end-chat", methods=['POST'])
def end_chat():
    """ Handles a POST request to /end-chat
    """
    logging.debug(request.json)
    logging.info('User identity is ' + str(request.json['identity']) + ", end chat")
    try:
        user = users[int(request.json['identity'])]
        user.send_message("END")
        time.sleep(2)
        user.upload_s3()
    except KeyError:
        logging.warning('Wrong user identity.')
    return 'ok'


@app.route('/_update', methods=['GET'])
def update():
    """ Handles a GET request to /_update
    """
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
    """ Handles a POST request to /begin-chat
    """
    logging.info('User identity is ' + str(request.json['identity']) + ", begin chat")
    user = users[request.json['identity']]
    user.begin_chat()
    return 'ok'


@app.route("/", methods=['GET', 'POST'])
def index():
    """ Handles a GET/POST request to /
    """
    sqs_manager = aws_wrapper.SqsManager()
    user = client_interface.SqsClientInterface(sqs_manager)
    user._sqs_manager.bind_to(received_message)
    user.daemon = True
    user.start()
    users[user._identity] = user
    return render_template('index.html', identity=user._identity)


def received_message(message):
    """ Callback for the reception of messages in the messaging interface.

    :param message: Received message.
    """
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
    else:
        logging.warning('User ' + str(addressee) + ' received wrong command ' + str(command))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

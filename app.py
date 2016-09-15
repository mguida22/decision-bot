import json, os, random, re, sys

import nltk, requests
from flask import Flask, abort, request
from dotenv import load_dotenv


HUMANIZE_REGEX = re.compile(r'\s+?([,.?!\'\"])')

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

# load up our responses
with open('data.json', encoding='utf-8') as f:
    data = json.loads(f.read())

RESPONSES = data["responses"]
STOP_CODES = data["stop_codes"]
START_CODES = data["start_codes"]
FAILURE_RESPONSES = data["failure_responses"]

def humanize_list(l):
    l = " ".join(l)
    l = HUMANIZE_REGEX.sub(r'\1', l)
    return l

def decide(question):
    tokens = nltk.word_tokenize(question)
    pos_list = nltk.pos_tag(tokens)

    # pull out each option from the question
    potential_options = []
    current_option = []
    started = False
    for token in pos_list:
        if started:
            if token[1] in STOP_CODES:
                potential_options.append(current_option)
                current_option = []
                started = False
            else:
                current_option.append(token[0])
        else:
            if token[1] in START_CODES:
                current_option.append(token[0])
                started = True

    # handle the case of no options
    if len(potential_options) == 0:
        rand_index = random.randint(0, len(FAILURE_RESPONSES) - 1)
        return FAILURE_RESPONSES[rand_index]

    # choose one option at random
    rand_index = random.randint(0, len(potential_options) - 1)
    chosen_option = humanize_list(potential_options[rand_index])

    # pull a random response template and fill in the chosen option
    rand_index = random.randint(0, len(RESPONSES) - 1)
    response = RESPONSES[rand_index].format(chosen_option)

    return response

def reply(recipient_id, msg):
    params = {
        'access_token': os.environ.get('FB_ACCESS_TOKEN')
    }
    headers = {
        'Content-type': 'application/json'
    }
    data = json.dumps({
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': msg
        }
    })

    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params = params,
                      headers = headers,
                      data = data)
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)

@app.route('/')
def hello_world():
    return 'Hello, world!'

@app.route('/webhook', methods = ['GET'])
def auth():
    # Authenticate with Facebook
    if request.args.get('hub.verify_token') == os.environ.get('FB_VERIFY_TOKEN'):
        return request.args.get('hub.challenge')
    else:
        return abort(403)

@app.route('/webhook', methods = ['POST'])
def webhook():
    data = request.get_json()

    if os.environ.get("ENV") != "production":
        print(data)

    for entry in data["entry"]:
        for message_evt in entry["messaging"]:
            if message_evt.get("message"):
                sender_id = message_evt["sender"]["id"]
                recipient_id = message_evt["recipient"]["id"]
                message_text = message_evt["message"]["text"]

                reply(sender_id, decide(message_text))

    return 200

@app.route('/test')
def test():
    if os.environ.get("ENV") == "production":
        return abort(404)

    if request.args.get('q'):
        return decide(request.args.get('q'))
    else:
        return abort(400)

if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(host='127.0.0.1', port=port)

from flask import Flask, request
from pymongo import MongoClient
from uuid import uuid4
import requests
import json
import io
import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN = os.getenv('ADMIN')
GROUP = os.getenv('GROUP')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
AUTHORIZED_USER_IDS = list(map(int, os.getenv('AUTHORIZED_USER_IDS').split(',')))
# global last_update_id
# only for testing 👆

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_webhook():
    try:
        process(json.loads(request.get_data()))
        return 'Success!'
    except Exception as e:
        print(e)
        return 'Error'

def testing():
    global last_update_id
    last_update_id = -1
    while True:
        updates = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id}").json().get('result', [])
        for update in updates:
            process(update)
            last_update_id = update['update_id'] + 1

def process(update):
    if 'message' in update:
        print(update)
        if update['message']['from']['id'] not in AUTHORIZED_USER_IDS:
            return
        if 'text' in update['message']:
            if update['message']['text'] == '/manual':
                manual(update['message']['from']['id'])
            elif update['message']['text'] == '/voices':
                callback(update['message']['from']['id'], 0, 0)
            elif 'reply_to_message' in update['message'] and 'voice' in update['message']['reply_to_message'] and update['message']['chat']['type'] == 'private':
                record = {
                    "file_id": update['message']['reply_to_message']['voice']['file_id'],
                    "number": 0,
                    "name": update['message']['from']['first_name'].split()[0],
                    "description": update['message']['text']
                }
                database_insert(record)
    elif 'inline_query' in update:
        if update['inline_query']['from']['id'] not in AUTHORIZED_USER_IDS:
            results = [{'type': 'article','title': "Access denied!",'input_message_content': {'message_text': "*Contact* ➡️ @boot\_to\_root",'parse_mode': 'Markdown'}}]
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerInlineQuery", data={'inline_query_id': update['inline_query']['id'],'results': json.dumps(results)})
            return
        matches = database_search(update['inline_query']['query'].lower(), 1)
        offset = int(update['inline_query']['offset']) if update['inline_query']['offset'] and update['inline_query']['offset'] != 'null' else 0
        next_offset = str(offset + 20) if offset + 20 < len(matches) else ''
        results = []
        for result in matches[offset:offset + 20]:
            results.append({'id': str(uuid4()),'voice_file_id': result["file_id"],'title': result["description"],'type': 'voice'})
        print(requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerInlineQuery", json={'inline_query_id': update['inline_query']['id'],'results': results,'next_offset': next_offset, 'cache_time': 20}, headers={'Content-Type': 'application/json'}).json())
    else:
        print(update['callback_query']['data'])
        if update['callback_query']['data'].isdigit():
            callback(update['callback_query']['from']['id'], int(update['callback_query']['data']), update['callback_query']['message']['message_id'])
        else:
            matched = database_search(update['callback_query']['data'], 2)
            print(requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",json={'chat_id': update['callback_query']['from']['id'], 'voice': matched['file_id']}).json())

def callback(user_id, limit, state):
    voices = database_search(0, 3)
    reply_markup = {'inline_keyboard' : [[{'text': "######################", 'callback_data': 'xay'}]]}
    counter = 0
    for voice in voices:
        if counter >= limit and counter < limit + 10:
            reply_markup['inline_keyboard'].append([{'text': voice["description"], 'callback_data': voice["description"]}])
            counter = counter + 1
        elif counter < limit:
            counter = counter + 1
        else:
            break
    if len(reply_markup['inline_keyboard']) == 1:
        print(requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',json={'chat_id': user_id, 'text': 'That was all in my database!'}).json())
        return
    else:
        del reply_markup['inline_keyboard'][0]
    if limit == 0:
        reply_markup['inline_keyboard'].append([{'text': f"▶️️️", 'callback_data': f"{limit + 10}"}])
    elif len(reply_markup['inline_keyboard']) < 10:
        reply_markup['inline_keyboard'].append([{'text': f"◀️", 'callback_data': f"{limit - 10}"}])
    else:
        reply_markup['inline_keyboard'].append([{'text': f"◀️", 'callback_data': f"{limit - 10}"}, {'text': f"▶️️️", 'callback_data': f"{limit + 10}"}])
    if state == 0:
        print(requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={'chat_id': user_id, 'text': 'Choose:','reply_markup': reply_markup}).json())
    else:
        print(requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup', json={'chat_id': user_id, "message_id": state, 'reply_markup': reply_markup}).json())

def manual(user_id):
    print(requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/copyMessage',data={'chat_id': user_id, 'from_chat_id': ADMIN,'message_id': 2502}))

def database_search(id, state):
    connection_string = f"mongodb+srv://{USERNAME}:" + PASSWORD + "@cluster0.a0mvghx.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(connection_string)
    db = client['guys_voice']
    collection = db['voices']
    if state == 1:
        return list(collection.find({"file_id": {"$regex": id, "$options": "i"}}).sort("number"))
    elif state == 2:
        return collection.find_one({"description": id})
    else:
        return list(collection.find())

def database_insert(record):
    connection_string = f"mongodb+srv://{USERNAME}:" + PASSWORD + "@cluster0.a0mvghx.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(connection_string)
    db = client['guys_voice']
    collection = db['voices']
    collection.insert_one(record)


if __name__ == '__main__':
    #testing()
    app.run(debug=False)

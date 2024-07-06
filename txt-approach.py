from flask import Flask, request
from uuid import uuid4
import requests
import base64
import json
import io
import os

GIT_NAME = 'my-github-account' # Change it
REPO_NAME = "my-repository" # Change it
BOT_TOKEN = os.getenv('BOT_TOKEN')
GIT_TOKEN = os.getenv('GIT_TOKEN')
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
        if update['message']['from']['id'] not in AUTHORIZED_USER_IDS:
            return
        if 'text' in update['message']:
            if update['message']['text'] == '/manual':
                manual(update['message']['from']['id'])
            elif update['message']['text'] == '/voices':
                callback(update['message']['from']['id'], 0, 0)
            elif update['message']['text'] == '/VOICES' and update['message']['from']['id'] == ADMIN:
                send_voices()
            elif update['message']['text'] == '/FILE' and update['message']['from']['id'] == ADMIN:
                voice()
            elif 'reply_to_message' in update['message'] and 'voice' in update['message']['reply_to_message'] and update['message']['chat']['type'] == 'private':
                with open('voices.txt', 'r') as file:
                    lines = file.readlines()
                    updated_lines = [line for line in lines if update['message']['reply_to_message']['voice']['file_id'] not in line]
                with open('voices.txt', 'w') as file:
                    file.write(f"{update['message']['reply_to_message']['voice']['file_id']} {0} {update['message']['from']['first_name'].split()[0]} {update['message']['text']}\n")
                    file.writelines(updated_lines)
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={'chat_id': update['message']['from']['id'],'text': '*Done!*', 'parse_mode': 'Markdown'})
                git_update('voices.txt')
    elif 'inline_query' in update:
        if update['inline_query']['from']['id'] not in AUTHORIZED_USER_IDS:
            results = [{'type': 'article','title': "Access denied!",'input_message_content': {'message_text': "*Contact* ➡️ @boot\_to\_root",'parse_mode': 'Markdown'}}]
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerInlineQuery", data={'inline_query_id': update['inline_query']['id'],'results': json.dumps(results)})
            return
        with open('voices.txt', 'r') as file:
            lines = file.readlines()
        voices = [line for line in lines if update['inline_query']['query'].lower() in ' '.join(line.split()[3:]).lower()]
        filtered_voices = sorted(voices, key=lambda line: int(line.split()[1]), reverse=True)
        offset = int(update['inline_query']['offset']) if update['inline_query']['offset'] and update['inline_query']['offset'] != 'null' else 0
        next_offset = str(offset + 20) if offset + 20 < len(lines) else ''
        results = []
        for line in filtered_voices[offset:offset + 20]:
            results.append({'id': str(uuid4()),'voice_file_id': line.split()[0],'title': ' '.join(line.split()[3:]),'type': 'voice',})
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerInlineQuery", json={'inline_query_id': update['inline_query']['id'],'results': results,'next_offset': next_offset, 'cache_time': 20}, headers={'Content-Type': 'application/json'})
    else:
        if update['callback_query']['data'].isdigit():
            callback(update['callback_query']['from']['id'], int(update['callback_query']['data']), update['callback_query']['message']['message_id'])
        else:
            with open('voices.txt', 'r') as file:
                voices1 = file.readlines()
            for voice1 in voices1:
                if ' '.join(voice1.split()[3:]) == update['callback_query']['data']:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",json={'chat_id': update['callback_query']['from']['id'], 'voice': voice1.split()[0]})

def callback(user_id, limit, state):
    with open('voices.txt', 'r') as file:
        lines = file.readlines()
    reply_markup = {'inline_keyboard' : [[{'text': "######################", 'callback_data': 'xay'}]]}
    counter = 0
    for line in lines:
        if counter >= limit and counter < limit + 10:
            reply_markup['inline_keyboard'].append([{'text': f"{' '.join(line.split()[3:])}", 'callback_data': f"{' '.join(line.split()[3:])}"}])
            counter = counter + 1
        elif counter < limit:
            counter = counter + 1
        else:
            break
    if len(reply_markup['inline_keyboard']) == 1:
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',json={'chat_id': user_id, 'text': 'That was all in my database!'})
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
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={'chat_id': user_id, 'text': 'Choose:','reply_markup': reply_markup})
    else:
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup', json={'chat_id': user_id, "message_id": state, 'reply_markup': reply_markup})


def send_voices():
    with open('voices.txt', 'r') as file:
        lines = file.readlines()
    for line in lines:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",json={'chat_id': ADMIN, 'voice': line.split()[0], 'caption': line})

def voice():
    with open('voices.txt', 'r') as file:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",params={'chat_id': ADMIN},files={'document': ('voices.txt', io.StringIO(''.join(file.readlines())))})
    file.close()
    return

def manual(user_id):
    requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/copyMessage',data={'chat_id': user_id, 'from_chat_id': ADMIN,'message_id': 2502}) # Uploaded before


def git_update(filename):
    branch = "main" # Assuming it is in main branch
    with open(filename, "r") as file:
        new_content = file.read()
    new_content_bytes = new_content.encode("utf-8")
    new_content_base64 = base64.b64encode(new_content_bytes).decode("utf-8")
    url = f"https://api.github.com/repos/{GIT_NAME}/{REPO_NAME}/contents/{filename}"
    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    response_data = response.json()
    sha = response_data["sha"]
    payload = {
        "message": "Update users.txt",
        "content": new_content_base64,
        "sha": sha,
        "branch": branch
    }
    update_url = f"https://api.github.com/repos/{GIT_NAME}/{REPO_NAME}/contents/{filename}"
    requests.put(update_url, json=payload, headers=headers)


if __name__ == '__main__':
    #testing()
    app.run(debug=False)

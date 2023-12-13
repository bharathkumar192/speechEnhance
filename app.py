from flask import Flask, request, jsonify, render_template
import os
from werkzeug.utils import secure_filename
from hume import HumeBatchClient
from hume.models.config import LanguageConfig, ProsodyConfig
from openai import OpenAI



app = Flask(__name__)
prompt_msg = '''
You are a speech feedback GPT

Your goal is to help user getting right feedback to talk better. You will get an input from our speech emotion detection model, which looks like Sentence (which is transcribed) and Emotion of that sentence which our model analyzed

Sentence (emotion) , Sentence (emotion)
And inputs include a series of sentences with emotions attached to it 

Your goal is to understand the context of that speech 
And next produce a constructive feedback of that speech to make it better 

As you are a chatbot, you will receive followup questions also asking for more feedback , suggestions to improve , simplification of feedback , substitution sentences 

Main Rule -Always give feedback by pointing out the sentence which has to be changed , and where he had to make changes 

Your output will provide a feedback 
1- Which looks for emotion and context mis-match ,(as some speeches look good on paper , but delivered with terrible emotions)

2- Which looks for sentences which are delivered well with the right emotion but can be improved if substituted with different sentences. 

3- be a great conversationalist when you were asked followup questions based on your output to help him deliver best talk 

4- Help with any minor mistakes which he is doing which can make the talk better if avoided

5- look for any sentences which can create audience engagement, and suggest if none are mentioned.'''


ALLOWED_EXTENSIONS = {'mp4', 'wav', 'mp3','flac'}

@app.route('/', methods=['POST','GET'])
def home():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_top_five_emotions(emotions):
    return sorted(emotions, key=lambda x: x['score'], reverse=True)[:5]

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        print('file recieved')
        filename = secure_filename(file.filename)
        # filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filename)

        # Process the file
        client = HumeBatchClient("zVU7pn8hIYx1TpOYAqQkAFGviXcY242Xvkx1PcfSoD9GUyGn")
        job = client.submit_job(urls=[],files=[filename], configs=[LanguageConfig(granularity="sentence"), ProsodyConfig()])
        job.await_complete()
        predictions = job.get_predictions()

        # Prepare the JSON data
        json_data = []

        for item in predictions:
            predictions = item.get('results', {}).get('predictions', [])
            for prediction in predictions:
                grouped_predictions = prediction.get('models', {}).get('prosody', {}).get('grouped_predictions', [])
                for group in grouped_predictions:
                    for pred in group['predictions']:
                        text = pred.get('text', '')
                        emotions = pred.get('emotions', [])
                        top_emotions = get_top_five_emotions(emotions)
                        json_data.append({
                            'text': text,
                            'emotions': [{'name': e['name'], 'score': e['score']} for e in top_emotions]
                        })

        # Optionally delete the file after processing
        os.remove(filename)
        primary_suggestion = initial_suggestion(json_data)
        print(primary_suggestion)
        return primary_suggestion

    return jsonify({'error': 'Error processing file'}), 500




def initial_suggestion(data):
    key = os.environ.get('API_KEY')
    print(key)
    client = OpenAI(api_key=key)
    suggestion = '' 
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": prompt_msg},
        {"role": "user", "content": str(data)}
    ]
    )
    suggestion = completion.choices[0].message.content
    return suggestion



def further_suggestions(data):
    key = os.environ.get('API_KEY')
    print(key)
    client = OpenAI(api_key=key)
    suggestion = ''
    messages = [{"role": "system", "content": prompt_msg}]
    for x in data:
        print(x)
        messages.append(x)
    print(messages)
    completion = client.chat.completions.create( model="gpt-3.5-turbo", messages=messages)
    suggestion = completion.choices[0].message.content 
    return suggestion


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json  
    response = further_suggestions(data)
    return response


if __name__ == '__main__':
    app.run(debug=True)


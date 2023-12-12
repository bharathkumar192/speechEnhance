from flask import Flask, request, jsonify,render_template
import os
from werkzeug.utils import secure_filename
from hume import HumeBatchClient
from hume.models.config import LanguageConfig, ProsodyConfig

app = Flask(__name__)

# Configure the upload folder and allowed extensions
UPLOAD_FOLDER = '/Users/bhkakuma/Downloads/assignments/dheemanth'
ALLOWED_EXTENSIONS = {'mp4', 'wav', 'mp3'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process the file
        client = HumeBatchClient("zVU7pn8hIYx1TpOYAqQkAFGviXcY242Xvkx1PcfSoD9GUyGn")
        job = client.submit_job(urls=[],files=[filepath], configs=[LanguageConfig(granularity="sentence"), ProsodyConfig()])
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
        os.remove(filepath)

        return jsonify(json_data)

    return jsonify({'error': 'Error processing file'}), 500

if __name__ == '__main__':
    app.run(debug=True)

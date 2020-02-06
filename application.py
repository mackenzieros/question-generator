from flask import Flask, request, abort, jsonify
from .question_generator import QuestionGenerator

app = Flask(__name__)

@app.route('/genquest', methods=['POST'])
def genquest():
    if not request.json:
        abort(400)
    
    if 'blurb' not in request.json.keys():
        abort(422)
    
    blurb = request.json['blurb']
    qg = QuestionGenerator(blurb)
    return jsonify({'questions': [str(question) for question in qg.get_questions()]}), 201

if __name__ == '__main__':
    app.run()
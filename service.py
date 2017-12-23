import grouper
from flask import Flask, jsonify, request, Response
from werkzeug import utils

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'Karaoke Team'


# change to post
@app.route('/group', methods=['POST'])
def get_group():
    file = request.files['file']
    file.save(utils.secure_filename(file.filename))
    groups = grouper.get_note_groups(file.filename)
    return Response(jsonify(groups), status=200, mimetype='application/json')


# change to post
@app.route('/grade', methods=['POST'])
def get_grade():
    file = request.files['file']
    file.save(utils.secure_filename(file.filename))
    # algorithm works
    return Response("{'grade':'100'}", status=200, mimetype='application/json')


if __name__ == "__main__":
    app.run(debug=True)

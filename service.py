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
    return Response(status=200)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

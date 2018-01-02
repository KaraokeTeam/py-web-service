import grouper
from flask import Flask, jsonify, request, Response
from werkzeug import utils
import os
import ffmpy

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'Karaoke Team'


# change to post
@app.route('/group', methods=['POST'])
def get_group():
    file = request.files['file']
    file.save(utils.secure_filename(file.filename))
    if any(File == 'output.wav' for File in os.listdir(".")):
        os.remove('output.wav')
        # convert the file to wav using ffmpeg
    ff = ffmpy.FFmpeg(inputs={utils.secure_filename(file.filename): None}, outputs={'output.wav': None})
    ff.run()
    # keep only the original
    os.remove(file.filename)
    groups = grouper.get_note_groups(file.filename)
    return Response(jsonify(groups), status=200, mimetype='application/json')


# change to post
@app.route('/grade', methods=['POST'])
def get_grade():
    file = request.files['file']
    file.save(utils.secure_filename(file.filename))
    # if an output file already exists delete it
    if any(File == 'output.wav' for File in os.listdir(".")):
        os.remove('output.wav')
    # convert the file to wav using ffmpeg
    ff = ffmpy.FFmpeg(inputs={utils.secure_filename(file.filename): None}, outputs={'output.wav': None})
    ff.run()
    # keep only the original
    os.remove(file.filename)
    # algorithm works - gives answer
    alg_answer = "65"
    return Response(response=alg_answer, status=200)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

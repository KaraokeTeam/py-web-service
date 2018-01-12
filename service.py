import time
import grouper
from flask import Flask, jsonify, request, Response
from werkzeug import utils
import os
import ffmpy

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'Karaoke Team'


def convert_to_wav(input_file, output_file_without_extension):
    new_file_name = output_file_without_extension + '.wav'
    if any(File == new_file_name for File in os.listdir(".")):
        os.remove('output.wav')
        # convert the file to wav using ffmpeg
    ff = ffmpy.FFmpeg(inputs={input_file: None}, outputs={new_file_name: None})
    ff.run()
    # keep only the original
    os.remove(input_file)
    return new_file_name


# change to post
@app.route('/group', methods=['POST'])
def get_group():
    file = request.files['file']
    file.save(utils.secure_filename(file.filename))
    groups = grouper.json_to_groups_array("zlil.json")
    groups_arr = groups.groups
    return Response(jsonify(groups.groups), status=200, mimetype='application/json')


# change to post
@app.route('/grade', methods=['POST'])
def get_grade():
    start = time.time()
    file = request.files['file']
    file.save(utils.secure_filename(file.filename))
    wav_file = convert_to_wav(utils.secure_filename(file.filename), "output")
    original = grouper.json_to_groups_array('zlil.json')
    client = grouper.get_note_groups(wav_file)
    res = grouper.compare(original, client)
    print("TOOK ME %f SECONDS TO RESPOND WITH RESULT %f" % ((time.time() - start), res))
    return Response(response=str(res), status=200)



if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
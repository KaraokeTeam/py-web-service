import sys
from aubio import source, pitch
import os.path
from numpy import array, ma
import matplotlib.pyplot as plt
from pylab import savefig
from demo_waveform_plot import get_waveform_plot, set_xlabels_sample2time
import json
import time

# maybe save all octaves too?
notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

notes_by_hertz = [32.7, 34.6, 36.7, 38.9, 41.2, 43.7, 46.2, 49.0, 51.9, 55.0, 58.3, 61.7, 65.4, 69.3
    , 73.4, 77.8, 82.4, 87.3, 92.5, 98.0, 103.8, 110.0, 116.5, 123.5, 130.8, 138.6, 146.8, 155.6, 164.8
    , 174.6, 185.0, 196.0, 207.7, 220.0, 233.1, 246.9, 261.6, 277.2, 293.7, 311.1, 329.6, 349.2, 370.0
    , 392.0, 415.3, 440.0, 466.2, 493.9, 523.3, 554.4, 587.3, 622.3, 659.3, 698.5, 740.0, 784.0, 830.6
    , 880.0, 932.3, 987.8, 1046.5, 1108.7, 1174.7, 1244.5, 1318.5, 1396.9, 1480.0, 1568.0, 1661.2, 1760.0
    , 1864.7, 1975.5, 2093.0, 2217.5, 2349.3, 2489.0, 2637.0, 2793.8, 2960.0, 3136.0, 3322.4, 3520.0
    , 3729.3, 3951.1]


class Pitch:
    def __init__(self, time, raw_pitch, conf):
        self.time = time
        self.raw_pitch = raw_pitch
        self.conf = conf

    @staticmethod
    def new_pitch(time,raw_pitch,conf):
        new_pitch = Pitch(time, raw_pitch, conf)
        return new_pitch

    def __str__(self):
        return "TIME : " + "{:.3f}".format(self.time) + " FREQ : " + "{:.4f}".format(
            self.raw_pitch) + " CONFIDENCE : " + "{:.3f}".format(self.conf) + "\n"

    def get_note(self):
        num = int(round(self.raw_pitch)) % 12
        return notes[num]

    def repr_json(self):
        return dict(t=str(self.time), r=str(self.raw_pitch), c=str(self.conf))


class ComplexJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, 'repr_json'):
            return o.repr_json()
        else:
            return json.JSONEncoder.default(self, o)


class Group:
    def __init__(self, note):
        self.note = note
        self.pitch_arr = []
        self.start_time = -1
        self.end_time = -1
        self.samples_amount = -1
        self.note_value = -1
        self.duration = -1

    @staticmethod
    def new_group(note):
        new_group = Group(note)
        new_group.pitch_arr = []
        return new_group


    def __str__(self):
        result = "NOTE : " + str(self.note) + "\n" +\
        "\nstart_time : " + str(self.start_time) + "\n" +\
        "\nend_time : " + str(self.end_time) + "\n" +\
        "\nsamples_amount : " + str(self.samples_amount) + "\n" +\
        "\nnote_value : " + str(self.note_value) + "\n" +\
        "\n PITCHES: \n"
        for pitch in self.pitch_arr:
            result += "\t" + str(pitch) + "\n"
        return result

    def repr_json(self):
        group_dict = dict(n=str(self.note),s=str(self.start_time),e=str(self.end_time),a=str(self.samples_amount),v=str(self.note_value),d=str(self.duration))
        return group_dict

    def set_start(self):
        if len(self.pitch_arr) > 0:
            self.start_time = self.pitch_arr[0].time


    def set_end(self):
        if len(self.pitch_arr) > 0:
            self.end_time = self.pitch_arr[len(self.pitch_arr) - 1].time

    def set_samples_amount(self):
        self.samples_amount = self.pitch_arr.__len__()

    def set_duration(self):
        self.duration=self.end_time-self.start_time


class GroupArray:
    def __init__(self, groups):
        self.groups = groups

    def repr_json(self):
        groups_dict = dict(groups=[])
        for group in self.groups:
            groups_dict['groups'].append(group)
        return groups_dict

    def __str__(self):
        result = ""
        for group in self.groups:
            result += group.__str__() + '\n'
        return result

    def set_groups_value(self):
        total_time=0
        for group in self.groups:
            group.set_start()
            group.set_end()
            group.set_duration()
            group.set_samples_amount()
            total_time=total_time+(group.end_time-group.start_time)
        for group in self.groups:
            group.note_value=(group.end_time-group.start_time)/total_time
        return self;


def compare(original, performance):
    if len(original.groups) < len(performance.groups):
        size = len(original)
    else:
        size = len(performance.groups)
    i = 0
    counter = 0
    while i < size:
        if original.groups[i].note != performance.groups[i].note:
            counter = counter + 1
            # print(original[i].note +" "+ str(original[i].get_start()) + " " +performance[i].note +" "+ str(performance[i].get_start()))
        i = i + 1
    return counter


def get_note_groups(filename):
    f = open(filename[:filename.find('.')] + '.txt', 'w')
    downsample = 1
    # 0 is default sample rate
    samplerate = 0 // downsample

    win_s = 4096 // downsample  # fft size
    hop_s = 512 // downsample  # hop size

    s = source(filename, samplerate, hop_s)
    samplerate = s.samplerate
    tolerance = 0.8
    pitch_o = pitch("yin", win_s, hop_s, samplerate)
    pitch_o.set_unit("midi")  # Hz
    pitch_o.set_tolerance(tolerance)

    pitches = []
    confidences = []
    groups = []
    previous = Pitch(0, 0, 0)
    new_group = None
    # total number of frames read
    total_frames = 0
    while True:
        samples, read = s()
        raw_pitch = pitch_o(samples)[0]
        confidence = pitch_o.get_confidence()
        current = Pitch.new_pitch(time=float((total_frames / float(samplerate))), conf=confidence, raw_pitch=raw_pitch)
        # if confidence < 0.8: pitch = 0.
        # print("%f %f %f" % (total_frames / float(samplerate), pitch, confidence))
        if 0 < raw_pitch < 128 and confidence > 0.8:
            # not the same note as the previous pitch - open a new group
            if int(round(current.raw_pitch)) != int(round(previous.raw_pitch)):
                new_group = Group.new_group(current.get_note())
                new_group.pitch_arr += [current]
                groups += [new_group]
                # same note as the previous pitch - add it to existing group
            else:
                if new_group is not None:
                    new_group.pitch_arr += [current]

        pitches += [raw_pitch]
        confidences += [confidence]
        total_frames += read
        previous = current
        if read < hop_s:
            return GroupArray(groups).set_groups_value()


def get_pitches(filename):
    downsample = 1
    # 0 is default sample rate
    samplerate = 0 // downsample

    win_s = 4096 // downsample  # fft size
    hop_s = 512 // downsample  # hop size

    s = source(filename, samplerate, hop_s)
    samplerate = s.samplerate
    tolerance = 0.8
    pitch_o = pitch("yin", win_s, hop_s, samplerate)
    pitch_o.set_unit("Hz")  # Hz
    pitch_o.set_tolerance(tolerance)

    pitches = []
    # total number of frames read
    total_frames = 0
    while True:
        samples, read = s()
        raw_pitch = pitch_o(samples)[0]
        confidence = pitch_o.get_confidence()
        current = Pitch(time=float((total_frames / float(samplerate))), conf=confidence, raw_pitch=raw_pitch)
        hz, octave, note = get_note_octave_deviation(raw_pitch)
        if confidence > 0.8:
            pitches += [current]
            # f.write("hertz: " + str(raw_pitch)+" octave: "+str(octave)+" note: "+ str(note) + "\n")

        total_frames += read
        if read < hop_s:
            return pitches


def get_note_octave_deviation(num):
    i = 0
    if (num > notes_by_hertz[len(notes_by_hertz) - 1]):
        return (notes_by_hertz[len(notes_by_hertz) - 1], 7, notes[11])
    else:
        while num > notes_by_hertz[i]:
            i = i + 1

    distance1 = abs(float(num - notes_by_hertz[i]))
    distance2 = abs(float(num - notes_by_hertz[i - 1]))
    if distance1 > distance2:
        hz = notes_by_hertz[i - 1]
        distance = distance2
    else:
        hz = notes_by_hertz[i]
        distance = distance1

    note = notes[i % 12]
    i = i + 1
    octave = int(round(i / 12))
    octave = octave + 1

    return (hz, octave, note)


def array_from_text_file(filename, dtype='float'):
    filename = os.path.join(os.path.dirname(__file__), filename)
    return array([line.split() for line in open(filename).readlines()], dtype=dtype)


def plot_pitches(filename, pitches, confidences, tolerance=0.8, hop_s=(512 // 1), samplerate=(0 // 1)):
    skip = 1
    pitches = array(pitches[skip:])
    confidences = array(confidences[skip:])
    times = [t * hop_s for t in range(len(pitches))]

    fig = plt.figure()

    ax1 = fig.add_subplot(311)
    ax1 = get_waveform_plot(filename, samplerate=samplerate, block_size=hop_s, ax=ax1)
    plt.setp(ax1.get_xticklabels(), visible=False)
    ax1.set_xlabel('')

    ax2 = fig.add_subplot(312, sharex=ax1)
    ground_truth = os.path.splitext(filename)[0] + '.f0.Corrected'
    if os.path.isfile(ground_truth):
        ground_truth = array_from_text_file(ground_truth)
        true_freqs = ground_truth[:, 2]
        true_freqs = ma.masked_where(true_freqs < 2, true_freqs)
        true_times = float(samplerate) * ground_truth[:, 0]
        ax2.plot(true_times, true_freqs, 'r')
        ax2.axis(ymin=0.9 * true_freqs.min(), ymax=1.1 * true_freqs.max())
        # plot raw pitches
        # ax2.plot(times, pitches, '.-')
        # plot cleaned up pitches
        cleaned_pitches = pitches
        cleaned_pitches = ma.masked_where(cleaned_pitches < 0, cleaned_pitches)
        cleaned_pitches = ma.masked_where(cleaned_pitches > 120, cleaned_pitches)
        cleaned_pitches = ma.masked_where(confidences < tolerance, cleaned_pitches)
        ax2.plot(times, cleaned_pitches, 'b.')
        ax2.axis(ymin=0.9 * cleaned_pitches.min(), ymax=1.1 * cleaned_pitches.max())
        # ax2.axis( ymin = 55, ymax = 70 )
        plt.setp(ax2.get_xticklabels(), visible=False)
        ax2.set_ylabel('f0 (midi)')
        # plot confidence
        ax3 = fig.add_subplot(313, sharex=ax1)
        # plot the confidence
        ax3.plot(times, confidences)
        # draw a line at tolerance
        ax3.plot(times, [tolerance] * len(confidences))
        ax3.axis(xmin=times[0], xmax=times[-1])
        ax3.set_ylabel('confidence')
        set_xlabels_sample2time(ax3, times[-1], samplerate)
        savefig(filename + 'fig.png')
        plt.show()


def groups_array_to_json(filename, groups):
    f = open(filename, "w")
    json.dump(groups, fp=f, cls=ComplexJsonEncoder)


def json_to_groups_array(filename):
    groups_dict = json.load(fp=open(filename, "r"))
    result = []
    for group in groups_dict['groups']:
        pitch_arr = []
        for pitch in group['p']:
            pitch_object = Pitch(time=float(pitch['t']), raw_pitch=float(pitch['r']),
                                 conf=float(pitch['c']))
            pitch_arr.append(pitch)
        result.append(Group(group['n'], pitch_arr))
    return GroupArray(result)


# if this is the running module execute, if its imported dont
if __name__ == "__main__":
    groups_array_to_json("jinjit.json", get_note_groups("jinjit3.wav"))
    # groups_array = json_to_groups_array("zlil.json")
    # print(str(groups_array))
    # performance = get_note_groups(sys.argv[2])
    # mis = compare(original, performance)
    # print(mis)
    # print(len(original))


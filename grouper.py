import sys
from aubio import source, pitch
import os.path
from numpy import array, ma
import matplotlib.pyplot as plt
from pylab import savefig
from demo_waveform_plot import get_waveform_plot, set_xlabels_sample2time

# maybe save all octaves too?
notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


class Pitch:
    def __init__(self, time, raw_pitch, conf):
        self.time = time
        self.raw_pitch = raw_pitch
        self.conf = conf

    def get_note(self):
        num = int(round(self.raw_pitch)) % 12
        return notes[num]


class Group:
    def __init__(self, note):
        self.note = note
        self.pitch_arr = []

    def get_start(self):

        if (len(self.pitch_arr) > 0):
            return self.pitch_arr[0].time
        return 0

    def get_end(self):
        if (len(self.pitch_arr) > 0):
            return self.pitch_arr[len(self.pitch_arr) - 1].time


def get_note_groups(filename):
    filename = sys.argv[1]
    f = open(filename[:filename.find('.')] + '.txt', 'w')
    downsample = 1
    # 0 is default sample rate
    samplerate = 0 // downsample
    if len(sys.argv) > 2:
        samplerate = int(sys.argv[2])

    win_s = 4096 // downsample  # fft size
    hop_s = 512 // downsample  # hop size

    s = source(filename, samplerate, hop_s)
    samplerate = s.samplerate
    tolerance = 0.8
    pitch_o = pitch("yin", win_s, hop_s, samplerate)
    pitch_o.set_unit("midi")
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
        current = Pitch(time=float((total_frames / float(samplerate))), conf=confidence, raw_pitch=raw_pitch)
        # if confidence < 0.8: pitch = 0.
        # print("%f %f %f" % (total_frames / float(samplerate), pitch, confidence))
        if 0 < raw_pitch < 128 and confidence > 0.8:
            # not the same note as the previous pitch - open a new group
            if int(round(current.raw_pitch)) != int(round(previous.raw_pitch)):
                new_group = Group(note=current.get_note())
                new_group.pitch_arr += [current]
                groups += [new_group]
                # same note as the previous pitch - add it to existing group
            else:
                if new_group is not None:
                    new_group.pitch_arr += [current]

            f.write(
                "Time : %f\tPitch :  %f\tConfidence : %f\n" % (total_frames / float(samplerate), raw_pitch, confidence))

        pitches += [pitch]
        confidences += [confidence]
        total_frames += read
        previous = current
        if read < hop_s:
            return groups

        def array_from_text_file(filename, dtype='float'):
            filename = os.path.join(os.path.dirname(__file__), filename)
            return array([line.split() for line in open(filename).readlines()],
                         dtype=dtype)

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

# if this is the running module execute, if its imported dont
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s <filename> [samplerate]" % sys.argv[0])
        sys.exit(1)
    f2 = open("note_groups.txt", "w")
    result = get_note_groups(sys.argv[1])
    for group in result:
        f2.write("Start: %f\t End: %f\t Note: %s\n" % (group.get_start(), group.get_end(), group.note));

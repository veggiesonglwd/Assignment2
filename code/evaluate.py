import json
import argparse
import numpy as np
from mir_eval import transcription, io, util


def prepare_data(answer_true, answer_pred, time_shift):
    ref_pitches = []
    est_pitches = []
    ref_intervals = []
    est_intervals = []

    if time_shift >= 0.0:
        for i in range(len(answer_true)):
            if (answer_true[i] is not None and float(answer_true[i][1]) - float(answer_true[i][0]) > 0
                and answer_true[i][0] >= 0.0):
                ref_intervals.append([answer_true[i][0], answer_true[i][1]])
                ref_pitches.append(answer_true[i][2])

        for i in range(len(answer_pred)):
            if (answer_pred[i] is not None and float(answer_pred[i][1]) - float(answer_pred[i][0]) > 0 
                and answer_pred[i][0]+time_shift >= 0.0):
                est_intervals.append([answer_pred[i][0]+time_shift, answer_pred[i][1]+time_shift])
                est_pitches.append(answer_pred[i][2])

    else:
        for i in range(len(answer_true)):
            if (answer_true[i] is not None and float(answer_true[i][1]) - float(answer_true[i][0]) > 0
                and answer_true[i][0]-time_shift >= 0.0):
                ref_intervals.append([answer_true[i][0]-time_shift, answer_true[i][1]-time_shift])
                ref_pitches.append(answer_true[i][2])

        for i in range(len(answer_pred)):
            if (answer_pred[i] is not None and float(answer_pred[i][1]) - float(answer_pred[i][0]) > 0
                and answer_pred[i][0] >= 0.0):
                est_intervals.append([answer_pred[i][0], answer_pred[i][1]])
                est_pitches.append(answer_pred[i][2])

    ref_intervals = np.array(ref_intervals)
    est_intervals = np.array(est_intervals)

    return ref_intervals, est_intervals, ref_pitches, est_pitches



def eval_one_data(answer_true, answer_pred, onset_tolerance=0.05, shifting=0, gt_pitch_shift=0):
    
    ref_intervals, est_intervals, ref_pitches, est_pitches = prepare_data(answer_true, answer_pred, time_shift=shifting)

    ref_pitches = np.array([float(ref_pitches[i])+gt_pitch_shift for i in range(len(ref_pitches))])
    est_pitches = np.array([float(est_pitches[i]) for i in range(len(est_pitches))])

    ref_pitches = util.midi_to_hz(ref_pitches)
    est_pitches = util.midi_to_hz(est_pitches)

    if len(est_intervals) == 0:
        ret = np.zeros(14)
        ret[9] = len(ref_pitches)
        return ret

    raw_data = transcription.evaluate(ref_intervals, ref_pitches, est_intervals, est_pitches, onset_tolerance=onset_tolerance, pitch_tolerance=50)

    ret = np.zeros(14)
    ret[0] = raw_data['Precision']
    ret[1] = raw_data['Recall']
    ret[2] = raw_data['F-measure']
    ret[3] = raw_data['Precision_no_offset']
    ret[4] = raw_data['Recall_no_offset']
    ret[5] = raw_data['F-measure_no_offset']
    ret[6] = raw_data['Onset_Precision']
    ret[7] = raw_data['Onset_Recall']
    ret[8] = raw_data['Onset_F-measure']
    ret[9] = len(ref_pitches)
    ret[10] = len(est_pitches)
    ret[11] = int(round(ret[1] * ret[9]))
    ret[12] = int(round(ret[4] * ret[9]))
    ret[13] = int(round(ret[7] * ret[9]))

    return ret

def eval_all(answer_true, answer_pred, onset_tolerance=0.05, shifting=0, print_result=True, id_list=None):

    avg = np.zeros(14)

    for i in range(len(answer_true)):
        ret = eval_one_data(answer_true[i], answer_pred[i], onset_tolerance=onset_tolerance,
                     shifting=shifting, gt_pitch_shift=0.0)

        for k in range(14):
            avg[k] = avg[k] + ret[k]

    for i in range(9):
        avg[i] = avg[i] / len(answer_true)


    if print_result:
        print("         Precision Recall F1-score")
        print("COnPOff  %f %f %f" % (avg[0], avg[1], avg[2]))
        print("COnP     %f %f %f" % (avg[3], avg[4], avg[5]))
        print("COn      %f %f %f" % (avg[6], avg[7], avg[8]))
        print("gt note num:", avg[9], "pred note num:", avg[10])
        print("song number:", len(answer_true))

    return avg


class MirEval():
    def __init__(self):
        self.gt = None
        self.pred = None
        self.gt_raw = None

    def add_gt(self, gt_path):
        with open(gt_path) as json_data:
            self.gt_raw = json.load(json_data)

    def add_tr_tuple_and_prepare(self, pred):
        length = len(pred)
        gt_data = []
        pred_data = []
        id_list = []
        for i in pred.keys():
            if i in self.gt_raw.keys():
                gt_data.append(self.gt_raw[i])
                pred_data.append(pred[i])
                id_list.append(i)

        self.gt = gt_data
        self.pred = pred_data
        self.id_list = id_list

    def prepare_data(self, annotation_path, predicted_json_path):
        with open(predicted_json_path) as json_data:
            pred = json.load(json_data)

        with open(annotation_path) as json_data:
            gt = json.load(json_data)

        gt_data = []
        pred_data = []
        id_list = []
        for i in pred.keys():
            if i in gt.keys():
                gt_data.append(gt[i])
                pred_data.append(pred[i])
                id_list.append(i)

        self.gt = gt_data
        self.pred = pred_data
        self.id_list = id_list

    def accuracy(self, onset_tolerance, print_result=True):
        return eval_all(self.gt, self.pred, onset_tolerance=onset_tolerance, print_result=print_result, id_list=self.id_list)
    

if __name__ == '__main__':
    """
    This script performs evaluation by metrics COnPOff, COnP, COn. 
    
    Sample usage:
    python evaluate.py
    
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--annotation_path', default='./data/annotations.json')
    parser.add_argument('--predicted_json_path', default='./data/predictions.json')
    parser.add_argument('--tolerance', default=0.05)

    args = parser.parse_args()
    my_eval = MirEval()
    my_eval.prepare_data(args.annotation_path, args.predicted_json_path)
    my_eval.accuracy(onset_tolerance=float(args.tolerance))


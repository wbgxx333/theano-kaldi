if __name__ == "__main__":
    import config
    config.structure("structure","Structure of discriminative model.")
    config.file("model","Pickle file containing canonical model.")
    config.file("vae_model","Pickle file containing vae model.")
    config.file("class_counts",".counts file giving counts of all the pdfs.")
    config.parse_args()

import theano
import theano.tensor as T
import ark_io
import numpy as np
import model
import data_io
import cPickle as pickle
import sys
import feedforward
from theano_toolkit.parameters import Parameters
def ark_stream():
    return ark_io.parse(sys.stdin)

def posterior_stream(predict,input_stream,buffer_size=2**16):
    frame_buffer = None
    frame_names = []
    frame_intervals = [0]

    def yield_buffer():
        posteriors = predict(frame_buffer)
        for name,start,end in zip(frame_names,frame_intervals[:-1],frame_intervals[1:]):
            print >> sys.stderr, (name,start,end)
            yield name,posteriors[start:end]
        frame_intervals[:] = [0]

    for name,frames in input_stream:
        s = frame_intervals[-1]
        if frame_buffer is None:
            frame_buffer = np.empty((buffer_size,frames.shape[1]),dtype=np.float32)

        if s + frames.shape[0] > buffer_size:
            for x in yield_buffer(): yield x
            s = 0

        frame_buffer[s:s + frames.shape[0]] = frames
        frame_intervals.append(s + frames.shape[0])
        frame_names.append(name)

    for x in yield_buffer(): yield x


def print_ark(name,array):
    print name,"["
    for i,row in enumerate(array):
        print " ",
        for cell in row:
            print "%0.6f"%cell,
        if i == array.shape[0]-1:
            print "]"
        else:
            print

if __name__ == "__main__":
    import utterance_vae
    import train_vae_features
    encoder = train_vae_features.feature_generator() 


    input_size  = config.args.structure[0]
    layer_sizes = config.args.structure[1:-1]
    output_size = config.args.structure[-1]

    with open(config.args.class_counts) as f:
        row = f.next().strip().strip('[]').strip()
        counts = np.array([ np.float32(v) for v in row.split() ])

    X = T.matrix('X')
    P = Parameters()
    classify = feedforward.build_classifier(
            P,"classifier",
            [input_size],layer_sizes,output_size,
            initial_weights=feedforward.initial_weights,
            activation=T.nnet.sigmoid
        )

    _, outputs = classify([X])
    log_output = T.log(outputs)

    P.load(config.args.model)
    predict = theano.function(
            inputs = [X],
            outputs = log_output - T.log(counts/T.sum(counts))
        )

    if predict != None:
        stream = data_io.context(ark_stream(),left=5,right=5)
        for name, frames in stream:
            print_ark(name, predict(encoder(frames)))

        #stream = posterior_stream(predict,stream)
        #for name,posteriors in stream:
        #    print_ark(name,posteriors)


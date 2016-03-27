import config
import logging
import numpy as np
import theano
@config.option("improvement_threshold","Must beat score by this amount to be considered improvement.")
def build(inputs,outputs,monitored_var,validation_stream,
        improvement_threshold,
        best_score_init=np.inf,
        best_score_callback=lambda:None,
        no_improvement_callback=lambda: None):
    output_keys = outputs.keys()
    test = theano.function(
            inputs=inputs,
            outputs=[outputs[k] for k in output_keys],
        )

    class Validator:
        def __init__(self):
            self.best_score = best_score_init
        
        def __call__(self):
            total_instances = 0
            total = np.zeros((len(output_keys),),dtype=np.float32)

            for x in validation_stream():
                outputs = test(*x)
                total_instances += x[0].shape[0]
                total += [ x[0].shape[0] * y for y in outputs ]

            report = { output_keys[i]: total[i] / float(total_instances)
                        for i in xrange(len(output_keys)) }
            logging.info(report)
            score = report[monitored_var]
            
            if self.best_score == best_score_init or \
                    score < self.best_score * improvement_threshold:
                pass
            else:
                no_improvement_callback()

            if score < self.best_score:
                self.best_score = score
                best_score_callback()
    return Validator()

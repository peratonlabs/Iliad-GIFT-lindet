import warnings
warnings.filterwarnings("ignore")

from detection.wa_detection import det
from detection.wa_detection import cal

from utils import ref_models
from utils import schema_ns
from utils import utils
import numpy as np
import os


if __name__ == "__main__":
    import json
    import jsonschema
    from jsonargparse import ArgumentParser, ActionConfigFile
    
    parser = ArgumentParser(description='Fake Trojan Detector to Demonstrate Test and Evaluation Infrastructure.')
    parser.add_argument('--model_filepath', type=str, help='File path to the pytorch model file to be evaluated.')
    parser.add_argument('--features_filepath', type=str, help='File path to the file where intermediate detector features may be written. After execution this csv file should contain a two rows, the first row contains the feature names (you should be consistent across your detectors), the second row contains the value for each of the column names.', default = "./scatch")
    parser.add_argument('--result_filepath', type=str, help='File path to the file where output result should be written. After execution this file should contain a single line with a single floating point trojan probability.', default='./output.txt')
    parser.add_argument('--scratch_dirpath', type=str, help='File path to the folder where scratch disk space exists. This folder will be empty at execution start and will be deleted at completion of execution.', default= "./scratch")
    parser.add_argument('--examples_dirpath', type=str, help='File path to the directory containing json file(s) that contains the examples which might be useful for determining whether a model is poisoned.')
    parser.add_argument('--source_dataset_dirpath', type=str, help='File path to a directory containing the original clean dataset into which triggers were injected during training.', default=None)

    parser.add_argument('--tokenizer_filepath', type=str, help='', default=None)



    parser.add_argument('--round_training_dataset_dirpath', type=str, help='File path to the directory containing id-xxxxxxxx models of the current rounds training dataset.', default=None)

    # parser.add_argument('--metaparameters_filepath', help='Path to JSON file containing values of tunable paramaters to be used when evaluating models.', action=ActionConfigFile)
    parser.add_argument('--metaparameters_filepath', help='Path to JSON file containing values of tunable paramaters to be used when evaluating models.', default= "./config/metaparameters.json")
    
    parser.add_argument('--schema_filepath', type=str, help='Path to a schema file in JSON Schema format against which to validate the config file.', default=None)
    parser.add_argument('--learned_parameters_dirpath', type=str, help='Path to a directory containing parameter data (model weights, etc.) to be used when evaluating models.  If --configure_mode is set, these will instead be overwritten with the newly-tuned parameters.', default = "./learned_parameters")

    parser.add_argument('--configure_mode', help='Instead of detecting Trojans, set values of tunable parameters and write them to a given location.',  action="store_true")
    parser.add_argument('--configure_models_dirpath', type=str, help='Path to a directory containing models to use when in self-tune mode.',default = "./data/round11/")
    parser.add_argument('--gift_basepath', type=str, help='File path to the folder where our trained detection or calibration models are.', default='/gift/')
    parser.add_argument('--task', type=str, help='Which task(s) to calibrate.  valid options: [ob, cv, all]', default='all')

    parser.add_argument('--num_cv_trials', help='number of cross validation trials to run.',  type=int, default=30)
    parser.add_argument('--cv_test_prop', help='proportion of samples to be held out during cross validation.', type=float, default=0.1)
    parser.add_argument('--round', help='the round we are running on.', type=str, default='11')

    #TEST
    # python cv_detector.py --model_filepath data/round10/models/id-00000001/model.pt  --examples_dirpath "data/round10/models/id-00000001/clean-example-data" --gift_basepath ./

    args = parser.parse_args()
    arg_dict = vars(args)
    print("summary of all arguments: ", arg_dict)

    # Validate config file against schema
    if args.metaparameters_filepath != None:
        if args.schema_filepath != None:
            with open(args.metaparameters_filepath) as config_file:
                config_json = json.load(config_file)
            with open(args.schema_filepath) as schema_file:
                schema_json = json.load(schema_file)
            jsonschema.validate(instance=config_json, schema=schema_json)

    # metaParameters = utils.read_json(args.metaparameters_filepath)
    metaParameters = schema_ns.recover_actual_config(args.metaparameters_filepath)

    model_dir = os.path.join(args.gift_basepath, 'reference_models')
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    if args.round == '-1':
        pass
    elif args.round == '1':
        ref_models.r1_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r1_load_ref_model(arch, model_dir)
    elif args.round == '2' or args.round == '3':
        ref_models.r3_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r3_load_ref_model(arch, model_dir)
    elif args.round == '4':
        ref_models.r4_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r4_load_ref_model(arch, model_dir)
    elif args.round == '7':
        ref_models.r7_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r7_load_ref_model(arch, model_dir)
    elif args.round == '8':
        ref_models.r8_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r8_load_ref_model(arch, model_dir)
    elif args.round == '9':
        ref_models.r9_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r9_load_ref_model(arch, model_dir)
    elif  args.round == '10':
        ref_models.r10_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r10_load_ref_model(arch, model_dir)
    elif args.round == '11':
        ref_models.r11_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r11_load_ref_model(arch, model_dir)
    elif  args.round == '13':
        ref_models.r13_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r13_load_ref_model(arch, model_dir)
    elif  args.round == '14':
        ref_model_function = lambda arch: None
    elif  args.round == '15':
        ref_models.r15_check_for_ref_models(model_dir)
        ref_model_function = lambda arch: ref_models.r15_load_ref_model(arch, model_dir)
    else:
        print('Round ' + args.round + ' not supported, skipping reference models')
        ref_model_function = lambda arch: None


    if args.configure_mode:
        if (args.learned_parameters_dirpath != None and args.configure_models_dirpath != None ):
            print(f"Configure Mode Activated: Calibrating Detector(s)!")
            cal(arg_dict, metaParameters, ref_model_function=ref_model_function)
        else:
            print("Required Self-Tune-Mode parameters missing!")

    else:
        if (args.model_filepath != None and 
                args.result_filepath != None and
                args.scratch_dirpath != None and
                args.examples_dirpath != None and
                # args.round_training_dataset_dirpath is not None and
                args.learned_parameters_dirpath is not None and
                args.metaparameters_filepath is not None):

            mydet = det(arg_dict, metaParameters, ref_model_function, train=False)
            # trojan_probability = mydet(model_filepath=args.model_filepath, examples_dirpath=args.examples_dirpath, scratch_dirpath=args.scratch_dirpath)[0]
            trojan_probability = mydet(model_filepath=args.model_filepath)[0]
            print("Trojan prob (before clipping ): ", trojan_probability)
            trojan_probability = np.clip(trojan_probability, 0.01, 0.99)
            # print("Trojan prob: ", trojan_probability)
                                     
            with open(args.result_filepath, 'w') as fh:
                fh.write("{}".format(trojan_probability))
        else:
            print("Required Evaluation-Mode parameters missing!")


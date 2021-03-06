#! /usr/bin/env python
import datetime
import argparse
import os
import sys
import numpy as np
import json
import logging
from preprocessing_yolo import parse_annotation
from frontend_yolo import YOLO

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"


def main(args):
    '''
    Trains the yolov2 model
    Args:
        args (argparser.parse_args object): argument object with attibutes:
            args.conf: config file
    Returns:
        N/A
    Updates:
        N/A
    Writes to file:
        -A log file in train_info/
        -The train weights---location based on config
    '''
    # set-up logger
    logger = logging.getLogger('yolo_train')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('yolo_train.log', mode='w')
    fh.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    # build the sat_obj
    # get configs
    config_path = args.conf
    with open(config_path) as config_buffer:
        config = json.load(config_buffer)
    # set paths
    curr_dir = os.getcwd()
    train_image_folder = (curr_dir + '/' +
                          config['train']['train_image_folder'])
    train_annot_folder = (curr_dir + '/' +
                          config['train']['train_annot_folder'])
    valid_image_folder = (curr_dir + '/' +
                          config['valid']['valid_image_folder'])
    valid_annot_folder = (curr_dir + '/' +
                          config['valid']['valid_annot_folder'])
    # parse annotations of the training set
    train_imgs, train_labels = (
        parse_annotation(train_annot_folder,
                         train_image_folder,
                         config['model']['labels']))

    # parse annotations of the validation set,
    # if any, otherwise split the training set
    if os.path.exists(valid_annot_folder):
        print('Using validation set:', valid_annot_folder)
        valid_imgs, valid_labels = (
            parse_annotation(valid_annot_folder,
                             valid_image_folder,
                             config['model']['labels']))
    else:
        print('Cannot find validation:', valid_annot_folder)
        print('Using training set')
        train_valid_split = int(0.8*len(train_imgs))
        np.random.shuffle(train_imgs)
        valid_imgs = train_imgs[train_valid_split:]
        train_imgs = train_imgs[:train_valid_split]

    if len(config['model']['labels']) > 0:
        overlap_labels = set(
            config['model']['labels']).intersection(set(train_labels.keys()))

        print('Seen labels:\t', train_labels)
        print('Given labels:\t', config['model']['labels'])
        print('Overlap labels:\t', overlap_labels)

        if len(overlap_labels) < len(config['model']['labels']):
            print('Some labels have no annotations!')
            print('Please revise the list of labels in the config.json file!')
            return
    else:
        print('No labels are provided. Train on all seen labels.')
        config['model']['labels'] = train_labels.keys()

    # construct the model
    logger.info('Building YOLO')
    yolo = YOLO(backend=config['model']['backend'],
                input_size=config['model']['input_size'],
                labels=config['model']['labels'],
                max_box_per_image=config['model']['max_box_per_image'],
                anchors=config['model']['anchors'],
                freeze_backend=config['model']['freeze_backend'])
    # load the pretrained weights (if any)
    pre_w_path = config['train']['pretrained_weights']
    print('Looking to load weights', pre_w_path)
    if os.path.exists(pre_w_path):
        logger.info("Loading pre-trained weights in " + pre_w_path)
        yolo.load_weights(pre_w_path)
    else:
        logger.info("No pre-trained weights loaded")

    # start the training process
    logger.info('Training started...')
    ave_pred, mAP = yolo.train(train_imgs=train_imgs,
                               valid_imgs=valid_imgs,
                               train_times=config['train']['train_times'],
                               valid_times=config['valid']['valid_times'],
                               nb_epochs=config['train']['nb_epochs'],
                               learning_rate=config['train']['learning_rate'],
                               batch_size=config['train']['batch_size'],
                               warmup_epochs=config['train']['warmup_epochs'],
                               object_scale=config['train']['object_scale'],
                               no_object_scale=(
                                   config['train']['no_object_scale']),
                               coord_scale=config['train']['coord_scale'],
                               class_scale=config['train']['class_scale'],
                               saved_weights_name=(
                                   config['train']['saved_weights_name']),
                               debug=config['train']['debug'],
                               iou_threshold=config['model']['iou_threshold'])

    logger.info('Training finished...')
    logger.info('mAP: ' + str(mAP))
    logger.info('weights: ' + str(config['train']['saved_weights_name']))
    # Store training to file
    directory = 'train_info/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    # file name
    datestr = datetime.datetime.now().strftime("%Y%m%d%H%M")
    filename_indiv = directory + 'trainlog_' + datestr
    filename_all = directory + 'trainlog'
    main_info = (datestr + ' Model: ' + config['model']['backend']
                 + ' mAP: ' + str(mAP) + 'ave_pred: ' + str(ave_pred) + '\n')
    # write to the general log
    f_all = open(filename_all, 'a+')
    f_all.write(main_info)
    f_all.close()
    # write individual file
    f_indiv = open(filename_indiv, 'a+')
    f_indiv.write(main_info)
    for x in config:
        f_indiv.write(x + '\n')
        for y in config[x]:
            str2write = y + ': ' + str(config[x][y]) + '\n'
            f_indiv.write(str2write)
    f_indiv.close()


if __name__ == '__main__':
    '''
    Executeable:
    python src/models/keras_yolo2/train.py -c configs/config_yolo.json

    Credit: Code adapted from experiencor/keras-yolo2
    '''
    # parse args
    argparser = argparse.ArgumentParser(
        description='Train and validate YOLO_v2 model on any dataset')
    argparser.add_argument(
        '-c',
        '--conf',
        help='path to configuration file')
    args = argparser.parse_args()
    # run main
    main(args)

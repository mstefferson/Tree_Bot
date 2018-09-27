#! /usr/bin/env python

import datetime
import argparse
import os
import sys
import numpy as np
import json
sys.path.append(os.getcwd())
from src.models.keras_yolo2.preprocessing import parse_annotation
from src.models.keras_yolo2.frontend import YOLO

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

argparser = argparse.ArgumentParser(
    description='Train and validate YOLO_v2 model on any dataset')

argparser.add_argument(
    '-c',
    '--conf',
    help='path to configuration file')


def _main_(args):
    config_path = args.conf

    # get configs
    with open(config_path) as config_buffer:
        config = json.loads(config_buffer.read())

    # store training info to a file

    # parse annotations of the training set
    train_imgs, train_labels = (
        parse_annotation(config['train']['train_annot_folder'],
                         config['train']['train_image_folder'],
                         config['model']['labels']))

    # parse annotations of the validation set,
    # if any, otherwise split the training set
    if os.path.exists(config['valid']['valid_annot_folder']):
        valid_imgs, valid_labels = (
            parse_annotation(config['valid']['valid_annot_folder'],
                             config['valid']['valid_image_folder'],
                             config['model']['labels']))
    else:
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
    yolo = YOLO(backend=config['model']['backend'],
                input_size=config['model']['input_size'],
                labels=config['model']['labels'],
                max_box_per_image=config['model']['max_box_per_image'],
                anchors=config['model']['anchors'])

    # load the pretrained weights (if any)
    if os.path.exists(config['train']['pretrained_weights']):
        print("Loading pre-trained weights in",
              config['train']['pretrained_weights'])
        yolo.load_weights(config['train']['pretrained_weights'])

    # start the training process
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
                               debug=config['train']['debug'])

    # Store training to file
    directory = 'train_info/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    # file name
    datestr = datetime.datetime.now().strftime("%Y%m%d%H%M")
    filename_indiv = directory + 'trainlog_' + datestr
    filename_all = directory + 'trainlog'
    main_info = (datestr + ' Model: ' + config['model']['backend']
                 + ' mAP:' + str(mAP) + '\n')
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
    args = argparser.parse_args()
    _main_(args)

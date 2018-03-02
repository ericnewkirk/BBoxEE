# -*- coding: utf-8 -*-
#
# Animal Detection Network (Andenet)
# Copyright (C) 2017 Peter Ersts
# ersts@amnh.org
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network (Andenet).
#
# Andenet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Andenet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Point Class Assigner.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
import io
import json
from PIL import Image
from PyQt5 import QtCore
import numpy as np


class AndenetPackager(QtCore.QThread):
    """
    Packacges annotated image examples into the Andenet format.

    Andenet package format consists of two file:
    metadata.json
        JSON file containing the annotation information

    images.bin
        Binary file of sequentially written images whos offsets and
        sizes are stored with the annotaiton information
    """

    progress = QtCore.pyqtSignal(int)
    packaged = QtCore.pyqtSignal()

    def __init__(self, directory, examples, masks, remap):
        """
        Class init function.

        Args:
            directory (str): Destination directory
            examples (list): List of all of the annotated examples
            masks (dict): Dictionary holding the masks index by mask name
            remap (dict): A lookup table for renaming classes
        """
        QtCore.QThread.__init__(self)
        self.directory = directory
        self.examples = examples
        self.masks = masks
        self.remap = remap

    def run(self):
        """
        The starting point for the thread.

        After creating and instance of the class, calling start() will call this
        function which processes and saves all of the annotaiton examples to disk.
        """
        counter = 0
        running_byte_count = 0
        image_writer = open(self.directory + os.path.sep + 'images.bin', 'wb')
        json_writer = open(self.directory + os.path.sep + 'metadata.json', 'w')
        examples_to_package = []
        for example in self.examples:
            # Remap the label names and drop exluded classes
            annotations = []
            for annotation in example['annotations']:
                if self.remap[annotation['label']].lower() != 'exclude':
                    annotation['label'] = self.remap[annotation['label']]
                    annotations.append(annotation)
            example['annotations'] = annotations
            # Only process images with more than on annotation remaining
            if len(example['annotations']) > 0:
                file_name = example['directory'] + os.path.sep + example['file']
                img = Image.open(file_name)
                # Turn image into an array to remove metadata and apply mask if there is one
                array = np.array(img)
                if example['mask_name'] != '':
                    array = array * self.masks[example['mask_name']]
                # Convert array back into an image and save in memory as a jpeg
                img = Image.fromarray(array)
                jpeg_file = io.BytesIO()
                img.save(jpeg_file, format='JPEG')
                img.close()
                # Write image data to file and add metadata to example record
                encoded_jpg = jpeg_file.getvalue()
                bytes_out = image_writer.write(encoded_jpg)
                example['image_data'] = {'start': running_byte_count, 'size': bytes_out}
                running_byte_count += bytes_out
                # Push example onto metadata list to package
                examples_to_package.append(example)
            counter += 1
            self.progress.emit(counter)
        json.dump(examples_to_package, json_writer)
        image_writer.close()
        json_writer.close()
        self.packaged.emit()
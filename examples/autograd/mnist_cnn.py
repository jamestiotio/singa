#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import numpy as np
import argparse
import os

from singa import device
from singa import tensor
from singa import autograd
from singa import optimizer


def load_data(path):
    f = np.load(path)
    x_train, y_train = f['x_train'], f['y_train']
    x_test, y_test = f['x_test'], f['y_test']
    f.close()
    return (x_train, y_train), (x_test, y_test)


def to_categorical(y, num_classes):
    '''
    Converts a class vector (integers) to binary class matrix.

    Args
        y: class vector to be converted into a matrix
            (integers from 0 to num_classes).
        num_classes: total number of classes.

    Return
        A binary matrix representation of the input.
    '''
    y = np.array(y, dtype='int')
    n = y.shape[0]
    categorical = np.zeros((n, num_classes))
    categorical[np.arange(n), y] = 1
    categorical = categorical.astype(np.float32)
    return categorical


def preprocess(data):
    data = data.astype(np.float32)
    data /= 255
    data = np.expand_dims(data, axis=1)
    return data


def accuracy(pred, target):
    y = np.argmax(pred, axis=1)
    t = np.argmax(target, axis=1)
    a = y == t
    return np.array(a, 'int').sum() / float(len(t))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Train CNN over MNIST')
    parser.add_argument('file_path', type=str, help='the dataset path')
    parser.add_argument('--use_cpu', action='store_true')
    args = parser.parse_args()

    assert os.path.exists(args.file_path), \
        'Pls download the MNIST dataset from '

    if args.use_cpu:
        print('Using CPU')
        dev = device.get_default_device()
    else:
        print('Using GPU')
        dev = device.create_cuda_gpu()

    train, test = load_data(args.file_path)

    batch_number = 600
    num_classes = 10
    epochs = 1

    sgd = optimizer.SGD(0.05)

    x_train = preprocess(train[0])
    y_train = to_categorical(train[1], num_classes)

    x_test = preprocess(test[0])
    y_test = to_categorical(test[1], num_classes)
    print('the shape of training data is', x_train.shape)
    print('the shape of training label is', y_train.shape)
    print('the shape of testing data is', x_test.shape)
    print('the shape of testing label is', y_test.shape)

    # operations initialization
    conv1 = autograd.Conv2D(1, 32, 3, padding=1, bias=False)
    conv2 = autograd.Conv2D(32, 32, 3, padding=1)
    linear = autograd.Linear(32 * 28 * 28, 10)

    def forward(x, t):
        y = conv1(x)
        y = autograd.relu(y)
        y = conv2(y)
        y = autograd.relu(y)
        y = autograd.max_pool_2d(y)
        y = autograd.flatten(y)
        y = linear(y)
        y = autograd.soft_max(y)
        loss = autograd.cross_entropy(y, t)
        return loss, y

    autograd.training = True
    for epoch in range(epochs):
        for i in range(batch_number):
            inputs = tensor.Tensor(device=dev, data=x_train[i * 100:(1 + i) * 100])
            targets = tensor.Tensor(device=dev, data=y_train[i * 100:(1 + i) * 100])

            loss, y = forward(inputs, targets)

            accuracy_rate = accuracy(tensor.to_numpy(y),
                                     tensor.to_numpy(targets))
            if (i % 5 == 0):
                print('accuracy is:', accuracy_rate, 'loss is:',
                      tensor.to_numpy(loss)[0])

            for p, gp in autograd.backward(loss):
                sgd.apply(0, gp, p, '')
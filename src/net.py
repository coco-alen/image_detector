'''
implement the underlying architecture 
contains the code that creates the yolo network
'''
from __future__ import division
from operator import mod
from turtle import forward
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import conv2d, max_pool2d, tensor
from torch.autograd import Variable
import numpy as np
from util import *
import time
'''those algorithm are used to detect human. 
   As a result, there are only one class as default'''
class Yolov1(nn.Module):
    def __init__(self, num_class = 1) -> None:
        super(Yolov1, self).__init__()
        self.feature = nn.Sequential(           # input[3, 448, 448]
            nn.Conv2d(3, 64, 7, 2, 3),          # output[64, 224, 224]
            nn.LeakyReLU(inplace=True),
            nn.MaxPool2d(2, 2),                 # output[64, 112, 112]
            nn.Conv2d(64, 192, 3, 1, 1),        # output[192, 112, 112  
            nn.LeakyReLU(inplace=True),
            nn.MaxPool2d(2, 2),                 # output[192, 56, 56]
            nn.Conv2d(192, 128, 1, 1, 0),       # output[128, 56, 56]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(128, 256, 3, 1, 1),       # output[256, 56, 56]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(256, 256, 1, 1, 0),       # output[256, 56, 56]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(256, 512, 3, 1, 1),       # output[512, 56, 56]
            nn.LeakyReLU(inplace=True),
            nn.MaxPool2d(2, 2),                 # output[512, 28, 28]
            nn.Conv2d(512, 256, 1, 1, 0),       # output[256, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(256, 512, 3, 1, 1),       # output[512, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 256, 1, 1, 0),       # output[256, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(256, 512, 3, 1, 1),       # output[512, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 256, 1, 1, 0),       # output[256, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(256, 512, 3, 1, 1),       # output[512, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 256, 1, 1, 0),       # output[256, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(256, 512, 3, 1, 1),       # output[512, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 512, 1, 1, 0),       # output[512, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 1024, 3, 1, 1),      # output[1024, 28, 28]
            nn.LeakyReLU(inplace=True),
            nn.MaxPool2d(2, 2),                 # output[1024, 14, 14]
            nn.Conv2d(1024, 512, 1, 1, 0),      # output[512, 14, 14]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 1024, 3, 1, 1),      # output[1024, 14, 14]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(1024, 512, 1, 1, 0),      # output[512, 14, 14]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(512, 1024, 3, 1, 1),      # output[1024, 14, 14]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, 1, 1),     # output[1024, 14, 14]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, 2, 1),     # output[1024, 7, 7]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, 1, 1),     # output[1024, 7, 7]
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, 1, 1),     # output[1024, 7, 7]
            nn.LeakyReLU(inplace=True),
        )
        self.linear1 = nn.Sequential(
            nn.Linear(7*7*1024, 4096),         # output[4096]
            nn.LeakyReLU(inplace=True),
        )
        self.linear2 = nn.Linear(4096, 7*7*num_class)    # output[7*7*30]
        self.num_class = num_class
    def forward(self, x):
        
        x = self.feature(x)
        x = x.view(-1, 7*7*1024)
        x = self.linear1(x)
        x = self.linear2(x)
        
        return x
def parse_cfg(cfgfile):
    """
    Takes a configuration file
    
    Returns a list of blocks. Each blocks describes a block in the neural
    network to be built. Block is represented as a dictionary in the list
    
    """
    line = []
    with open(cfgfile, 'r') as conf:
        # split the file by '\n' character
        lines = conf.read().split('\n')
        lines = [x for x in lines if len(x)>0]
        lines = [x for x in lines if x[0]!='#']
        lines = [x.strip() for x in lines]
    block = {}
    blocks = []

    for line in lines:
        if line[0] == '[':
            if len(block) != 0:
                blocks.append(block)
                block = {}
            block["type"] = line[1:-1].rstrip()
        else:
            key, value = line.split('=')
            block[key.strip()] = value.strip()
    blocks.append(block)
    return blocks
def create_modules(blocks):
    net_info = blocks[0]
    module_list = nn.ModuleList()
    # make sure the number of previous layer's filters
    prev_filters = 3
    output_filters = []
    for index, x in enumerate(blocks[1:]):
        module = nn.Sequential()
        if x["type"] == "convolutional":
            try:
                batch_normalize = int(x["batch_normalize"])
                bias = False
            except:
                batch_normalize = 0
                bias = True
            
            filters = int(x["filters"])
            kernel_size = int(x["size"])
            stride = int(x["stride"])
            padding = int(x["pad"])
            activation = x["activation"]

            # pad规则
            if padding:
                pad = (kernel_size - 1) // 2
            else:
                pad = 0
            
            # Add the Convolutional Layer
            conv = nn.Conv2d(prev_filters, filters, kernel_size, stride, pad, bias = bias)
            module.add_module("conv_{}".format(index), conv)

            # Add the Batch Norm Layer
            if batch_normalize:
                bn = nn.BatchNorm2d(filters)
                module.add_module("batch_norm_{}".format(index), bn)
            
            # Add activation layer
            if activation == "leaky":
                activn = nn.LeakyReLU(0.1, inplace=True)
                module.add_module("leaky_{}".format(index), activn)
            else: 
                pass

        elif x["type"] == "upsample":
            stride = int(x["stride"])
            upsample = nn.Upsample(scale_factor = stride, mode = "bilinear")
            module.add_module("upsample_{}".format(index), upsample)

        elif x["type"] == "route":
            x["layers"] = x["layers"].split(',')
            start = int(x["layers"][0])
            try:
                end = int(x["layers"][1])
            except:
                end = 0

            # this step is uesd to transform absolute index to relative index
            if start > 0:
                start = start - index
            if end > 0:
                end = end - index
            route = EmptyLayer()
            module.add_module("route_{}".format(index), route)
            if end < 0:
                filters = output_filters[index + start] + output_filters[index + end]
            else:
                filters = output_filters[index + start]
            
        elif x["type"] == "shortcut":
            shortcut = EmptyLayer()
            module.add_module("shortcut_{}".format(index), shortcut)
        
        elif x["type"] == "yolo":
            mask = x["mask"].split(',')
            mask = [int(x) for x in mask]
            anchors = x["anchors"].split(',')
            anchors = [int(x) for x in anchors]
            anchors = [(anchors[i], anchors[i+1]) for i in range(0, len(anchors), 2)]
            anchors = [anchors[i] for i in mask]

            detection = DetectionLayer(anchors)
            module.add_module("yolo_{}".format(index), detection)
        elif x["type"] == "maxpool":
            pool_size = int(x["size"])
            pool_stride = int(x["stride"])
            maxpool = nn.MaxPool2d(pool_size, pool_stride)
            module.add_module("maxpool_{}".format(index), maxpool)
        
        module_list.append(module)
        prev_filters = filters
        output_filters.append(filters)
    
    return (net_info, module_list)
def get_test_input():
    img = cv2.imread("data_set\dog-cycle-car.png")
    img = cv2.resize(img, (416,416))          #Resize to the input dimension
    
    img_ =  img[:,:,::-1].transpose((2,0,1))  # BGR -> RGB | H X W C -> C X H X W 
    img_ = img_[np.newaxis,:,:,:]/255.0       #Add a channel at 0 (for batch) | Normalise
    img_ = torch.from_numpy(img_).float()     #Convert to float
    img_ = Variable(img_)                     # Convert to Variable
    return img_
class EmptyLayer(nn.Module):
    def __init__(self):
        super(EmptyLayer, self).__init__()
class DetectionLayer(nn.Module):
    def __init__(self, anchors):
        super(DetectionLayer, self).__init__()
        self.anchors = anchors
class Darknet(nn.Module):
    def __init__(self, cfgfile) -> None:
        super(Darknet, self).__init__()
        self.blocks = parse_cfg(cfgfile)
        self.net_info, self.module_list = create_modules(self.blocks)
    
    def forward(self, x, CUDA : bool = False):
        '''
        CUDA: True means to use CUDA, False means not to use CUDA
        '''
        
        modules = self.blocks[1:]
        cache_outputs = {}
        write = 0

        for i, module in enumerate(modules):
            module_type = (module["type"])
            if module_type == "convolutional" or module_type == "upsample":
                x = self.module_list[i](x)
                
            elif module_type == "route":
                layers = module["layers"]
                layers = [int(i) for i in layers]

                if layers[0] > 0:
                    layers[0] = layers[0] - i
                if len(layers) == 1:
                    x = cache_outputs[i + layers[0]]
                else:
                    if layers[1] > 0:
                        layers[1] = layers[1] - i
                    
                    map1 = cache_outputs[i + layers[0]]
                    map2 = cache_outputs[i + layers[1]]

                    x = torch.cat((map1, map2), 1)
            
            elif module_type == "shortcut":
                from_ = int(module["from"])
                x = cache_outputs[i-1] + cache_outputs[i+from_]
            
            elif module_type == "yolo":
                anchors = self.module_list[i][0].anchors

                #Get the inout dimensions
                inp_dim = int(self.net_info["height"])

                #Get the num of classes
                num_classes = int(module["classes"])

                # Transform
                x = x.data
                x = predict_transform(x, inp_dim, anchors, num_classes, CUDA)

                if not write:
                    detections = x
                    write = 1
                else:
                    detections = torch.cat((detections, x), 1)
            elif module_type == "maxpool":
                try:
                    pool_pad = int(module["pad"])
                except:
                    pool_pad = 0
                
                if pool_pad:
                    pd = (0, 1, 0, 1)
                    x = F.pad(x, pd, 'constant', 0)
                x = self.module_list[i](x)
            cache_outputs[i] = x
        return detections
    
    def load_weights(self, weightfile):
        with open(weightfile, 'rb') as fp:
            #The first 5 values are header information 
            # 1. Major version number
            # 2. Minor Version Number
            # 3. Subversion number 
            # 4,5. Images seen by the network (during training)
            header = np.fromfile(fp, dtype = np.int32, count = 5)
            self.header = torch.from_numpy(header)
            self.seen = self.header[3]

            weights = np.fromfile(fp, dtype = np.float32)
            ptr = 0
            for i in range(len(self.module_list)):
                module_type = self.blocks[i + 1]["type"]

                #If module_type is convolutional load weights
                #Otherwise ignore.

                if module_type == "convolutional":
                    model = self.module_list[i]
                    try:
                        batch_normalize = int(self.blocks[i+1]["batch_normalize"])
                    except:
                        batch_normalize = 0
                    # read convolutional layer
                    conv = model[0]

                    if (batch_normalize):
                        bn = model[1]

                        #Get the number of weights of Batch Norm Layer
                        num_bn_biases = bn.bias.numel()

                        #Load the weights
                        bn_biases = torch.from_numpy(weights[ptr:ptr + num_bn_biases])
                        ptr += num_bn_biases

                        bn_weights = torch.from_numpy(weights[ptr: ptr + num_bn_biases])
                        ptr  += num_bn_biases

                        bn_running_mean = torch.from_numpy(weights[ptr: ptr + num_bn_biases])
                        ptr  += num_bn_biases

                        bn_running_var = torch.from_numpy(weights[ptr: ptr + num_bn_biases])
                        ptr  += num_bn_biases

                        #Cast the loaded weights into dims of model weights. 
                        bn_biases = bn_biases.view_as(bn.bias.data)
                        bn_weights = bn_weights.view_as(bn.weight.data)
                        bn_running_mean = bn_running_mean.view_as(bn.running_mean)
                        bn_running_var = bn_running_var.view_as(bn.running_var)

                        #Copy the data to model
                        bn.bias.data.copy_(bn_biases)
                        bn.weight.data.copy_(bn_weights)
                        bn.running_mean.copy_(bn_running_mean)
                        bn.running_var.copy_(bn_running_var)
                    else:
                        #Number of biases
                        num_biases = conv.bias.numel()

                        #Load the weights
                        conv_biases = torch.from_numpy(weights[ptr: ptr + num_biases])
                        ptr = ptr + num_biases

                        #reshape the loaded weights according to the dims of the model weights
                        conv_biases = conv_biases.view_as(conv.bias.data)

                        #Finally copy the data
                        conv.bias.data.copy_(conv_biases)
                
                    #Let us load the weights for the Convolutional layers
                    num_weights = conv.weight.numel()

                    #Do the same as above for weights
                    conv_weights = torch.from_numpy(weights[ptr:ptr+num_weights])
                    ptr = ptr + num_weights

                    conv_weights = conv_weights.view_as(conv.weight.data)
                    conv.weight.data.copy_(conv_weights)


if __name__ == '__main__':
    model = Darknet("cfg/yolov3-tiny.cfg").cuda()
    model.load_weights("weights\yolov3-tiny.weights")
    inp = get_test_input().cuda()
    model.eval()

    with torch.no_grad():
        t1 = time.perf_counter()
        print(model)
        pred = model(inp, True)
        print(time.perf_counter() - t1)
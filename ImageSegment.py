import cv2
import numpy as np
from SegmentNet import SegmentNet
import torch

#set device to GPU
device = torch.device(0)

#Load in net and parameters
net_state_dict = ".\\TrainedNet3-5EPOCH"
net = SegmentNet().type(torch.cuda.FloatTensor).cuda()
net.load_state_dict(torch.load(net_state_dict))
net.eval()

img_path = "C:\\Users\\Spencer\\Documents\\GitHub\\PASCAL-VOC-2012-Segmentation-Experiement\\VOCdevkit\\VOC2012\\JPEGImages\\2007_000032.jpg"
img = cv2.imread(img_path, 1)


def encode_image(img): #any image HxWx3
    x = np.swapaxes(x, 0, 1)
    x = np.swapaxes(x, 1, 2)
    img = torch.tensor(img).type(torch.cuda.FloatTensor)
    img = img.unsqueeze_(0)
    return img

def decode_image(label): #1x512x512
    label = np.swapaxes(label, 1, 2)
    label = np.swapaxes(label, 0, 1)
    h,w,c = label.shape
    res = np.zeros((h, w, 3))
    label = label.to('cpu').detach().numpy()
    label = np.squeeze(label, 0)

    classes = [[0, 0, 0], [192, 224, 224], [0, 0, 128], [0, 128, 0], [0, 128, 128],
                    [128, 0, 0], [128, 0, 128], [128, 128, 0], [128, 128, 128], [0, 0, 64],
                    [0, 0, 192], [0, 128, 64], [0, 128, 192], [128, 0, 64], [128, 0, 192],
                    [128, 128, 64], [128, 128, 192], [0, 64, 0], [0, 64, 128], [0, 192, 0],
                    [0, 192, 128], [128, 64, 0]]

    for i in range(len(label)):
        for j in range(len(label[i])):
            res[i][j] = classes[label[i][j]]

    return res

img_enc = encode_image(img)
label = net(img_enc)
print(label)
res = decode_image(label)

print(res)
cv2.imshow('seg', res)
cv2.imshow('img', img)
cv2.waitKey(0)



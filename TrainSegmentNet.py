from SegmentNet import SegmentNet
from DatasetCreate import ImageData
from JaccardLoss import jaccard_loss
import torch
import torch.optim as optim
import torch.utils.data as data
import torch.nn as nn
import sys
from tqdm import tqdm
import wandb

wandb.init(project="segmentation-net")

print("Loading Data...")
trainset = ImageData("./VOCdevkit/VOC2012/SegmentTrain", "./VOCdevkit/VOC2012/SegmentTrainLabels")
valset = ImageData("./VOCdevkit/VOC2012/SegmentVal", "./VOCdevkit/VOC2012/SegmentValLabels")

BATCH_SIZE = 5

train_loader = data.DataLoader(trainset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = data.DataLoader(valset, batch_size=BATCH_SIZE, shuffle=True)
print("completed.")

device = torch.device(0)

def net_init(model):
    classname = model.__class__.__name__
    if classname.find('Conv2d') != -1:
        model.weight.data.uniform_(0.0, 0.05)
        if model.bias is not None:
            model.bias.data.fill_(0.0)

print("Initializing Network...")
net = SegmentNet().type(torch.cuda.FloatTensor).cuda()
net.apply(net_init)
wandb.watch(net)
print("completed")

EPOCHS = 1

def train(net):
    print("Training Beginning")
    optimizer = optim.RMSprop(net.parameters(), lr=0.00025, momentum=0.9, weight_decay=0.0005)
    weights = torch.ones(21)
    criterion = nn.CrossEntropyLoss(weight=weights, reduction='sum')
    for epoch in range(EPOCHS):
        loss_track = 0.0
        for data in enumerate(tqdm(train_loader)):
            X, label = data[1][0].type(torch.cuda.FloatTensor), data[1][1].type(torch.cuda.FloatTensor)
            
            optimizer.zero_grad()

            #small GPU: only 3GiB :( Cloud GPU :)
            try:
                output_label = net(X)
            except RuntimeError as e:
                if 'out of memory' in str(e):
                    print("No more memory: retrying", sys.stdout)
                    sys.stdout.flush()
                    for p in net.parameters():
                        if p.grad is not None:
                            del p.grad
                    torch.cuda.empty_cache()
                    output_label = net(X)
                else:
                    raise e

            label = label.squeeze(1)
            jacc = jaccard_loss(label.type(torch.cuda.LongTensor), output_label.type(torch.cuda.FloatTensor), eps=1e-4)
            loss = jacc + criterion(output_label.type(torch.cuda.FloatTensor), label.type(torch.int64))
            loss.backward()

            optimizer.step()

            loss_track += loss.item()/BATCH_SIZE
            if data[0] % 5 == 0:
                print("Epoch: %d    Training Loss: %.5f\n" % (epoch+1, loss_track))
                wandb.log({"Training Loss": loss_track})
                loss_track = 0.0

        print("Running Validation...")
        track_val_loss = 0.0
        track_val_acc = 0.0
        with torch.no_grad():
            for val in enumerate(tqdm(val_loader)):
                val_img, val_lab = val[1][0].type(torch.cuda.FloatTensor), val[1][1].type(torch.cuda.FloatTensor)
                output_label = net(val_img)
                val_lab = val_lab.squeeze(1)
                val_loss = jaccard_loss(val_lab.type(torch.cuda.LongTensor), output_label.type(torch.cuda.FloatTensor), eps=1e-4)
                val_acc = ((val_loss)-1)*-1
                track_val_acc += val_acc/BATCH_SIZE
                track_val_loss += val_loss/BATCH_SIZE
                if val[0] % 10 == 0:
                    wandb.log({"Val Acc": track_val_acc, "Val Jaccard Loss": track_val_loss})
                    print("   Validation Acc: %.5f    Validation Jaccard Loss: %.5f\n" % (track_val_acc, track_val_loss))
                    track_val_loss = 0.0
                    track_val_acc = 0.0


train(net)
#16:14 min/epoch

torch.save(net.state_dict(), "./TrainedNet1")
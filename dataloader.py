import numpy, random, pdb, math, pickle, glob, time
import torch

class DataLoader():
    def __init__(self, fname, opt):
        self.opt = opt
        self.data = []
        k = 0
        for i in range(opt.nshards):
            f = f'{opt.data_dir}/traffic_data_lanes={opt.lanes}-episodes={opt.n_episodes}-seed={i+1}.pkl'
            print(f'loading {f}')
            self.data += pickle.load(open(f, 'rb'))
        self.images = []
        self.states = []
        self.actions = []
        self.masks = []
        for run in self.data:
            self.images.append(run.get('images'))
            self.states.append(run.get('states'))
            self.actions.append(run.get('actions'))
            self.masks.append(run.get('masks'))

        print(len(self.states))
        self.n_episodes = len(self.states)
        self.n_train = int(math.floor(self.n_episodes * 0.9))
        self.n_valid = int(math.floor(self.n_episodes * 0.05))
        self.n_test = int(math.floor(self.n_episodes * 0.05))
        self.train_indx = range(0, self.n_train)
        self.valid_indx = range(self.n_train+1, self.n_train+self.n_valid)
        self.test_indx = range(self.n_train+self.n_valid+1, self.n_episodes)


    # get batch to use for imitation learning:
    # a sequence of ncond consecutive states, and a sequence of npred actions
    def get_batch_il(self, split):
        if split == 'train':
            indx = self.train_indx
        elif split == 'valid':
            indx = self.valid_indx
        elif split == 'test':
            indx = self.test_indx

        images, states, masks, actions = [], [], [], []
        nb = 0
        while nb < self.opt.batch_size:
            s = random.choice(indx)
            T = len(self.states[s]) - 1
            if T > (self.opt.ncond + self.opt.npred):
                t = random.randint(0, T - (self.opt.ncond+self.opt.npred))
                images.append(self.images[s][t:t+(self.opt.ncond+self.opt.npred)+1])
                states.append(self.states[s][t:t+(self.opt.ncond+self.opt.npred)+1])
                masks.append(self.masks[s][t:t+(self.opt.ncond+self.opt.npred)])
                actions.append(self.actions[s][t:t+(self.opt.ncond+self.opt.npred)])
                nb += 1
        images = torch.stack(images)
        states = torch.stack(states)
        actions = torch.stack(actions)
        masks = torch.stack(masks)
        images = images[:, :self.opt.ncond].clone()
        states = states[:, :self.opt.ncond, 0].clone()
        masks = masks[:, :self.opt.ncond].clone()
        actions = actions[:, self.opt.ncond:(self.opt.ncond+self.opt.npred)].clone()
        images = images.float() / 255.0
        print(time.time() - t0)

        assert(images.max() <= 1 and images.min() >= 0)
        return images.float().cuda(), states.float().cuda(), actions.float().cuda()



    # get batch to use for forward modeling
    # a sequence of ncond given states, a sequence of npred actions, 
    # and a sequence of npred states to be predicted
    def get_batch_fm(self, split):
        tt = time.time()
        if split == 'train':
            indx = self.train_indx
        elif split == 'valid':
            indx = self.valid_indx
        elif split == 'test':
            indx = self.test_indx

        images, states, masks, actions = [], [], [], []
        nb = 0
        t0 = time.time()
        while nb < self.opt.batch_size:
            s = random.choice(indx)
            T = self.images[s].size(0)
            if T > (self.opt.ncond + self.opt.npred + 1):
                t = random.randint(0, T - (self.opt.ncond+self.opt.npred + 1))
                images.append(self.images[s][t:t+(self.opt.ncond+self.opt.npred)+1].cuda())
                states.append(self.states[s][t:t+(self.opt.ncond+self.opt.npred)+1])
                masks.append(self.masks[s][t:t+(self.opt.ncond+self.opt.npred)])
                actions.append(self.actions[s][t:t+(self.opt.ncond+self.opt.npred)].cuda())
                nb += 1

        images = torch.stack(images)
        actions = torch.stack(actions)
        actions = actions[:, (self.opt.ncond-1):(self.opt.ncond+self.opt.npred-1)].float().contiguous()
        input_images = images[:, :self.opt.ncond].float()
        target_images = images[:, self.opt.ncond:(self.opt.ncond+self.opt.npred)].float()
        input_images.div_(255.0)
        target_images.div_(255.0)

        input_states, target_states, masks = None, None, None


#        states = torch.stack(states)
#        masks = torch.stack(masks)
#        input_states = states[:, :self.opt.ncond, 0].clone()
#        target_states = states[:, self.opt.ncond:(self.opt.ncond+self.opt.npred), 0].clone()
#        masks = masks[:, :self.opt.ncond].clone()

        return input_images, actions, target_images, None, None #input_states.float().cuda(), target_states.float().cuda()


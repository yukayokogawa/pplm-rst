import random
import os
import glob
import numpy as np
import torch
import torch.nn.functional as F
import math

from nltk.tree import Tree

def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.n_gpus > 0:
        torch.cuda.manual_seed_all(args.seed)

def get_latest_ckpt_path(ckpt_dir):
    def get_epoch_num(path):
        base = os.path.basename(path)
        base = base.split('.')[0].split('_')[0]
        base = base.split('=')[1]
        return int(base)

    ckpt_list = sorted(
        glob.glob(os.path.join(ckpt_dir, "*.ckpt")),
        key=lambda x: get_epoch_num(x),
        reverse=False
    )
    return ckpt_list[-1]


def collate_tokens(values, pad_idx):
    """Convert a list of 1d tensors into a padded 2d tensor."""
    size = max(v.size(0) for v in values)
    res = values[0].new(len(values), size).fill_(pad_idx)

    def copy_tensor(src, dst):
        assert dst.numel() == src.numel()
        dst.copy_(src)

    for i, v in enumerate(values):
        copy_tensor(v, res[i][:len(v)])
    return res

def get_perplexity(loss):
    try:
        return math.pow(2, loss)
    except OverflowError:
        return float('inf')

def move_to_cuda(sample):

    def _move_to_cuda(tensor):
        return tensor.cuda()

    return apply_to_sample(_move_to_cuda, sample)

def apply_to_sample(f, sample):
    if len(sample) == 0:
        return {}

    def _apply(x):
        if torch.is_tensor(x):
            return f(x)
        elif isinstance(x, dict):
            r = {key: _apply(value) for key, value in x.items()}
            return r
            # return {
            #     key: _apply(value)
            #     for key, value in x.items()
            # }
        elif isinstance(x, list):
            return [_apply(x) for x in x]
        else:
            return x

    return _apply(sample)


def get_normalized_probs(output, log_probs=False):
    logits = output.float()
    if log_probs:
        return F.log_softmax(logits, dim=-1)
    else:
        return F.softmax(logits, dim=-1)

def assign_tree_to_edu(tree_str):
    tree = Tree.fromstring(tree_str)
    leaves = tree.leaves()
    left_tree = tree[0]
    right_tree = tree[1]
    left_leaves = left_tree.leaves()
    right_leaves = right_tree.leaves()
    num_left_leaves = len(left_leaves)
    num_right_leaves = len(right_leaves)
    assert num_left_leaves <= 2
    assert num_right_leaves <= 2
    if num_left_leaves == 1:
        if num_right_leaves == 1:
            assert leaves == ['0', '1']
            result = {
                '0' : 1,
                '1' : 3,
            }
        else:
            assert leaves == ['0', '1', '2']
            result = {
                '0' : 1,
                '1' : 2,
                '2' : 3,
            }
    else: #num_left_leaves == 2
        if num_right_leaves == 1:
            assert leaves == ['0', '1', '2']
            result = {
                '0' : 0,
                '1' : 1,
                '2' : 3,
            }
        else:
            assert leaves == ['0', '1', '2', '3']
            result = {
                '0' : 0,
                '1' : 1,
                '2' : 2, 
                '3' : 3,
            }
    return result
        
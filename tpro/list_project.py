#!/usr/bin/env python3

import glob
import argparse
import numpy as np
import subprocess

def system1(cmd):
    out = subprocess.check_output(cmd,shell=True)
    return out 

def print_list(psts):
    for pst in psts:
        pp = '/'.join(pst.split('/')[-3:]) 
    if args.xped:
        for pst in psts:
            pp = '/'.join(pst.split('/')[-3:])
            xped = system1('get_season '+ '/'.join(pst.split('/')[-3:]))
            print(pp, xped.decode('ascii').rstrip('\n'))
    else:
        for pst in psts:
         print('/'.join(pst.split('/')[-3:]))
        
def print_sets(psts):
    sets = []
    xped = []
    for pst in psts:
        sets.append(pst.split('/')[-2])
    print('==== sets ====')
    print(np.unique(sets))


def make_list(args):

    WAIS= '/disk/kea/WAIS/'
    CHA = '/disk/kea/CHA/'

    psts = glob.glob(WAIS+f'targ/xtra/*/CMP/pik1/{args.proj}/*/*')
    print('==== WAIS ====')
    if len(psts) > 0:
        print_list(psts)
        print_sets(psts)
        
    psts = glob.glob(CHA+f'targ/xtra/*/CMP/pik1/{args.proj}/*/*')
    print('==== CHA ====')
    if len(psts) > 0:
        print_list(psts)

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('proj',help='project to list')
    parser.add_argument('-xped',action='store_true',help='print xped of each pst')
    args = parser.parse_args()

    make_list(args)

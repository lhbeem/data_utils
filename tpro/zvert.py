#!/usr/bin/env python

import os
import glob 
import subprocess
import argparse

def zvert(proj,set,tran,radar,tpro,CHA):

    if not CHA:
        WAIS = 'WAIS'
    else:
        WAIS='CHA'
    
    if tpro not in ['thk','bed','srf','echo','spec','rad_pos','all']:
        print('{}: tpro product not supported')
        exit()
    
    if tpro in ['thk','bed','srf','echo','spec']:
	    datadir = os.path.join('/disk/kea/',WAIS,'targ/tpro',proj,set,tran)
    else:
        if not CHA:
            datadir = os.path.join('/disk/qnap-3/wais/targ/treg',proj,set,tran,)    
        else:
            datadir = os.path.join('/disk/qnap-3/cha/targ/treg',proj,set,tran,) 
    if tpro in ['thk']:
        prod = 'p_'+radar+'_icethk/ztim_llh_icethk.bin'
        folder_name = radar+'_'+tpro
    elif tpro in ['echo']:
        prod = 'p_'+radar+'_echo/ztim_llehr_bedeco.bin'
        folder_name = radar+'_'+tpro
    elif tpro in ['bed']:
        prod = 'p_'+radar+'_bedelv/ztim_llz_bedelv.bin'
        folder_name = radar+'_'+tpro
    elif tpro in ['spec']:
        prod = 'p_spec/ztim_lls_spec.bin'
        folder_name = tpro
    elif tpro in ['srf']:
        prod = 'p_'+radar+'_rad_srfelv/ztim_llz_srfelv.bin'
        folder_name = radar+'_'+tpro
    elif tpro in ['rad_pos']:
        prod = 'PIK1_*/ztim_llz.bin'
        folder_name = tpro

    for transect in glob.glob(datadir):
        filename = '_'.join(transect.split('/')[-3:]) 
        direct = '{}_{}'.format(transect.split('/')[-3],folder_name)
        outdir = '/disk/tio/WAIS/home/wais/users/lhb/{}'.format(direct)
        if not os.path.isdir(outdir):
            os.mkdir(outdir)
        cmd = 'zvert {}/{} >{}/{}'.format(transect,prod,outdir,filename)
        print(cmd)
        subprocess.call(cmd, shell=True)

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('proj',type=str, help='project if wildcard operators are desired enclose argument in double quotes')
    parser.add_argument('set',type=str, help='set if wildcard operators are desired enclose argument in double quotes')
    parser.add_argument('tran',type=str, help='transect if wildcard operators are desired enclose argument in double quotes')
    parser.add_argument('radar',type=str, help='radar processor (pik1, foc1, foc2)')
    parser.add_argument('tpro',type=str, help='tpro product to analyze [thk, bed, srf, echo,spec,rad_pos], ''all'' does all except rad_pos')
    parser.add_argument('-CHA',action='store_true',help='flag to use CHA root')
    args = parser.parse_args()
    
    if (args.tpro in ['thk','bed','srf','echo','rad_pos']) & (args.radar not in ['pik1','foc1','foc2']):
        print('the tpro product {} requires a radar product argument'.format(tpro))
        exit()
    if args.tpro == 'all':
        for tp in ['thk','bed','srf','echo','spec']:
            zvert(args.proj, args.set, args.tran, args.radar, tp, args.CHA)

    else:
        zvert(args.proj, args.set, args.tran, args.radar, args.tpro, args.CHA)

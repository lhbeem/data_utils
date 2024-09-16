#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# scp -P 2222 /Volumes/projects/one_off_scripts/make_elv_radargram.py wais-lhb@freeze.ig.utexas.edu:/disk/kea/WAIS/home/wais/users/lhb/elv_radargram
# scp -P 2222 wais-lhb@freeze.ig.utexas.edu:/disk/kea/WAIS/home/wais/users/lhb/elv_radargram/figures/elv_radgram_THW_UBH0c_X60a.png /Users/lhbeem/Desktop


'''
make an elvation corrected radargram

height of the aircraft
    $WAIS/targ/treg/{PST}/PIK1_{platform}a/ztim_llz.bin
surface pick comes from the targ-propgated pick
    $WAIS/targ/xtra/{XEPD}/CMP/pik1/{PST}/MagLoResInco1.srf
srf elevation come from differenceing the aircraft height from the radar range
    - assuming wavespeed args.cair
    - assuming main bang offset args.bang

'''

import numpy as np
import matplotlib.pylab as pl
import matplotlib
import argparse
import os 
import subprocess
matplotlib.use('Agg')
import pyproj

def main(args):
    
    if args.pole == 'south':
        P = pyproj.Proj('EPSG:3031')
    elif args.pole == 'north':
        P = pyproj.Proj('EPSG:3413')
    else:
        print('args.pole not north or south : {}'.format(args.pole))
    
    
    if args.product in ['pik1']:
        rad_filename = '{}/targ/xtra/{}/CMP/pik1/{}/MagLoResInco{}'.format(args.WAIS,args.xped,args.pst,args.chan)
        pick_filename= '{}/targ/xtra/{}/PIK/pik1/{}/MagLoResInco1.srf'.format(args.WAIS,args.xped,args.pst)
    elif args.product in ['foc1']: 
        rad_filename = '{}/targ/xtra/{}/FOC/Best_Versions/S5_VEW/{}/M1D{}'.format(args.WAIS,args.xped,args.pst,args.chan)
        pick_filename= '{}/targ/xtra/{}/PIK/Best_Versions/S5_VEW/{}/M1D1.srf'.format(args.WAIS,args.xped,args.pst)
    elif args.product in ['foc2']:
        rad_filename = '{}/targ/xtra/{}/FOC/Best_Versions/S5_VEW/{}/M2D{}'.format(args.WAIS,args.xped,args.pst,args.chan)
        pick_filename= '{}/targ/xtra/{}/PIK/Best_Versions/S5_VEW/{}/M2D1.srf'.format(args.WAIS,args.xped,args.pst)
    else:
        print( 'radar product not recognized: {}'.format(args.product) )
    
    
    # load RAD
    count = os.path.getsize(rad_filename) / 4
    sweeps = int(count / args.samples)
    rad = np.rot90(np.memmap(rad_filename, '>i4', mode='r', shape=(sweeps, args.samples)),-1)
    rad = np.fliplr(rad) # to align with srf picking direction
    
    
    if args.flip: # flip to create orientation desired for display
        print('flipping')
        rad = np.fliplr(rad)
        
    # load aircraft height
    platform = args.pst.split('/')[1][:3]
    hgt_file = '{}/targ/treg/{}/PIK1_{}a/ztim_llz.bin'.format(args.WAIS,args.pst,platform)
    zvert_hgt = '/disk/kea/WAIS/home/wais/users/lhb/elv_radargram/tmp/hgt'
    
    cmd = 'zvert {} >{}'.format(hgt_file,zvert_hgt)
    subprocess.call(cmd, shell=True)
    hgt_data = np.loadtxt(zvert_hgt,usecols=[3,4,5])  # lon, lat, height
    hgt = hgt_data[:,2]
    

     
    #load srf pick
    f = open(pick_filename,'r')
    pick = []
    for line in f:
        if line.startswith('P'):
            d = line.split()[1:]
            l = []
            for ele in d:
                if ele in 'x':
                    l.append(np.nan)
                else:
                    l.append(float(ele))
            
            pick.append( l )
    pick = np.array(pick)[:,0] #use vmax picks
    
    # determine srf_elv
    srf_elv = hgt - (pick-args.bang) / 2 / args.F * args.cair
    max_srf = np.nanmax(srf_elv)
    
    #load bed_elv
    bed_filename = '{}/targ/tpro/{}/p_{}_bedelv/ztim_llz_bedelv.bin'.format(args.WAIS,args.pst,args.product)
    zvert_bed = '/disk/kea/WAIS/home/wais/users/lhb/elv_radargram/tmp/bed'
    cmd = 'zvert {} >{}'.format(bed_filename, zvert_bed)
    subprocess.call(cmd, shell=True)
    min_bed = np.nanmin(np.loadtxt(zvert_bed,usecols=5))
    
    
    
    
    # make radargram
    print(args.pst)
    print('traces:  ',rad.shape[1],'\npickfile:',len(pick),'\nRADPOS:  ',len(hgt))
    
    dz = args.c / 2 / args.F #distance radar travels per sample
    z = np.arange(10000,-10000,-dz)
    rad_adj = np.zeros((len(z), len(srf_elv)))
    for i,elv in enumerate(srf_elv):
        if np.isnan(elv):
            continue
        anchor = int((z[0] - elv) / dz)
        io = int(pick[i])
        zlen = 3200 - io 
        rad_adj[anchor:anchor + zlen,i ] = rad[io:,i]
       
    zi1 = int((z[0] - max_srf) / dz) - 50
    zi2 = int((z[0] - min_bed) / dz) + 50
    rad_adj = rad_adj[zi1:zi2,:]
    
    #track distance estimate (first and last, assumed constant speed)
    x,y = P(hgt_data[:,0],hgt_data[:,1])
    
    d = np.cumsum( np.sqrt( (x[1:] - x[:-1]) **2 + (y[1:] - y[:-1]) **2)) / 1000 # km
    d = np.insert(d,0,0)
    dx = d[-1] 
    
    asp = dx / (z[zi1]- z[zi2]) / 1.6
    
    
    if args.contrast == 'high':
        v0 = 100000
        v1 = 200000
    elif args.contrast == 'low':
        v0 =  0
        v1 = 180000
    else:
        print('Constrast not recognized (high or low): {}'.format(args.contrast) )
    
    
    
    # plot radargram
    figname = '_'.join( args.pst.split('/') )
    
    fig = pl.figure(1)
    fig.clf()
    
    pl.imshow(rad_adj,cmap='Greys_r',extent=[0,dx,z[zi2],z[zi1]], vmin=v0,vmax=v1,aspect=asp)
    pl.ylabel('Elevation (m)')
    pl.xlabel('Distance along profile (km)')
    fig_file = '/disk/kea/WAIS/home/wais/users/lhb/elv_radargram/figures/{}/{}.png'.format(args.product, figname)
    fig.savefig(fig_file,dpi=300)
    print('saved: {}'.format(fig_file))
    
    
    if args.vp:
        
        fig = pl.figure(1)
        fig.clf()
        
        pl.imshow(rad_adj,cmap='Greys_r',extent=[0,dx,z[zi2],z[zi1]], vmin=v0,vmax=v1,aspect=asp)
        pl.title(args.pst)
        pl.plot(np.linspace(0,dx,len(d)), srf_elv, label = 'srf elv')
        pl.plot(np.linspace(0,dx,len(d)), hgt, label = 'platform alt')
        pl.plot(np.linspace(0,dx,len(d)), pick, label = 'srf pick sample')
        pl.ylabel('Elevation (m)')
        pl.xlabel('Disstance along profile (km)')
        
        pl.legend()
        fig_file = '/disk/kea/WAIS/home/wais/users/lhb/elv_radargram/figures/{}/{}2.png'.format(args.product, figname)
        fig.savefig(fig_file,dpi=300)
        print('saved: {}'.format(fig_file))

    
    if args.raster:
        raster_file = '/disk/kea/WAIS/home/wais/users/lhb/elv_radargram/raster/{}/{}'.format(args.product, figname)
        np.savez(raster_file,rad = rad_adj, z = z[zi1:zi2] , d = d)
        print(f'saved: {raster_file}.npz')
        print(d[-1], d[0])

if __name__=="__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('pst',help='PST to generate radargram')
    parser.add_argument('product', help='radar product to check (pik1, foc1, foc2)')
    parser.add_argument('chan', help='radar channel to plot')
    parser.add_argument('-WAIS',default=os.getenv('WAIS'), help="WAIS root path variable")
    parser.add_argument('-c',default=1.67e8, help="radar wave speed in ice")
    parser.add_argument('-cair',default=2.99e8, help="radar wave speed in air")
    parser.add_argument('-contrast', default='high',help='constrast [''high'' or ''low'']')
    parser.add_argument('-flip', action='store_true', help='flip radargram orientation')
    parser.add_argument('-samples', default = 3200, help='samples per trace')
    parser.add_argument('-F', default = 50e6, help='sample frequency')
    parser.add_argument('-bang', default = 115, help='main bang offset in samples')
    parser.add_argument('-vp', action='store_true', help='verbose printing (i.e. second page with source data)')
    parser.add_argument('-pole', default= 'south', help = 'pole of data region (south or north')
    parser.add_argument('-raster', action='store_true', help='save copy of raster as .npz [rad,z,d]') 
    args = parser.parse_args()

    args.xped = subprocess.check_output(['get_season ' + args.pst], shell=True).decode()[:-1]
                          
    main(args)


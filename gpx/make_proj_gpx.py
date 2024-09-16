#!/usr/bin/env python3


"""

Creates a synopsis of an PROJ as a GPX or a space-delimited table.

For example, if you want to create a GPX of all transects in THW, 
and output that to /tmp/synoptic_tracks.

./make_synoptic_track.py --proj THW -o /tmp/synoptic_tracks

If you wanted to get a synopsis for the season CHA5, a CHINARE season,
use the --WAIS flag 

./make_synoptic_track.py --WAIS /disk/kea/CHA --proj AMY -o /tmp/synoptic_tracks


If you want to output as a space-delimited table of points rather than a GPX, 
use the --format table option


./make_synoptic_track.py --WAIS /disk/kea/CHA --proj AMY -o /tmp/synoptic_tracks --format table

"""



import os
import sys
import argparse
import logging
import glob
import traceback
import collections
import datetime

import gpxpy
import gpxpy.gpx

SET_PST_BLACKLIST = set([
    # Bogus transect names
    'prj/set/trn',
    ])


def main():
    global zutils, waisxped

    parser = argparse.ArgumentParser(description='Create a synopsis of flights per season')
    parser.add_argument('-o', '--output', help='Output directory', required=False, default='./output')
    parser.add_argument('-d', '--maxdistance', type=int, default=50.0, help='Simplification distance')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--format', default='gpx', choices=('gpx', 'table'), help='Output format')
    parser.add_argument('--WAIS', default=os.getenv('WAIS'), help='WAIS root path variable')
    parser.add_argument('--proj', default=os.getenv('QXPED'), help='project to process')
    args = parser.parse_args()


    LOGLEVEL = logging.DEBUG if args.verbose else logging.INFO

    logging.basicConfig(level=LOGLEVEL, stream=sys.stdout,
                    format='mst: [%(levelname)-5s] %(message)s',
                    )

    # if not args.xped:
    #     raise ValueError('Set expedition with --xped argument')


    if not args.WAIS:
        raise ValueError('Set WAIS variable with --WAIS argument')


    # Add syst to the path
    sys.path.insert(0, os.path.join(args.WAIS, 'syst/linux/py'))
    import zutils.zfile
    # import waisutils.xped as waisxped

    normdir = os.path.join(args.WAIS, 'targ/norm')
    outdir = args.output if not args.output else args.output

    if args.format == 'gpx':
        outfile = os.path.join(outdir, '{:s}.gpx'.format(args.proj.lower()))
        make_synoptic_gpx( normdir, outfile, args.proj, args.maxdistance)
    else:
        assert args.format == 'table'
        outfile = os.path.join(outdir, '{:s}.txt'.format(args.proj.lower()))
        make_synoptic_table( normdir, outfile, args.maxdistance)


def make_synoptic_table(normdir, outfile, proj, max_distance=50.0):
    gpx = collect_tracks_to_gpx( normdir, outfile, proj, max_distance)

    logging.info("Writing " + outfile)
    with open(outfile, 'wt') as fout:
        for gpx_track in gpx.tracks:
            pst = gpx_track.name
            for gpx_seg in gpx_track.segments:
                for point in gpx_seg.points:
                    stime = point.time.strftime('%Y-%m-%dT%H:%M:%S')
                    line = "{0:s} {1:s} {2.longitude:0.6f} {2.latitude:0.6f} " \
                           "{2.elevation:0.1f}\n".format(pst, stime, point)
                    fout.write(line)


def make_synoptic_gpx(normdir, outfile, proj, max_distance=50.0):
    gpx = collect_tracks_to_gpx( normdir, outfile, proj, max_distance)

    logging.info("Writing " + outfile)
    with open(outfile, 'wt') as fout:
        fout.write(gpx.to_xml())

def collect_tracks_to_gpx( normdir, outfile, proj, max_distance=50.0):
    outdir = os.path.dirname(outfile)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    logging.info("Collecting transects for {:s} from {:s}".format(proj, normdir))
    # Get list of xped PSTs under norm
    trackdirlist = [rec for rec in getpsts(normdir, proj)]
    trackdirlist.sort()    # sort by time, then by pst
    logging.info("Got {:d} transects".format(len(trackdirlist)))

    gpx = gpxpy.gpx.GPX()
    for t0, pst, pstdir in trackdirlist:
        # Create track in our GPX
        gpx_track = gpxpy.gpx.GPXTrack(name=pst)
        gpx_track.source = pstdir
        # Create segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        logging.debug("Parsing " + pstdir)
        for ii, rec in enumerate(read_norm_gps(pstdir)):
            # Convert from a ztim to a ISO-8601 string (nearest second)
            unixtime = round(zutils.zfile.ztim_to_posix(rec.ztim), 0)
            time1 = datetime.datetime.utcfromtimestamp(unixtime)
            lat, lon, alt = round(rec.lat, 6), round(rec.lon, 6), round(rec.alt, 1)
            pt = gpxpy.gpx.GPXTrackPoint(time=time1, latitude=lat, longitude=lon, elevation=alt)
            gpx_segment.points.append(pt)

        gpx_track.simplify(max_distance=max_distance)
        if len(gpx_segment.points) >= 1:
            st0 = gpx_segment.points[0].time.strftime('%Y-%m-%dT%H:%M:%S')
            st1 = gpx_segment.points[-1].time.strftime('%Y-%m-%dT%H:%M:%S')
            dt = (gpx_segment.points[-1].time - gpx_segment.points[0].time).seconds / 60.0
        else:
            st0, st1 = '?', '?'
            dt = float('nan')
        gpx_track.comment = "PST: {:s}\nStart Time: {:s}\nEnd Time: {:s}\nDuration: {:0.2f} minutes\nSource: {:s}" \
                        "".format(pst, st0, st1, dt,  pstdir)
        # If everything seems fine, add it to the track.
        gpx.tracks.append(gpx_track)

    return gpx


def getpsts(normdir, proj):
    """ Get the time of the xped from syst/linux/py
    exception out, if xped is not found in syst/linux/py
    Inspect the GPS files for matching times
    Yields pst and directory corresponding to that PST
    """

    # try:
    #     xpedtimes = waisxped.xped_times[xped]
    #     logging.debug("xped {:s} has times from {:s}".format(xped, str(xpedtimes)))
    # except KeyError:
    #     logging.error("xped '{:s}' was not found in waisutils".format(xped))
    #     raise

    for dirname in glob.iglob(os.path.join(normdir, f'{proj}/*/*')):
        if not os.path.isdir(dirname):
            continue
        for cname in sorted(os.listdir(dirname)):
            r1 = os.path.join(dirname, cname)
            # Filter for certain cnames. Should we allow POS also?
            if not cname.startswith('GPS_') or not os.path.isdir(r1):
                continue

            # Parse and filter according to PST
            pstfields = dirname.split(os.path.sep)[-3:]
            pst = os.path.join(*pstfields)

            # # Filter for set, if specified
            # if xpedtimes[2] and xpedtimes[2] not in pstfields[1]:
            #     continue

            # if pst in SET_PST_BLACKLIST:
            #     continue


            tt = None
            path1 = os.path.join(r1, 'syn_ztim')
            # minimum size of a file that has 2 ztims in it
            if not os.path.exists(path1) or os.path.getsize(path1) < 20:
                continue

            try:
                tt = zutils.zfile.get_ztim_range_posix(path1)
            except:
                logging.warning("PST={:s} Problem parsing {:s}:".format(pst, path1))
                for line in traceback.format_exc().split("\n"):
                    logging.warning("PST={:s} {:s}".format(pst, line))
                continue
            if tt[0] >= tt[1]:
                logging.warning("PST {:s} started after it ended!".format(pst))
                continue

            # if not (xpedtimes[0] <= tt[0] <= xpedtimes[1] or
            #         xpedtimes[0] <= tt[1] <= xpedtimes[1]):
            #     continue


            yield tt[0], pst, r1
            # only do one cname per transect
            break

def nan_generator():
    while True:
        yield 'nan'

def read_norm_gps(normdir):
    """ Read a norm directory line-by-line and return namedtuples for each track point """
    TrackPoint = collections.namedtuple('TrackPoint', 'ztim lon lat alt')
    fhlon, fhlat, fhalt = None, None, None
    altfile = os.path.join(normdir, 'vert_cor')
    try:
        # Open each individual file as text, except for the syn_ztim file, which
        # we invoke the pre-made reader that returns tuples that parse the ztim.
        ztim_gen = zutils.zfile.read_ztim_text(os.path.join(normdir, 'syn_ztim'))
        fhlon = open(os.path.join(normdir, 'lon_ang'), 'rt')
        fhlat = open(os.path.join(normdir, 'lat_ang'), 'rt')
        if os.path.exists(altfile): # altitude is optional
            fhalt = open(altfile, 'rt')
        else: #pragma: no-cover
            fhalt = nan_generator()

        for ii, rec in enumerate(zip(ztim_gen, fhlon, fhlat, fhalt)):
            if ii == 0:
                logging.debug("[0] " + str(rec))
            trackpt = TrackPoint(rec[0], float(rec[1]), float(rec[2]), float(rec[3]))
            # Filter out trackpoints with bad times (nans)
            if trackpt.lat != trackpt.lat or trackpt.lon != trackpt.lon:
                continue

            yield trackpt
    except FileNotFoundError:
        logging.error("Missing files in " + normdir)
    finally:
        if fhlon:
            fhlon.close()
        if fhlat:
            fhlat.close()
        if os.path.exists(altfile):
            fhalt.close()

if __name__ == "__main__":
    main()


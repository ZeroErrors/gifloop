#!/usr/bin/env python3

import os
import sys
import sqlite3
import argparse
from typing import Optional
from functools import partial
from multiprocessing import Pool
from subprocess import check_call, check_output, STDOUT, DEVNULL


def merge(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def find_line(arr, s):
    for a in arr:
        try:
            if a.index(s) >= 0:
                return a
        except ValueError:
            continue
    return ''


def update_progress(key, current, total, length=30):
    progress = min(max(current / total, 0), 1)
    blocks = int(round(length * progress))
    bar = '#' * blocks + '-' * (length - blocks)
    line = f'\r{key}: [{bar}] {progress * 100:6.2f}% {current}/{total}'
    sys.stdout.write(line)
    if progress >= 1:
        sys.stdout.write('\n\r')
    sys.stdout.flush()


def clean(args):
    if os.path.isdir(args.analyze_frames_dir):
        for f in os.listdir(args.analyze_frames_dir):
            full_path = os.path.join(args.analyze_frames_dir, f)
            if os.path.isfile(full_path) and f.endswith('.png'):
                os.remove(full_path)

    if os.path.isfile(args.analyze_result_file):
        os.remove(args.analyze_result_file)

    if os.path.isfile(args.gif_palette_file):
        os.remove(args.gif_palette_file)


def compare_ssim(comp, args):
    if comp['value'] != -1:
        return comp

    fr = comp['from']
    to = comp['to']
    output = check_output([
        'ffmpeg',
        '-hide_banner',
        '-nostats',
        # '-hwaccel' if args.hardware_acceleration else None,
        '-i', os.path.join(args.analyze_frames_dir, f'{fr:d}.png'),
        '-i', os.path.join(args.analyze_frames_dir, f'{to:d}.png'),
        '-lavfi', 'ssim',
        '-f', 'null',
        '–'
    ], stderr=STDOUT)

    if args.verbose > 1:
        print(output.decode('utf-8'))

    comp['value'] = float(between(output, b'All:', b' '))
    return comp


def compare_psnr(comp, args):
    if comp['value'] != -1:
        return comp

    fr = comp['from']
    to = comp['to']
    output = check_output([
        'ffmpeg',
        '-hide_banner',
        '-nostats',
        # '-hwaccel' if args.hardware_acceleration else None,
        '-i', os.path.join(args.analyze_frames_dir, f'{fr:d}.png'),
        '-i', os.path.join(args.analyze_frames_dir, f'{to:d}.png'),
        '-lavfi', 'psnr',
        '-f', 'null',
        '–'
    ], stderr=STDOUT)

    if args.verbose > 1:
        print(output.decode('utf-8'))

    comp['value'] = float(between(output, b'average:', b' '))
    return comp


comparison_types = {
    'ssim': compare_ssim,
    'psnr': compare_psnr
}


def run(args):
    stdout = DEVNULL
    stderr = DEVNULL
    if args.verbose > 0:
        stdout = None
        stderr = None

    # Get info about the input file
    input_info = check_output([
        'ffmpeg',
        '-hide_banner',
        '-nostats',
        # '-hwaccel' if args.hardware_acceleration else None,
        '-i', args.input_file,
        '-map', '0:v:0',
        '-c', 'copy',
        '-f', 'null',
        '-'
    ], stderr=STDOUT)

    if args.verbose > 0:
        print(input_info.decode('utf-8'))

    frame_count = int(between(input_info, b'frame=', b'fps='))
    frame_rate = float(between(find_line(input_info.split(b'\n'), b'Video:'), b'kb/s,', b'fps, '))
    print(f'Input - {frame_count} frames @ {frame_rate} fps')
    # TODO: Get input frame size and default gif and analyze accordingly

    analyze_frame_rate = args.analyze_frame_rate or frame_rate

    # TODO: Invalidate/Force if settings or input changed?
    if not os.path.isdir(args.analyze_frames_dir):
        if os.path.exists(args.analyze_frames_dir):
            raise Exception(f'Frames dir exists but isn\'t a directory: {args.analyze_frames_dir}')

        os.mkdir(args.analyze_frames_dir)

        # Export frames from file
        print(f'Exporting frames from \'{args.input_file}\' into \'{args.analyze_frames_dir}\' ...')
        check_call([
            'ffmpeg',
            '-hide_banner',
            '-nostats',
            # '-hwaccel' if args.hardware_acceleration else None,
            '-i', args.input_file,
            '-vf', f'scale=-1:{args.analyze_frame_height}:flags=lanczos,fps={analyze_frame_rate}',
            args.analyze_frames_dir + '/%d.png'
        ], stdout=stdout, stderr=stderr)

    analyze_frame_count = 0
    for f in os.listdir(args.analyze_frames_dir):
        if os.path.isfile(os.path.join(args.analyze_frames_dir, f)) and f.endswith('.png'):
            analyze_frame_count += 1

    print(f'Analyze - {analyze_frame_count} frames @ {analyze_frame_rate} fps')

    analyze_skip_frames = args.analyze_skip_frames or int(analyze_frame_rate * 0.5)
    analyze_max_frames = args.analyze_max_frames or int(analyze_frame_rate * args.gif_max_length)

    conn = sqlite3.connect(args.analyze_result_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        'from' INT NOT NULL, 
        'to' INT NOT NULL,
        'value' REAL NOT NULL,
        PRIMARY KEY ('from', 'to')
    )''')
    conn.commit()

    values = []
    print('Loading Existing Frame Results...')
    for i in range(analyze_frame_count - analyze_skip_frames):
        start = i + analyze_skip_frames
        for x in range(start, min(analyze_frame_count, start + analyze_max_frames)):
            value = {
                'from': i + 1,
                'to': x + 1,
                'value': -1
            }
            c.execute('SELECT value FROM results WHERE "from"=? and "to"=?', (value['from'], value['to']))
            result = c.fetchone()
            if result is not None:
                value['value'] = result[0]
            values.append(value)

    print('Analyzing Frames...')
    # TODO: Add binary search frame comparison
    frames = []
    with Pool(processes=args.processes) as p:
        compare = partial(comparison_types[args.analyze_compare_type], args=args)
        for value in p.imap(compare, values):
            frames.append(value)
            update_progress('Frames', len(frames), len(values))
            c.execute('INSERT OR IGNORE INTO results VALUES (?, ?, ?)', (value['from'], value['to'], value['value']))
            conn.commit()

    conn.close()

    # TODO: Just use sqlite to find the max value?
    value = max(frames, key=lambda v: v['value'])
    value['from_input'] = value['from'] * (frame_rate / analyze_frame_rate)
    value['to_input'] = value['to'] * (frame_rate / analyze_frame_rate)

    start_frame = value['from_input']
    end_frame = value['to_input']

    print(f'Output - {end_frame - start_frame} frames @ {args.gif_frame_rate or frame_rate} fps')
    print(f"\nBest Looping Gif is: ({value['value']})\n"
          f"\tAnalyzed frames {value['from']} to {value['to']}\n"
          f"\tInput frames {start_frame} to {end_frame}")

    # TODO: Invalidate/Force if settings or input changed?
    if not os.path.isfile(args.gif_palette_file) or not os.path.isfile(args.gif_output_file):
        if os.path.exists(args.gif_palette_file):
            raise Exception(f'Gif palette file exists but isn\'t a file: {args.gif_palette_file}')
        if os.path.exists(args.gif_output_file):
            raise Exception(f'Gif output file exists but isn\'t a file: {args.gif_output_file}')

        extra = ''
        if args.gif_frame_rate is not None:
            extra += f',fps={args.gif_frame_rate}'
        if args.gif_frame_height is not None:
            extra += f',scale=-1:{args.gif_frame_height}:flags=lanczos'

        check_call([
            'ffmpeg',
            '-hide_banner',
            '-nostats',
            # '-hwaccel' if args.hardware_acceleration else None,
            '-y',
            '-i', args.input_file,
            '-vf', f'trim=start_frame={start_frame}:end_frame={end_frame}{extra},palettegen',
            args.gif_palette_file
        ], stdout=stdout, stderr=stderr)

        check_call([
            'ffmpeg',
            '-hide_banner',
            '-nostats',
            # '-hwaccel' if args.hardware_acceleration else None,
            '-i', args.input_file,
            '-i', args.gif_palette_file,
            '-filter_complex', f'trim=start_frame={start_frame}:end_frame={end_frame}{extra}[x];[x][1:v]paletteuse',
            args.gif_output_file
        ], stdout=stdout, stderr=stderr)

    if args.clean:
        clean(args)


parser = argparse.ArgumentParser()
parser.add_argument('input_file',
                    metavar='file',
                    help='The input file to process')
# Output gif options
parser.add_argument('-o', '--output',
                    metavar='file',
                    default='output.gif',
                    dest='gif_output_file',
                    help='The file to store the output gif')
parser.add_argument('-p', '--palette',
                    metavar='file',
                    default='palette.png',
                    dest='gif_palette_file',
                    help='The file to store the output gif palette')
parser.add_argument('-H', '--height',
                    metavar='pixels',
                    dest='gif_frame_height',
                    type=int,
                    help='The height of the output gif')
parser.add_argument('-f', '--fps',
                    metavar='fps',
                    dest='gif_frame_rate',
                    type=float,
                    help='The frame rate of the output gif')
parser.add_argument('-l', '--length',
                    metavar='seconds',
                    default=999999999,
                    dest='gif_max_length',
                    type=float,
                    help='The maximum length of the output gif')
# Frame analyze options
parser.add_argument('-t', '--analyze-type',
                    default='psnr',
                    choices=comparison_types.keys(),
                    dest='analyze_compare_type',
                    help='The algorithm to use when analyzing frames')
parser.add_argument('-r', '--results',
                    metavar='file',
                    default='results.db',
                    dest='analyze_result_file',
                    help='The file to store the frame analyze results')
parser.add_argument('-d', '--frames-dir',
                    metavar='dir',
                    default='frames',
                    dest='analyze_frames_dir',
                    help='The directory to store the exported frames')
parser.add_argument('-A', '--analyze-height',
                    metavar='pixels',
                    default=360,
                    dest='analyze_frame_height',
                    type=int,
                    help='The height of the exported frames to analyze')
parser.add_argument('-F', '--analyze-fps',
                    metavar='fps',
                    dest='analyze_frame_rate',
                    type=float,
                    help='The frame rate of the exported frames to analyze')
parser.add_argument('--skip-frames',
                    metavar='frames',
                    dest='analyze_skip_frames',
                    type=int,
                    help='The number of frames to skip when analyze frames')
parser.add_argument('--max-frames',
                    metavar='frames',
                    dest='analyze_max_frames',
                    type=int,
                    help='The maximum number of frames to analyze')
# Misc options
parser.add_argument('--processes',
                    metavar='n',
                    default=None,
                    type=Optional[int],
                    help='The number of parallel task to run when analyzing frames')
# parser.add_argument('--hwaccel',
#                    default=True,
#                    dest='hardware_acceleration',
#                    action='store_true',
#                    help='Enables hardware acceleration via the "-hwaccel" argument to ffmpeg')
parser.add_argument('-c', '--clean',
                    action='store_true',
                    help='Cleans up the files when finished')
parser.add_argument('-v', '--verbose',
                    default=0,
                    action='count',
                    help='Increase the logging verbosity')

if __name__ == '__main__':
    run(parser.parse_args())

import os
import argparse
from typing import Optional
from subprocess import check_call, DEVNULL


def generate_gif(args, file_name, ext, extra, fps, width, height):
    stdout = DEVNULL
    stderr = DEVNULL
    if args.verbose > 0:
        stdout = None
        stderr = None

    size_str = 'orig'
    if width is not None and height is not None:
        extra += f'scale={width}:{height}:flags=lanczos,'
        size_str = str(width) + 'x' + str(height)
    elif width is not None:
        extra += f'scale={width}:-1:flags=lanczos,'
        size_str = str(width) + 'x-1'
    elif height is not None:
        extra += f'scale=-1:{height}:flags=lanczos,'
        size_str = '-1x' + str(height)
    file_name += '_' + size_str

    fps_str = 'orig'
    if fps is not None:
        extra += f'fps={fps},'
        fps_str = f'{fps:g}'
    file_name += '_' + fps_str

    if os.path.exists(file_name + ext):
        print('Skipping GIF because it already exists: ' + file_name + ext)
        return

    print('Making GIF: ' + file_name + ext)

    palette_file = 'palette_' + file_name + '.png'

    check_call([
        'ffmpeg',
        '-hide_banner',
        '-nostats',
        '-y',
        '-i', args.input_file,
        '-vf', f'{extra}palettegen',
        palette_file
    ], stdout=stdout, stderr=stderr)

    if extra.endswith(','):
        extra = extra[:-1]

    check_call([
        'ffmpeg',
        '-hide_banner',
        '-nostats',
        '-i', args.input_file,
        '-i', palette_file,
        '-filter_complex', f'{extra}[x];[x][1:v]paletteuse',
        file_name + ext
    ], stdout=stdout, stderr=stderr)

    print("\tFinished!")


def run(args):
    output_split = os.path.splitext(args.gif_output_file or args.input_file)
    file_name = output_split[0]
    ext = '.gif'
    if args.gif_output_file is not None:
        ext = output_split[1]

    extra = ''
    frame_str = 'orig'
    if args.start_frame is not None and args.end_frame is not None:
        extra += f'trim=start_frame={args.start_frame}:end_frame={args.end_frame},'
        frame_str = str(args.start_frame) + 'to' + str(args.end_frame)
    elif args.start_frame is not None:
        extra += f'trim=start_frame={args.start_frame},'
        frame_str = str(args.start_frame) + 'to-1'
    elif args.end_frame is not None:
        extra += f'trim=end_frame={args.end_frame},'
        frame_str = '-1to' + str(args.end_frame)
    file_name += '_' + frame_str

    for fps in args.gif_fps:
        # TODO: Async Fork
        generate_gif(args, file_name, ext, extra, fps, None, None)

    for size in args.gif_sizes:
        split = size.split('x')
        width = int(split[0]) if split[0] else None
        height = int(split[1]) if split[1] else None

        # TODO: Async Fork
        generate_gif(args, file_name, ext, extra, None, width, height)

    for fps in args.gif_fps:
        for size in args.gif_sizes:
            split = size.split('x')
            width = int(split[0]) if split[0] else None
            height = int(split[1]) if split[1] else None

            # TODO: Async Fork
            generate_gif(args, file_name, ext, extra, fps, width, height)


parser = argparse.ArgumentParser()
parser.add_argument('input_file',
                    metavar='file',
                    help='The input file to process')
# Output gif options
parser.add_argument('-f', '--fps',
                    metavar='fps',
                    dest='gif_fps',
                    nargs='+',
                    type=float,
                    help='The frame rate of the output gif')
parser.add_argument('-o', '--output',
                    metavar='file',
                    default='output.gif',
                    dest='gif_output_file',
                    help='The file to store the output gif')
parser.add_argument('-S', '--sizes',
                    metavar='sizes',
                    dest='gif_sizes',
                    nargs='+',
                    help='The output gif sizes in the format of {width}x{height}')
parser.add_argument('-s', '--start',
                    metavar='frame',
                    dest='start_frame',
                    type=int,
                    help='The first frame of the gif')
parser.add_argument('-e', '--end',
                    metavar='frame',
                    dest='end_frame',
                    type=int,
                    help='The last frame of the gif')
# Misc options
parser.add_argument('--processes',
                    metavar='n',
                    default=None,
                    type=Optional[int],
                    help='The number of parallel task to run when analyzing frames')
parser.add_argument('-v', '--verbose',
                    default=0,
                    action='count',
                    help='Increase the logging verbosity')

if __name__ == '__main__':
    run(parser.parse_args())

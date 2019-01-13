#!/usr/bin/env python3

import os
import json
import time

import gifloop

cwd = os.getcwd()
os.chdir(cwd)

for d in os.listdir('.'):
    os.chdir(cwd)
    if not os.path.isdir(d):
        continue

    os.chdir(os.path.join(cwd, d))

    config_file = 'config.json'
    if not os.path.isfile(config_file):
        continue

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    args = gifloop.parser.parse_args(['input_file'])
    for key, value in config.items():
        setattr(args, key, value)

    start = time.time()
    print(f'Running Example: {d}')
    print('----')
    gifloop.run(args)
    print(f'---- Took: {time.time() - start}')
    print()

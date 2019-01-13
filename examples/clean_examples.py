#!/usr/bin/env python3

import os
import json
import time

import gifloop

cwd = os.getcwd()

for d in os.listdir('.'):
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
    print(f'Cleaning Example: {d}')
    print('----')
    gifloop.clean(args)
    print(f'---- Took: {time.time() - start}')
    print()

    os.chdir(cwd)

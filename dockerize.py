#!/usr/bin/env python3

from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
import sys

import docker
from docker.utils.json_stream import json_stream


def parse_args():
    parser = ArgumentParser(description='Generate a Docker image from selected components')
    #parser.add_argument('--push', '-p', action='store_true', help='Push the resulting image to Docker Hub')
    parser.add_argument('--base', '-b', type=str, default='submitty/core:latest')
    parser.add_argument('tag', type=str)
    parser.add_argument('components', nargs='*', metavar='component')
    return parser.parse_args()


def main():
    client = docker.from_env()
    args = parse_args()
    dockerfile = BytesIO()
    dockerfile.write("FROM {}\n\n".format(args.base).encode('utf-8'))
    for component in args.components:
        with Path('components', component, 'Dockerfile.part').open() as component_dockerfile:
            dockerfile.write((component_dockerfile.read() + "\n\n").encode('utf-8'))
    # we need the " character around the command or else it doesn't work properly
    dockerfile.write("CMD [\"/bin/bash\"]\n".encode('utf-8'))
    
    parts = args.tag.split(':')
    name_parts = parts[0].split('/')
    metadata = {
        'hostname': name_parts[0],
        'name': name_parts[1],
        'tag': parts[1],
        'components': args.components
    }
    build_dir = Path('dockerfiles', metadata['hostname'], metadata['name'], metadata['tag'])
    build_dir.mkdir(parents=True, exist_ok=True)
    dockerfile.seek(0)
    Path(build_dir, 'Dockerfile').write_bytes(dockerfile.read())
    json.dump(metadata, Path(build_dir, 'metadata.json').open('w'), indent=2)
    
    return_status = 0
    image_id = None
    for line in json_stream(client.api.build(fileobj=dockerfile, tag=args.tag, rm=True, forcerm=True)):
        if 'stream' in line:
            print(line['stream'], end='')
        elif 'errorDetail' in line:
            print(line['errorDetail']['message'], file=sys.stderr)
            return_status = line['errorDetail']['code'] if 'code' in line['errorDetail'] else -1
        elif 'aux' in line:
            image_id = line['aux']['ID']
    #if return_status == 0 and args.push:
        # split the user input that is of the form <repo>:<tag>
    #    split = args.tag.split(':')
    #    print(split)
    #    for line in client.images.push(*split, stream=True):
    #        print(line)

if __name__ == '__main__':
    main()

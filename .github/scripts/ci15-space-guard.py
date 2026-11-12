"""Only skip broad runner cleanup with at least 10 GiB actually available."""
import argparse
import os
import shutil

MIN_FREE_BYTES = 10 * 1024**3


def cleanup_needed(available_bytes):
    if available_bytes < 0:
        raise ValueError('invalid available space')
    return available_bytes < MIN_FREE_BYTES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default='.')
    args = parser.parse_args()
    free = shutil.disk_usage(args.path).free
    needed = cleanup_needed(free)
    print(f'Available {free} bytes; minimum {MIN_FREE_BYTES}; cleanup_needed={needed}')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'cleanup_needed={str(needed).lower()}\n')


if __name__ == '__main__':
    main()

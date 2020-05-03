from pathlib import Path


def bytesto(bytes, from_='b', to='m', bsize=1024):
    """convert bytes to megabytes, etc.
       sample code:
           print('mb= ' + str(bytesto(314575262000000, 'm')))
       sample output:
           mb= 300002347.946
    """
    a = {'b': 0, 'k': 1, 'Ki': 1, 'm': 2, 'Mi': 2, 'g': 3, 'Gi': 3, 't': 4, 'Ti': 4, 'p': 5, 'Pi': 5, 'e': 6, 'Ei': 6}
    r = float(bytes)
    for i in range(a[from_], a[to]):
        r = r / bsize
    return r


def get_image_name(path, build_type):
    app_name = Path(path).stem
    postfix = f'-{build_type}' if build_type else ''
    return f'{app_name}{postfix}'.strip()


def merge_dicts(a, b, path=None):
    """merges b into a"""
    if path is None:
        path = []

    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def read_dot_env_file(env_file):
    d = {}
    with open(env_file, 'r') as f:
        for line in f:
            (key, val) = line.split('=')
            d[key] = val.rstrip()
    return d

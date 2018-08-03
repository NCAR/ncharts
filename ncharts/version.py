# Source: https://github.com/Changaco/version.py

from os.path import dirname, isdir, join
import re
from subprocess import CalledProcessError, check_output


PREFIX = 'v'

tag_re = re.compile(r'\btag: %s([0-9][^,]*)\b' % PREFIX)
version_re = re.compile('^Version: (.+)$', re.M)


def get_version():
    # Return the version if it has been injected into the file by git-archive
    version = tag_re.search('$Format:%D$')
    if version:
        return version.group(1)

    d = dirname(__file__)

    if isdir(join(d, '../.git')):
        # Get the version using "git describe".
        cmd = 'git describe --tags --match %s[0-9]* --dirty' % PREFIX
        try:
            version = check_output(cmd.split()).decode().strip()
        except CalledProcessError:
            # raise RuntimeError('Unable to get version number from git tags')
            version = 'unknown version'

        # PEP 440 compatibility
        if '-' in version:
            # if version.endswith('-dirty'):
            #     raise RuntimeError('The working tree is dirty')
            version = '-'.join(version.split('-')[:2])

    else:
        # Extract the version from the PKG-INFO file.
        try:
            with open(join(d, 'PKG-INFO')) as f:
                version = version_re.search(f.read()).group(1)
        except:
            version = 'unknown version'

    return version


if __name__ == '__main__':
    print(get_version())

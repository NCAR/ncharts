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

    version = PREFIX + '?'

    if isdir(join(d, '../.git')):
        # Get the version using "git describe".
        cmd = 'git describe --match %s[0-9]* --dirty' % PREFIX
        try:
            version = check_output(cmd.split()).decode().strip()

            exstr = ''
            if version.endswith('-dirty'):
                exstr = '+'
                version = version[:-6]
            if '-' in version:
                version = '-'.join(version.split('-')[:2])
            version += exstr

        except CalledProcessError:
            pass

    else:
        # Extract the version from the PKG-INFO file.
        try:
            with open(join(d, 'PKG-INFO')) as f:
                version = version_re.search(f.read()).group(1)
        except:
            pass

    return version


if __name__ == '__main__':
    print(get_version())

#!/usr/bin/env python
from pprint import pprint
import sys
import os
import logging
from logging import critical, error, info, warning, debug
import subprocess

CWORKING = '\033[34;1m'
# The 'color' we use to reset the colors
# @todo for some reason this is NOT resetting the colors after use
CRESET = '\033[0m\033[K'
# CRESET=$(tput sgr0 -T "${TERM}")
# bold, duh
CBOLD = '\033[1;96m'
# color we use for informational messages
CINFO = '\033[1;33m'
# color we use for warnings
CWARN = '\033[1;31m'
logging.basicConfig(format='%(message)s', level=logging.DEBUG, stream=sys.stdout)
logging.addLevelName(logging.WARNING, "%s%s%s" % (CWARN, logging.getLevelName(logging.WARNING), CRESET))
logging.addLevelName(logging.ERROR, "%s%s%s" % (CWARN, logging.getLevelName(logging.ERROR), CRESET))


def outputError(cmd, output):
    logging.warning("{}{}{}{} command failed!{}".format(CBOLD, cmd, CRESET, CWARN, CRESET))
    logging.info("See the following output:")
    logging.info(output)
    # @todo exit seems... dirty?
    # sys.exit("See previous error above")
    return False


def main():
    """

    :return:
    """
    updaters = {
        'composer.json': {'command': 'composer update', 'lock': 'composer.lock'},
        'Pipfile': {'command': 'pipenv update', 'lock': 'Pipfile.lock'},
        'Gemfile': {'command': 'bundle update --all', 'lock': 'Gemfile.lock'},
        'go.mod': {'command': 'go get -u all', 'lock': 'go.sum'},
        'package-lock.json': {'command': 'npm update', 'lock': 'package-lock.json'},
        'yarn.lock': {'command': 'yarn upgrade', 'lock': 'yarn.lock'}
    }

    logging.info("Beginning update process...")
    # get the path to our app. yes, it's different. in a source op container, we're in a different location
    appPath = os.getenv('PLATFORM_SOURCE_DIR')

    # grab the list of files in the app root
    # @todo for now this only supports single apps. we'll need to build in multiapp support
    appfiles = [file for file in os.listdir(appPath) if os.path.isfile(file) and file in updaters.keys()]

    if 1 > len(appfiles):
        return outputError('Gathering dependency definition file(s)',
                           "I was unable to locate any dependency definition files")

    actions = {}
    doCommit = False

    for file in appfiles:
        # @todo just to be safe, we should check to see if updaters has an entry for the file name before we use it
        actions[file] = updaters[file]
        # @todo later this needs to be updated to the *relative* directory location where we find the file(s)
        actions[file]['path'] = './'

    for file, action in actions.items():
        logging.info("Found a {} file...".format(file))
        logging.info("Running {}".format(action['command']))
        # run the update process
        procUpdate = subprocess.Popen(action['command'], shell=True, cwd=action['path'], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, error = procUpdate.communicate()

        if 0 != procUpdate.returncode:
            return outputError(action['command'], error)
        # now let's see if we have updates
        output = error = None
        logging.info("Seeing if there are any updates to commit.")
        procStatus = subprocess.Popen('git status --porcelain=1', shell=True, cwd=appPath, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, error = procStatus.communicate()

        if not output or action['lock'] not in output:
            logging.info("No updates available, nothing to commit. Exiting...")
            # no updates so nothing to add, not a failure, but we are done
            return True

        # one more, just need to add the file
        output = error = None
        # we don't really care about the path if it's in the current directory
        lockPath = (action['path'], '')[action['path'] == './']
        logging.info("Updates are available, adding {0}{1}...".format(lockPath, action['lock']))
        procAdd = subprocess.Popen(
            'git add {0}{1}'.format(lockPath, action['lock']), shell=True,
            cwd=appPath,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = procAdd.communicate()
        if 0 != procAdd.returncode:
            return outputError('git add', error)
        else:
            output = error = None
            doCommit = True

    if doCommit:
        # @todo should this message be configurable?
        message = "Auto dependency updates via source operation"
        cmd = 'git commit -m "{}"'.format(message)
        procCommit = subprocess.Popen(cmd, shell=True, cwd=appPath, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, error = procCommit.communicate()

        if 0 != procCommit.returncode:
            return outputError('git commit', error)
        else:
            logging.info("Changes successfully committed.")
            return True


if __name__ == '__main__':
    main()

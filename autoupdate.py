#!/usr/bin/env python
from pprint import pprint
import sys
import os
import logging
from logging import critical, error, info, warning, debug
import subprocess

APPVERSION = '0.2.0'
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


def output_error(cmd, output):
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

    appFile = '.platform.app.yaml'
    # @todo should this be a configurable message?
    gitCommitMsg = 'Auto dependency updates via source operation'

    def find_dependency_files(path):
        updateFiles = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            # do we have any updater files in this directory?
            # @todo is there a way to combine this with the platform.app.yaml check?
            toUpdate = list(set(filenames) & set(updaters.keys()))

            if appFile in filenames and 0 < len(toUpdate):
                # dirpath is the full path to the file, and we only want the relative path. if the two are equal, we
                # dont even need it
                if dirpath == path:
                    dirpath = ''
                else:
                    # otherwise we just want the relative bit
                    # full path location: /mnt/source/app
                    # path to composer.json: /mnt/source/app/drupal
                    # We only want to record `drupal`
                    # note, to add a cross-os-compatible ending directory slash, you path.join the path with empty. :shrug:
                    dirpath.replace(os.path.join(dirpath, ''), '')

                updateFiles += list(map(lambda file: os.path.join(dirpath, file), toUpdate))

        return updateFiles

    logging.info("Beginning update process using version {} of updater...".format(APPVERSION))
    # get the path to our app. yes, it's different. in a source op container, we're in a different location
    appPath = os.getenv('PLATFORM_SOURCE_DIR', os.getcwd())

    # grab the list of dependency management files in the app project
    appfiles = find_dependency_files(appPath)

    if 1 > len(appfiles):
        return output_error('Gathering dependency definition file(s)',
                           "I was unable to locate any dependency definition files")

    doCommit = False

    for fileFull in appfiles:
        # split the file into the actual file & relative path
        dependencyFilePath, dependencyFile = os.path.split(fileFull)
        logging.info("Found a {} file...".format(dependencyFile))
        logging.info("Running {}".format(updaters[dependencyFile]['command']))
        # run the update process
        procUpdate = subprocess.Popen(updaters[dependencyFile]['command'], shell=True, cwd=os.path.join(appPath, dependencyFilePath),
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, error = procUpdate.communicate()

        if 0 != procUpdate.returncode:
            return output_error(updaters[dependencyFile]['command'], error)
        # now let's see if we have updates
        output = error = None
        logging.info("Seeing if there are any updates to commit.")
        procStatus = subprocess.Popen('git status --porcelain=1', shell=True, cwd=appPath, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, error = procStatus.communicate()

        if not output or updaters[dependencyFile]['lock'] not in output:
            logging.info("No updates available, nothing to commit. Exiting...")
            # no updates so nothing to add, not a failure, but we are done
            return True

        # one more, just need to add the file
        output = error = None
        # we don't really care about the path if it's in the current directory
        lockPath = (dependencyFilePath, '')[dependencyFilePath == './']
        lockFileLocation = os.path.join(dependencyFilePath, updaters[dependencyFile]['lock'])
        logging.info("Updates are available, adding {}...".format(lockFileLocation))
        procAdd = subprocess.Popen(
            'git add {}'.format(lockFileLocation), shell=True,
            cwd=appPath,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = procAdd.communicate()
        if 0 != procAdd.returncode:
            return output_error('git add', error)
        else:
            output = error = None
            gitCommitMsg += '\nAdded updated {}'.format(lockFileLocation)
            doCommit = True

    if doCommit:
        cmd = 'git commit -m "{}"'.format(gitCommitMsg)
        procCommit = subprocess.Popen(cmd, shell=True, cwd=appPath, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        output, error = procCommit.communicate()

        if 0 != procCommit.returncode:
            return output_error('git commit', error)
        else:
            logging.info("Changes successfully committed.")
            return True


if __name__ == '__main__':
    main()

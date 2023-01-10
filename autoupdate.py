#!/usr/bin/env python
import logging
import os

from psh_logging import outputError
from psh_utility import runCommand, SOURCE_OP_TOOLS_VERSION

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

    def find_dependency_files(projectPath):
        updateFiles = []
        for (dirpath, dirnames, filenames) in os.walk(projectPath):
            # do we have any updater files in this directory?
            # @todo is there a way to combine this with the platform.app.yaml check?
            toUpdate = list(set(filenames) & set(updaters.keys()))

            if appFile in filenames and 0 < len(toUpdate):
                # dirpath is the full path to the file, and we only want the relative path. if the two are equal, we
                # dont even need it
                if dirpath == projectPath:
                    dirpath = ''
                else:
                    # otherwise we just want the relative bit
                    # full path location: /mnt/source/app
                    # path to composer.json: /mnt/source/app/drupal
                    # We only want to record `drupal`
                    # note, to add a cross-os-compatible ending directory slash, you path.join the path with empty. :shrug:
                    dirpath = dirpath.replace(os.path.join(projectPath, ''), '')

                updateFiles += list(map(lambda file: os.path.join(dirpath, file), toUpdate))

        return updateFiles

    logging.info("Beginning update process using version v{} of Source Ops Toolkit...".format(SOURCE_OP_TOOLS_VERSION))
    # get the path to our app. yes, it's different. in a source op container, we're in a different location
    appPath = os.getenv('PLATFORM_SOURCE_DIR', os.getcwd())

    # grab the list of dependency management files in the app project
    appfiles = find_dependency_files(appPath)

    if 1 > len(appfiles):
        return outputError('Gathering dependency definition file(s)',
                           "I was unable to locate any dependency definition files")

    doCommit = False

    for fileFull in appfiles:
        # split the file into the actual file & relative path
        dependencyFilePath, dependencyFile = os.path.split(fileFull)
        # When running `pipenv update` the update is being run inside a virtualenv. The default is to run with user set
        # to `true` which results in the error
        # `Can not perform a '--user' install. User site-packages are not visible in this virtualenv`
        # We'll need to set the config for user to false before running the update
        # @see 
        if 'Pipfile' == dependencyFile:
            rCommand = 'export PIP_USER=0;' + updaters[dependencyFile]['command']
        else:
            rCommand = updaters[dependencyFile]['command']

        logging.info("Found a {} file...".format(dependencyFile))
        logging.info("Running {}".format(rCommand))
        # run the update process
        procUpdate = runCommand(rCommand, os.path.join(appPath, dependencyFilePath))

        if not procUpdate['result']:
            return outputError(rCommand, procUpdate['message'])
        # now let's see if we have updates
        logging.info("Seeing if there are any updates to commit.")
        procStatus = runCommand('git status --porcelain=1', appPath)

        if not procStatus['message'] or updaters[dependencyFile]['lock'] not in procStatus['message']:
            logging.info("No updates available, nothing to commit. Exiting...")
            # no updates so nothing to add, not a failure, but we are done
            return True

        # one more, just need to add the file
        # we don't really care about the path if it's in the current directory
        lockPath = (dependencyFilePath, '')[dependencyFilePath == './']
        lockFileLocation = os.path.join(dependencyFilePath, updaters[dependencyFile]['lock'])
        logging.info("Updates are available, adding {}...".format(lockFileLocation))
        procAdd = runCommand('git add {}'.format(lockFileLocation), appPath)

        if not procAdd['result']:
            return outputError('git add', procAdd['message'])
        else:
            gitCommitMsg += '\nAdded updated {}'.format(lockFileLocation)
            doCommit = True

    if doCommit:
        cmd = 'git commit -m "{}"'.format(gitCommitMsg)
        procCommit = runCommand(cmd, appPath)

        if not procCommit['result']:
            return outputError('git commit', procCommit['message'])
        else:
            logging.info("Changes successfully committed.")
            return True


if __name__ == '__main__':
    main()

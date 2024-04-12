#!/usr/bin/env python
import logging
import os
import subprocess
from psh_logging import outputError

SOURCE_OP_TOOLS_VERSION = '0.3.2'
PSH_COMMON_MESSAGES = {
    'psh_cli': {
        'event': 'Checking for the Platform.sh CLI tool',
        'fail_message': """
            The Platform.sh CLI tool is not installed. Please add its installation to the build section of your
            .platform.app.yaml. See https://github.com/platformsh/cli#install for more information
        """,
        'success_message': 'The Platform.sh CLI tool is installed.'
    },
    'psh_cli_token': {
        'event': 'Checking for the Platform.sh CLI API token',
        'fail_message': """
        You will need to create an environmental variable 'PLATFORMSH_CLI_TOKEN' that contains a valid platform.sh
        API token before I can run platform.sh cli commands
        """,
        'success_message': 'Platform.sh CLI API token is available.'
    },
    'psh_cli_validity': {
        'event': 'Checking for the Platform.sh CLI API token validity',
        'fail_message': """
    It appears that the 'PLATFORMSH_CLI_TOKEN' is not valid, or is incorrect. I will need a valid
    API token before I can run platform.sh cli commands
    """,
        'success_message': 'Platform.sh CLI API token is valid.'
    }
}

validVendors = ['platform', 'upsun']
vendorEnvVarName = 'VENDOR'
defaultVendor = 'platform'


def determineVendor():
    """
    Determines the vendorized cli to use based on the value contained in the environment variable as defined by
    @see vendorEnvVarName
    :return: string
    """
    vendor = os.getenv(vendorEnvVarName, 'platform')
    if vendor not in validVendors:
        vendor = defaultVendor
        message = "The value you've set for {} is not valid. Must be one of: {}".format(vendorEnvVarName,
                                                                                        ', '.join(validVendors))
        outputError('Determining Vendor CLI', message)

    return vendor.lower()


# @todo is there a way
VENDOR = determineVendor()


def runVendorCommand(command, rcwd=None):
    """
    Runs a vendor cli subprocess on the system.
    :param string|list command: Command to be run as a string or as a list
    :param string rcwd: path to where we need the process to be run
    :return:dict {result: boolean, message: strdout|stderr }
    """
    if isinstance(command, list):
        command = list(map(lambda cmd: '{} {}'.format(VENDOR.lower(), cmd), command))
    else:
        command = '{} {}'.format(VENDOR.lower(), command)
    return runCommand(command, rcwd)


def runCommand(command, rcwd=None):
    """
    Runs a subprocess on the system. Mostly used to interact with psh cli and git
    :param string|list command: Command to be run as a string or as a list
    :param string rcwd: path to where we need the process to be run
    :return: dict {result: boolean, message: strdout|stderr }
    """
    procUpdate = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True, cwd=rcwd)
    output, procerror = procUpdate.communicate()

    if 0 == procUpdate.returncode:
        returnStatement = True
        # @todo Should we add a .strip() before we return the message?
        #  there are numerous situations where the message contains trailing \n that cause issues later when attempting
        #  to compare their contents (ie "branchname" == "branchname\n").
        message = output
    else:
        returnStatement = False
        message = procerror

    return {"result": returnStatement, "message": message}


def verifyPshCliInstalled():
    """
    Checks to make sure the psh cli tool is installed
    :return: bool
    @todo since we've moved the messaging, is this one needed anymore?
    """
    procResult = runCommand("which platform")
    return procResult['result']


def verifyPshCliToken():
    pshToken = os.getenv('PLATFORMSH_CLI_TOKEN', None)
    if pshToken is None:
        return False
    else:
        return True


def verifyPshCliTokenValidity():
    command = "platform auth:info > /dev/null 2>&1"
    validityResult = runCommand(command)
    return validityResult['result']

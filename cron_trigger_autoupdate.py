#!/usr/bin/env python
# $ bash <(curl -fsS https://raw.githubusercontent.com/gilzow/source-operations/main/setup.sh) autoprsourceop
# https://console.platform.sh/paul-gilzowatplatform-sh/rdj2cferlaluk/update/log/sqydnupxgbjqe
import os
import sys
import logging
from logging import critical, error, info, warning, debug
import psh_utility
from psh_utility import PSH_COMMON_MESSAGES
from psh_logging import outputError, CBOLD, CRESET, CWARN

DEFAULT_UPDATE_BRANCH = "update"
ENVVAR_UPDATE_BRANCH = "PSH_SOP_UPDATE_BRANCH"


def trigger_autoupdate():
    """
    Handles everything necessary for an auto-update source operation to occur:

    * Gathers the target branch name
    * makes sure the psh cli tool is installed and that we have a PSH CLI Token environmental variable
    * creates the target branch if it doesn't exist
    * If we have to create it, checks to see if there is a git integration and if so, makes sure prune_branches is
         disabled
    * activates the target branch if it exists but is inactive
    * Makes sure the target branch is a child of the production branch
    * syncs the target branch with production
    * Runs the auto-update source operation
    * Returns the target branch back to an inactive status if that's what it was previously
    :return: bool
    """
    defaultSourceOpName = "auto-update"
    defaultSourceOpNameEnvVar = 'PSH_SOP_NAME'

    def inner_trigger_autoupdate():
        """
        Main function. Controls the processing of the auto update run
        :return: bool
        """
        updateBranchPreviousStatus = "inactive"
        logging.info("Beginning set up to perform the source operation update...")

        # Do we have a PSH CLI Token set up?
        logging.info(PSH_COMMON_MESSAGES['psh_cli_token']['event'])
        if not psh_utility.verifyPshCliToken():
            outputError(PSH_COMMON_MESSAGES['psh_cli_token']['event'],
                        PSH_COMMON_MESSAGES['psh_cli_token']['fail_message'])
            return False
        else:
            logging.info('{}{}{}'.format(CBOLD, PSH_COMMON_MESSAGES['psh_cli_token']['success_message'], CRESET))

        # Is the psh cli installed?
        logging.info(PSH_COMMON_MESSAGES['psh_cli']['event'])
        if not psh_utility.verifyPshCliInstalled():
            outputError(PSH_COMMON_MESSAGES['psh_cli']['event'], PSH_COMMON_MESSAGES['psh_cli']['fail_message'])
            return False
        else:
            logging.info('{}{}{}'.format(CBOLD, PSH_COMMON_MESSAGES['psh_cli']['success_message'], CRESET))

        # now we need to get our production branch name. updateBranch and sourceOpName have defaults; only with the
        # productionBranch may we encounter a fatal error
        if not (productionBranchName := getProductionBranchName()):
            return False

        updateBranchName = getUpdateBranchName()
        sourceOpName = getSourceOpName()
        # what do we need to do with the target branch before we can update it
        updateBranchAction = determineBranchAction(updateBranchName)

        if "create" == updateBranchAction:
            logging.info("Your update branch '{}' does not exist so I need to create it".format(updateBranchName))
            integrationID = getGitIntegrationID()
            # first we need to check the integration status and if prune_branches is enabled
            if integrationID != "" and getGitIntPruneBranchProp(integrationID, updateBranchName):
                # we need to warn them
                logging.warning('{}{}{}'.format(CWARN, "'prune_branches' enabled in git integration!", CRESET))
                message = "You have a git integration with this project. If I create the update branch '{}'".format(
                    updateBranchName)
                message += " while 'prune_branches' is enabled, the integration will immediately attempt to delete it."
                message += " Attempting to disable it now. "
                logging.info(message)

                if not disableGitIntPruneBranches(integrationID):
                    # weird, we couldnt update the integration...
                    event = "Trying to update 'prune_branches' to false on git integration {}".format(integrationID)
                    message = "I was unable to disable the 'prune_branches' setting for git integration {}.".format(
                        integrationID)
                    message += " Your {} branch *will* be deleted by the git integration if I continue. You'll ".format(
                        updateBranchName)
                    message += "need to manually create the {} branch first before running this update process.".format(
                        updateBranchName)
                    message += " Exiting."
                    return outputError(event, message)
                else:
                    logging.info('{}{}{}'.format(CBOLD,"'prune_branches' disabled", CRESET))
                    message = " I have disable 'prune_branches' so I can create the branch and continue running "
                    message += "updates. You will need to re-enable 'prune_branches' in your integration after you "
                    message += "manually push the branch '{}' to your remote git repository.".format(updateBranchName)
                    logging.info(message)

                if not createBranch(updateBranchName, productionBranchName):
                    return False
        else:
            if "activate" == updateBranchAction:
                if not activateBranch(updateBranchName):
                    return False
            else:
                updateBranchPreviousStatus = "active"

            # for all existing branch situations, we need to verify the parent and then sync
            if not validateUpdateBranchAncestory(updateBranchName, productionBranchName):
                return False

            # now that we know it's active, let's sync
            # Originally we were checking the `commits_behind` status of the branch and only doing a sync if it was
            # behind, but if a branch is already up-to-date with its parent, then performing a sync command on it will
            # simply return a success exit status. We dont need to do it on a create action because we KNOW it's
            # already sync'ed
            if not syncBranch(updateBranchName, productionBranchName):
                return False

        # Hey, we can finally run the source operation!
        if not runSourceOperations(sourceOpName, updateBranchName):
            return False

        # Now that we're done, let's restore the targeted update branch back to where it was before we touched it
        if "inactive" == updateBranchPreviousStatus:
            logging.info("{} branch was inactive previously so we will deactivate it.".format(updateBranchName))
            deactivateUpdateBranch(updateBranchName)
        else:
            logging.info("{} was previously active so we'll leave it alone.".format(updateBranchName))

        logging.info("{}{}{}".format(CBOLD, "Auto update of {} environment complete.".format(updateBranchName), CRESET))
        return True

    def getGitIntPruneBranchProp(integrationID, updateBranchName):
        """
        Retrieves the status of 'prune_branches' property in the git integration
        :param string integrationID: The git integration ID
        :param string updateBranchName: Target branch name
        :return: bool
        """
        # now we need to get integration details
        command = "platform integration:get {} --property prune_branches".format(integrationID)
        integrationGetRun = psh_utility.runCommand(command)
        # @todo, what should we do here if the retrieval of the integration fails? we're in a situation where things
        # *might* fail, but might not...
        if not integrationGetRun['result']:
            event = "Retrieving details for integration id {}".format(integrationID)
            message = "It appears this project has a git integration, but I was unable to retrieve the details for "
            message += "integration ID {}. Since I can't retrieve the details, I'm not sure if".format(integrationID)
            message += " the 'prune_branches' setting is enabled. If the update branch '{}' is missing, ".format(
                updateBranchName)
            message += "then your git integration probably deleted it"
            outputError(event, message)
            # bail, cuz we can't do anything else
            return False

        if integrationGetRun['message'].strip() == "true":
            return True
        else:
            return False

    def disableGitIntPruneBranches(integrationID):
        """
        Attempts to disable the 'prune_branches' property in the git integration
        :param integrationID: The git integration ID
        :return: bool
        """
        # so we know prune_branches is true, let's try to change it

        command = "platform integration:update {} --prune-branches=false".format(integrationID)
        pruneBranchesRun = psh_utility.runCommand(command)
        return pruneBranchesRun['result']

    def getGitIntegrationID():
        """
        Retrieves the integration ID for any git source integration

        @todo For now we can only have ONE git source integration per project. This may need to be updated in the future
        if that changes

        :return: string The git integration ID
        """
        import csv
        validGitIntegrations = ['github', 'gitlab', 'bitbucket']
        command = "platform integration:list --columns=ID,Type --format=csv --no-header"
        integrationRun = psh_utility.runCommand(command)
        # it's possible there are zero integrations which will return an exit code of 1/false, but we dont care
        if not integrationRun['result']:
            return ""

        # now we need to parse the csv string into a list of "lines"
        listIntegrations = integrationRun['message'].splitlines()
        csvReader = csv.reader(listIntegrations)
        integrationFound = False
        for row in csvReader:
            if row[1] in validGitIntegrations:
                integrationFound = True
                integrationID = row[0]
                break

        if not integrationFound:
            return ""

        return integrationID

    def getProductionBranchName():
        """
        Gets the production branch name
        One would think this should be simple, but one would be wrong
        https://platformsh.slack.com/archives/CEDK8KCSC/p1640717471389700
        @todo I dont like mixing return types. Return an empty string if we dont find one and let the calling function
        handle it? an empty string should register as a false so it would work
        :return: bool|string: Name of the production branch
        """
        command = "platform environment:list --type production --pipe 2>/dev/null"
        event = "Retrieving production environments"
        prodBranchRun = psh_utility.runCommand(command)
        if not prodBranchRun['result'] or "" == prodBranchRun['message'].strip():
            message = "I was unable to retrieve a list of production type branches for this project. Please create a"
            message += " ticket and ask that it be assigned to the DevRel team.\n\n"
            return outputError(event, message)

        # oh, we're not done yet. It's plausible that in the future, we may have more than one production branch
        # so split the return from the above by line break, and then let's see if we were given exactly one
        prodEnvironments = prodBranchRun['message'].splitlines()
        if 1 != len(prodEnvironments):
            message = "More than one production branch was returned. I was given the following branches:\n{}".format(
                prodBranchRun['message'])
            return outputError(event, message)

        return prodEnvironments[0]

    def syncBranch(updateBranch, productionBranch):
        """
        Syncs the code from production down to our update branch before we run the auto-update source operation
        :param string updateBranch: update branch name
        :param string productionBranch: production branch name
        :return: bool
        """
        logging.info("Syncing branch {} with {}...".format(updateBranch, productionBranch))
        command = "platform sync -e {} --yes --wait code 2>/dev/null".format(updateBranch)
        syncRun = psh_utility.runCommand(command)
        if syncRun['result']:
            logging.info("{}{}{}".format(CBOLD, "Syncing complete.", CRESET))
        else:
            return outputError(command, syncRun['message'])

    def deactivateUpdateBranch(targetEnvironment):
        """
        Sets the environment back to inactive status (ie Deletes the *environment* but not the git branch)
        :param string targetEnvironment: name of branch to deactivate
        :return: bool
        """
        logging.info("Deactivating environment {}".format(targetEnvironment))
        command = "platform e:delete {} --no-delete-branch --no-wait --yes 2>/dev/null".format(targetEnvironment)
        deactivateRun = psh_utility.runCommand(command)
        if deactivateRun['result']:
            logging.info("{}{}{}".format(CBOLD, "Environment {} deactivated".format(targetEnvironment), CRESET))
        else:
            return outputError(command, deactivateRun['message'])

    def runSourceOperations(sourceoperation, targetEnvironment):
        """
        Runs the named source operation against a target branch
        :param string sourceoperation: name of the source operation we want to run
        :param string targetEnvironment: name of the branch we want to perform the source operation against
        :return: bool: source operation success
        """
        logging.info(
            "Running source operation '{}' against environment '{}'... ".format(sourceoperation, targetEnvironment))
        command = "platform source-operation:run {} --environment {} --wait 2>/dev/null".format(sourceoperation,
                                                                                                targetEnvironment)
        sourceOpRun = psh_utility.runCommand(command)

        if sourceOpRun['result']:
            logging.info("{}{}{}".format(CBOLD, "Source operation completed.", CRESET))
            return True
        else:
            return outputError(command, sourceOpRun['message'])

    def getUpdateBranchName():
        """
        Gets the update branch name from the environmental variable PSH_SOP_UPDATE_BRANCH, or defaults to 'update'
        :return: string: targeted update branch name
        """
        return os.getenv(ENVVAR_UPDATE_BRANCH, DEFAULT_UPDATE_BRANCH)

    def getSourceOpName():
        """
        Gets the source operation name from the environmental variable PSH_SOP_NAME, or defaults to 'auto-update'
        :return: string: source operation name we want to run
        """
        return os.getenv(defaultSourceOpNameEnvVar, defaultSourceOpName)

    def determineBranchAction(updateBranchName):
        """
        We need the update branch, and we need it to be synced with production
        This could mean we need to create the branch, or sync the branch, or do nothing
        :param string updateBranchName: name of branch we will target for updates
        :return: string: action we need to perform on the target branch
        """
        action = 'sync'
        # kill two birds with one stone here: if it doesn't exist, then we'll get an error & know we need to create it.
        # If it exists, then we'll know if we need to sync it
        command = "platform environment:info status -e {} 2>/dev/null".format(updateBranchName)
        branchStatusRun = psh_utility.runCommand(command)

        if not branchStatusRun['result']:
            action = 'create'
        elif 'inactive' == branchStatusRun['message'].strip():
            action = 'activate'

        return action

    def activateBranch(updateBranchName):
        """
        Activate a branch
        :param updateBranchName: name of branch to activate
        :return: bool
        """
        command = "platform environment:activate {} --wait --yes 2>/dev/null".format(updateBranchName)
        logging.info("Activating branch {}...".format(updateBranchName))
        activateBranchRun = psh_utility.runCommand(command)
        if not activateBranchRun['result']:
            event = "Activating branch {}".format(updateBranchName)
            message = "I encountered an error while attempting to activate the branch {}. Please ".format(
                updateBranchName)
            message += "check the activity log to see why activation failed"
            return outputError(event, message)

        logging.info("{}{}{}".format(CBOLD, "Environment activated.", CRESET))
        return True

    def createBranch(updateBranchName, productionBranchName):
        """
        Creates the update branch so we can run source operations against it
        :param string updateBranchName: name of the branch to be created
        :param string productionBranchName: name of the parent branch (production) to create the branch from
        :return: bool
        """
        event = "Creating environment {}".format(updateBranchName)
        logging.info("{}...".format(event))
        command = "platform e:branch {} {} --no-clone-parent --force 2>/dev/null".format(updateBranchName,
                                                                                         productionBranchName)
        createBranchRun = psh_utility.runCommand(command)
        if not createBranchRun['result']:
            event = "Failure {}".format(event)
            message = "I encountered an error while attempting to create the branch {}.".format(updateBranchName)
            message += " Please check the activity log to see why creation failed"
            outputError(event, message)
        else:
            logging.info("{}{}{}".format(CBOLD, "Environment created.", CRESET))

        return createBranchRun['result']

    def validateUpdateBranchAncestory(updateBranchName, productionBranchName):
        """
        Makes sure the update branch is a direct child of production branch
        :param updateBranchName: Name of the update branch
        :param productionBranchName: Name of the production branch
        :return: bool
        """
        command = "platform environment:info parent -e {} 2>/dev/null".format(updateBranchName)
        branchAncestoryRun = psh_utility.runCommand(command)
        if not branchAncestoryRun['result'] or productionBranchName != branchAncestoryRun['message'].strip():
            event = "Update Branch {} is not a direct descendant of {}".format(updateBranchName, productionBranchName)
            message = "The targeted update branch '{}', is not a direct descendant of the production branch".format(
                updateBranchName)
            message += " '{}'. The update branch's parent is '{}'. ".format(productionBranchName,
                                                                            branchAncestoryRun['message'])
            message += "This automated source operation only supports updating branches that are direct descendants "
            message += "of the production branch"
            return outputError(event, message)

        return True

    def syncBranch(updateBranchName, productionBranchName):
        event = "Sync{} branch {} with {}"
        command = "platform sync -e {} --yes --wait code 2>/dev/null".format(updateBranchName)
        logging.info(event.format('ing', updateBranchName, productionBranchName))
        syncRun = psh_utility.runCommand(command)

        if not syncRun['result']:
            failedEvent = "Failed to {}".format(event.format('', updateBranchName, productionBranchName))
            message = "I was unable to sync the environment {} with {}".format(updateBranchName, productionBranchName)
            message += "You will need to examine the logs to find out why"
            outputError(failedEvent, message)
        else:
            logging.info("{}{}{}".format(CBOLD, "Syncing complete.", CRESET))

        return syncRun['result']

    # fire off our workhorse function
    inner_trigger_autoupdate()

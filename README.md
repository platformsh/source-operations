# Automated Source Operations Toolkit
A collection of scripts to assist with Source Operations actions
## Installation
The setup file will handle installation and running of the update script. 
To run the setup file: 

The setup script it written for bash so if your default shell is dash, you can do either
```shell
bash -c "bash <(curl -fsS https://raw.githubusercontent.com/platformsh/source-operations/main/setup.sh) <command>"
```
or
```shell
curl -fsS https://raw.githubusercontent.com/platformsh/source-operations/main/setup.sh | { bash /dev/fd/3 <command>; } 3<&0
```

Where `<command>` is the action you want to perform.

## Available Commands
`sop-autoupdate` - runs the dependency management updater in a source operation. Will find a dependency management file 
indicator (composer.json, Gemfile, Pipfile, etc) and the corresponding update commands, then commit the updated lock file
 to the repository.

`trigger-sopupdate` - runs all of the set-up necessary to triggering the source operation command above. This can be 
triggered via cron job, worker, slack command, etc. It will check to make sure the target branch where the update should 
be committed exists, is a direct descendent of the production branch, is in an active state and is sync'ed with the 
production branch before proceeding. Also verifies that if a source integration is enabled, that `prune_branches` is 
disabled before proceeding. It requires a `PLATFORMSH_CLI_TOKEN` environmental variable to be set
with a valid token. You can change the target branch by setting an environmental variable named `PSH_SOP_UPDATE_BRANCH`, 
otherwise defaults to a value of `update`. You can change the name of the source operation to run by adding an 
environmental variable `PSH_SOP_NAME`, otherwise defaults to `auto-update`

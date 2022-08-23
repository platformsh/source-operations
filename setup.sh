#!/usr/bin/env bash
# This wont work in dash because dash doesn't support process substitution:
# https://mywiki.wooledge.org/ProcessSubstitution
# bash <(curl -fsS https://raw.githubusercontent.com/platformsh/source-operations/main/setup.sh) trigger-sopupdate
# so we're going to have to do either
# bash -c "bash <(curl -fsS https://raw.githubusercontent.com/platformsh/source-operations/main/setup.sh) trigger-sopupdate"
# where we call bash directly and pass it the commands we need to run OR we can use named pipes to get around the limitation
# dash> curl -fsS https://raw.githubusercontent.com/platformsh/source-operations/main/setup.sh | { bash /dev/fd/3 trigger-sopupdate; } 3<&0
# see https://mywiki.wooledge.org/NamedPipes
# We pipe the output of curl to a compound command, but duplicate the stdout to named pipe 3, which is then available
# inside the compound command as /dev/fd/3 where we can pass it to bash and include our command argument
# alternatively, we could scan PATH for an `.environment` file and then cat our new export of PATH to the bottom

# https://github.com/platformsh/source-operations.git

# Repo for our source ops support scripts
gitSourceOps="https://github.com/platformsh/source-operations.git"
# A writable location where we can store things
tmpDir="/tmp"
dirSourceOps="${tmpDir}/source-operations"

#check and see if we already have the repo cloned in /tmp
# we dont really care what the status is other than does it exist, hence the &>/dev/null
git -C "${dirSourceOps}" status &>/dev/null
gitCheck=$?

# we dont have the repo cloned so let's clone it
if (( 0 != gitCheck )) || [[ ! -d "${dirSourceOps}" ]]; then
  printf "Installing the source operations support tools..."
  git -C "${tmpDir}" clone --quiet "${gitSourceOps}"
  printf " Done.\n"
else
  # we have it so let's make sure we're up-to-date
  printf "Ensuring we have the latest version of the source operations support tools..."
  git -C "${dirSourceOps}" pull origin --quiet
  printf " Done.\n"
fi

# Add our directory to PATH so we can call it
export PATH="${dirSourceOps}:${PATH}"

sourceOp "${1:-'nothing'}"
#return the exit code from sourceOp
exit $?
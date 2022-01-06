#!/usr/bin/env bash
# This wont work in dash because `<(` is a bashism
# bash <(curl -fsS https://raw.githubusercontent.com/gilzow/source-operations/main/setup.sh) autoprsourceop
# so you're going to have to do
# bash -c "bash <(curl -fsS https://raw.githubusercontent.com/gilzow/source-operations/main/setup.sh) trigger-sopupdate"
# dash> curl -fsS https://raw.githubusercontent.com/gilzow/source-operations/main/setup.sh | { bash /dev/fd/3 trigger-sopupdate; } 3<&0
# alternatively, we could scan PATH for an `.environment` file and then cat our new export of PATH to the bottom

# https://github.com/gilzow/source-operations.git

# Repo for our source ops support scripts
gitSourceOps="https://github.com/gilzow/source-operations.git"
# A writable location where we can store things
tmpDir="/tmp"
dirSourceOps="${tmpDir}/source-operations"

#check and see if we already have the repo cloned in /tmp
# we dont really care what the status us other than does it exist, hence the &>/dev/null
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

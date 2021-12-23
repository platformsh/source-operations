#!/usr/bin/env bash

git clone https://github.com/platformsh/source-operations.git
# adds a symlink from our main executable to a valid, writable directory in PATH
IFS=':' read -ra PATHS <<< "${PATH}"
for dir in "${PATHS[@]}"; do
  sourceFile="sourceOp"
  source="${PLATFORM_SOURCE_DIR}/source-operations/${sourceFile}"
  if [ -d "${dir}" ] && [ -w "${dir}" ] && [ ! -e "${dir}/${sourceFile}" ]  && [ ! -L "${dir}/${sourceFile}" ]; then
    ln -s -f "$source" "${dir}/${sourceFile}"
    success=0
    break;
  fi
done

# we SHOULD have at least ONE directory in PATH we can work with, but just in case...
if [[ -z ${success+x} ]] || (( 0 != success )); then
  printf "I was unable to complete installation. Please create a ticket and report this issue.\n"
  exit 1
fi


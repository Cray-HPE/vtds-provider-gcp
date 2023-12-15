#!/bin/bash
#
# MIT License
# 
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# Set up .netrc so we can install from algol60.net
ALGOL60_HOST="artifactory.algol60.net"
> "${HOME}/.netrc"
chmod 600 "${HOME}/.netrc"
cat <<EOF >> "${HOME}/.netrc"
machine ${ALGOL60_HOST}
    login ${ARTIFACTORY_USERNAME}
    password ${ARTIFACTORY_PASSWORD}
EOF


export PATH="${PATH}:${HOME}/.local/bin"
pip3 install --upgrade pip
pip3 install --upgrade --no-use-pep517 nox
pip3 install --upgrade wheel

hash -r   # invalidate hash tables since we may have moved things around
pip3 install --ignore-installed setuptools_scm[toml]
pip3 install --ignore-installed virtualenv
pip3 install --ignore-installed -r requirements-style.txt
pip3 install --ignore-installed -r requirements-lint.txt
# pip3 install --ignore-installed -r requirements-test.txt
pip3 install --ignore-installed build
hash -r   # invalidate hash tables since we may have moved things around

find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

set -e

cat requirements-lint.txt

# Lint the public API code
nox -s lint_public

# Lint the private layer implementation code
nox -s lint_private

# Style check all the code
nox -s style

# Run unit tests
#
# Temporarily Disabled until there are unit tests to run
# nox -s tests

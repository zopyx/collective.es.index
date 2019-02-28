#!/bin/sh
rm -r ./lib ./include ./local ./bin
python3 -m venv .
./bin/pip install -U pip 
./bin/pip install -r https://raw.githubusercontent.com/plone/buildout.coredev/5.2/requirements.txt 
./bin/buildout -N

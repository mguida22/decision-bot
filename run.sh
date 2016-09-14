#!/usr/bin/env bash

export FLASK_APP=app.py

if [ "$1" == "debug" ]
then
  export FLASK_DEBUG=1
fi

flask run

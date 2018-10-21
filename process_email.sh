#!/bin/sh -
/usr/bin/env \
  API_KEY='' \
  API_ENDPOINT='' \
  python3 ./process_email.py "$@"

#!/bin/bash
source .venv/bin/activate
nohup python lib/main.py --nogui > /dev/null 2>&1 &

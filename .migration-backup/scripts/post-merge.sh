#!/bin/bash
set -e

# Install / upgrade Python dependencies after any merge
pip install -r requirements.txt --quiet

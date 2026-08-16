#!/bin/bash
set -e

# Install / upgrade pnpm workspace dependencies
pnpm install --frozen-lockfile

# Install / upgrade Python dependencies
pip install -r requirements.txt --quiet

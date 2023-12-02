#!/bin/bash
# This script destroys the conda environment named "xspec" and reinstalls it.
# It then installs xspec package.
# It also installs the documentation.

# Clean out old installation
source clean_xspec.sh

# Destroy conda environement named xspec and reinstall it
source install_conda_environment.sh

# Install xspec
source install_xspec.sh

# Build documentation
source install_docs.sh
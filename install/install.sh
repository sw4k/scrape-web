#!/bin/sh
# SPDX-License-Identifier: MIT
#
# Installs scrape-web cli tool into /usr/local/bin (rwfs)
#
# Usage:
#
# install.sh
#
mkdir -p /usr/local/bin
cp ./scrape-web /usr/local/bin/scrape-web
chmod 755 /usr/local/bin/scrape-web
pip install beautifulsoup4 --break-system-packages
pip install lxml --break-system-packages

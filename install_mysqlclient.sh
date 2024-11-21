#!/bin/bash

# Update package list
sudo apt-get update

# Install MySQL client development libraries and build tools
sudo apt-get install -y default-libmysqlclient-dev build-essential pkg-config

# Set environment variables for mysqlclient installation
export MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
export MYSQLCLIENT_LDFLAGS="-L/usr/lib/mysql"

# Install mysqlclient Python package
pip install mysqlclient --break-system-packages

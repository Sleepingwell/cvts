#!/usr/bin/bash

# Copied from various places noted below. There is redundancy, but I have left
# it largely so it is easy to update if things change.

#-------------------------------------------------------------------------------
# copied from: https://github.com/CVTS/valhalla#building-from-source---linux
#-------------------------------------------------------------------------------
sudo add-apt-repository -y ppa:valhalla-core/valhalla
sudo apt-get update
sudo apt-get install -y cmake make libtool pkg-config g++ gcc curl unzip jq lcov protobuf-compiler vim-common locales libboost-all-dev libcurl4-openssl-dev zlib1g-dev liblz4-dev libprime-server-dev libprotobuf-dev prime-server-bin
#if you plan to compile with data building support, see below for more info
sudo apt-get install -y libgeos-dev libgeos++-dev libluajit-5.1-dev libspatialite-dev libsqlite3-dev wget sqlite3 spatialite-bin
source /etc/lsb-release
if [[ $(python -c "print(int($DISTRIB_RELEASE > 15))") > 0 ]]; then sudo apt-get install -y libsqlite3-mod-spatialite; fi
#if you plan to compile with python bindings, see below for more info
sudo apt-get install -y python-all-dev


#-------------------------------------------------------------------------------
# copied from https://github.com/CVTS/prime_server#quick-start
#-------------------------------------------------------------------------------
# trusty didn't have czmq or newer zmq in the repositories so its repackaged here
if [[ $(grep -cF trusty /etc/lsb-release) > 0 ]]; then
    sudo add-apt-repository -y ppa:kevinkreiser/libsodium
    sudo add-apt-repository -y ppa:kevinkreiser/libpgm
    sudo add-apt-repository -y ppa:kevinkreiser/zeromq3
    sudo add-apt-repository -y ppa:kevinkreiser/czmq
    sudo apt-get update
fi
# grab some standard autotools stuff
sudo apt-get install autoconf automake libtool make gcc g++ lcov
# grab curl (for url de/encode) and zmq for the awesomeness
sudo apt-get install libcurl4-openssl-dev libzmq3-dev libczmq-dev

cd
git clone --recurse-submodules git@github.com:CVTS/prime_server.git
cd ~/prime_server
./autogen.sh
./configure
make -j8
sudo make install


#-------------------------------------------------------------------------------
# copied from: https://github.com/CVTS/valhalla#building-from-source---linux
#-------------------------------------------------------------------------------
cd
git clone --recurse-submodules https://github.com/CVTS/valhalla.git
cd valhalla
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc) # for macos, use: make -j$(sysctl -n hw.physicalcpu)
sudo make install

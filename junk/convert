#!/usr/bin/env python3

"""Ensure the test data is anonymous."""

import os
import sys
import csv
import json

def convert(infile, outfile):
    with open(infile, 'r') as cf, open(outfile, 'w') as of:
        reader = csv.DictReader(cf)
        line = 1
        for i, l in enumerate(reader):
            l['PlateNumber'] = 1
            l['VehicleType'] = 1
            l['Weight'] = 1

            if i==0:
                of.write(','.join(l.keys()))
                of.write('\n')

            of.write(','.join(str(v) for v in l.values()))
            of.write('\n')

if __name__ == '__main__':
    inputfile = 'test.csv'
    outputfile = 'out.csv'
    convert(inputfile, outputfile)

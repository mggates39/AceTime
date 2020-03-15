# Copyright 2019 Brian T. Park
#
# MIT License
"""
Generate the validation_data.py file that contains test validation data.
"""

import logging
import os
import pytz
from typing import List
from transformer import div_to_zero
from transformer import normalize_name
from tdgenerator import TestItem
from tdgenerator import TestData


class PythonValidationGenerator:
    """Generate Python validation_data.py file.
    """

    VALIDATION_DATA_FILE = """\
# This file was generated by the following script:
#
#  $ {invocation}
#
# TZ Database comes from:
#   * https://github.com/eggert/tz/releases/tag/{tz_version}
#
# Python database comes from:
#   * pytz library (version {pytz_version})

# DO NOT EDIT

from tdgenerator import TestItem

#---------------------------------------------------------------------------
# numZones: {numZones}
#
# The 'total' and 'dst' offset columns are in minutes, not seconds. The
# transition 'epoch' was determined by ZoneSpecifier using the TZ Data (version
# {tz_version}). The expected 'total' and 'dst' offsets come from
# TestDataGenerator which uses the data from pytz (version {pytz_version}) that
# was installed when the generating script was run.

{validationItems}
#---------------------------------------------------------------------------
# numZones: {numZones}

VALIDATION_DATA = {{
{validationMapItems}
}}
"""
    VALIDATION_ITEM = """\
VALIDATION_ITEM_{zoneNormalizedName} = [
    #            epoch total   dst     y   M   d   h   m   s type
{testItems}
]

"""

    TEST_ITEM = """\
    TestItem({epochSeconds:9}, {total:4}, {dst:4}, {y:4}, {M:2}, {d:2}, {h:2}, {m:2}, {s:2}, '{type}'),
"""

    VALIDATION_MAP_ITEM = """\
    '{zoneFullName}': VALIDATION_ITEM_{zoneNormalizedName},
"""

    VALIDATION_FILE_NAME = 'validation_data.py'

    def __init__(self,
        invocation: str,
        tz_version: str,
        test_data: TestData,
        num_items: int):
        self.invocation = invocation
        self.tz_version = tz_version
        self.test_data = test_data
        self.num_items = num_items

    def generate_files(self, output_dir: str):
        self._write_file(output_dir, self.VALIDATION_FILE_NAME,
                         self._generate_validation_data())

    def _write_file(self, output_dir: str, filename: str, content: str):
        full_filename = os.path.join(output_dir, filename)
        with open(full_filename, 'w', encoding='utf-8') as output_file:
            print(content, end='', file=output_file)
        logging.info("Created %s", full_filename)

    def _generate_validation_data(self) -> str:
        validation_items_str = self._get_validation_items(self.test_data)
        validation_map_items_str = self._get_validation_map_items(
            self.test_data)
        return self.VALIDATION_DATA_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            pytz_version=pytz.__version__, # type: ignore
            numZones=len(self.test_data),
            validationItems=validation_items_str,
            validationMapItems=validation_map_items_str)

    def _get_validation_items(self, test_data: TestData) -> str:
        s = ''
        for zone_name, test_items in sorted(test_data.items()):
            test_items_str = self._get_test_items(test_items)
            s += self.VALIDATION_ITEM.format(
                zoneNormalizedName=normalize_name(zone_name),
                testItems=test_items_str)
        return s

    def _get_test_items(self, test_items: List[TestItem]) -> str:
        s = ''
        for test_item in test_items:
            s += self._get_test_item(test_item)
        return s

    def _get_test_item(self, test_item: TestItem) -> str:
        return self.TEST_ITEM.format(
            epochSeconds=test_item.epoch,
            total=div_to_zero(test_item.total_offset, 60),
            dst=div_to_zero(test_item.dst_offset, 60),
            y=test_item.y,
            M=test_item.M,
            d=test_item.d,
            h=test_item.h,
            m=test_item.m,
            s=test_item.s,
            type=test_item.type)

    def _get_validation_map_items(self, test_data: TestData) -> str:
        s = ''
        for zone_name, test_items in sorted(test_data.items()):
            s += self.VALIDATION_MAP_ITEM.format(
                zoneFullName=zone_name,
                zoneNormalizedName=normalize_name(zone_name))
        return s

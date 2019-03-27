#!/usr/bin/env python3
#
# Copyright 2018 Brian T. Park
#
# MIT License
"""
Validate the inlined zonedb maps (zone_infos and zone_policies) generated by
InlineGenerator. These should be identical to the ZONE_INFO_MAP and
ZONE_POLICY_MAP created by PythonGenerator in the zone_infos.py and
zone_policies.py files.
"""

import logging
import collections
import pytz
from datetime import datetime
from tdgenerator import TestDataGenerator
from zone_specifier import ZoneSpecifier
from zone_specifier import to_utc_string
from zone_specifier import SECONDS_SINCE_UNIX_EPOCH


class Validator:
    """Validate the zone_infos and zone_policies data from the TZ Database,
    as extracted and transformed by Extractor and Transformer.

    Usage:
        # For validation against pytz golden test data
        validator = Validator(zone_infos, zone_policies, ...)
        validator.validate_transition_buffer_size()
        validator.validate_test_data()
    """

    def __init__(self, zone_infos, zone_policies, granularity, viewing_months,
                 validate_dst_offset, debug_validator, debug_specifier,
                 zone_name, year, in_place_transitions, optimize_candidates):
        """
        Args:
            zone_infos: (dict) of {name -> zone_info{} }
            zone_policies: (dict) of {name ->zone_policy{} }
            granularity (int): time resolution (in seconds) of
                zone_infos and zone_policies
            viewing_months: (int) number of months in the calculation window
                (13, 14, 36)
            validate_dst_offset: (bool) validate DST offset against Python in
                addition to total UTC offset
            debug_validator: (bool) enable debugging output for Validator
            debug_specifier: (bool) enable debugging output for ZoneSpecifier
            zone_name: (str) validate only this zone
            year: (int | None) validate only this year
            in_place_transitions: (bool)
            optimize_candidates: (bool)
        """
        self.zone_infos = zone_infos
        self.zone_policies = zone_policies
        self.granularity = granularity
        self.viewing_months = viewing_months
        self.validate_dst_offset = validate_dst_offset
        self.debug_validator = debug_validator
        self.debug_specifier = debug_specifier
        self.zone_name = zone_name
        self.year = year
        self.in_place_transitions = in_place_transitions
        self.optimize_candidates = optimize_candidates

    # The following are public methods.

    def validate_buffer_size(self):
        """Determine the size of transition buffer required for each zone.
        """
        # map of {zoneName -> (numTransitions, year)}
        transition_stats = {}

        # Calculate the number of Transitions necessary for every Zone
        # in zone_infos, for the years 2000 to 2038.
        logging.info('Calculating transitions between 2000 and 2038')
        for zone_short_name, zone_info in sorted(self.zone_infos.items()):
            if self.zone_name and zone_short_name != self.zone_name:
                continue
            if self.debug_validator:
                logging.info('Validating zone %s' % zone_short_name)

            zone_specifier = ZoneSpecifier(
                zone_info_data=zone_info,
                viewing_months=self.viewing_months,
                debug=self.debug_specifier,
                in_place_transitions=self.in_place_transitions,
                optimize_candidates=self.optimize_candidates)
            # pair of tuple(count, year), transition count, and candidate count
            count_record = ((0, 0), (0, 0))
            for year in range(2000, 2038):
                if self.year and self.year != year:
                    continue
                #logging.info('Validating year %s' % year)
                zone_specifier.init_for_year(year)

                transition_count = len(zone_specifier.transitions)
                if transition_count > count_record[0][0]:
                    count_record = ((transition_count, year), count_record[1])

                total_count = zone_specifier.max_num_transitions
                if total_count > count_record[1][0]:
                    count_record = (count_record[0], (total_count, year))
            transition_stats[zone_short_name] = count_record

        logging.info('Count(transitions) group by zone order by count desc')
        for zone_short_name, count_record in sorted(
                transition_stats.items(), key=lambda x: x[1], reverse=True):
            logging.info(
                '%s: %d (%04d); %d (%04d)' %
                ((zone_short_name, ) + count_record[0] + count_record[1]))

    def validate_test_data(self):
        """Compare Python and AceTime offsets by generating TestDataGenerator.
        """
        logging.info('Creating test data')
        data_generator = TestDataGenerator(self.zone_infos, self.zone_policies,
            self.granularity)
        (test_data, num_items) = data_generator.create_test_data()
        logging.info('test_data=%d', len(test_data))

        logging.info('Validating %s test items', num_items)
        self._validate_test_data(test_data)

    # The following are internal methods.

    def _validate_test_data(self, test_data):
        for zone_short_name, items in test_data.items():
            if self.zone_name and zone_short_name != self.zone_name:
                continue
            if self.debug_validator:
                logging.info('  Validating zone %s' % zone_short_name)
            self._validate_test_data_for_zone(zone_short_name, items)

    def _validate_test_data_for_zone(self, zone_short_name, items):
        zone_info = self.zone_infos[zone_short_name]
        zone_specifier = ZoneSpecifier(
            zone_info_data=zone_info,
            viewing_months=self.viewing_months,
            debug=self.debug_specifier,
            in_place_transitions=self.in_place_transitions,
            optimize_candidates=self.optimize_candidates)
        for item in items:
            if self.year and self.year != item.y:
                continue

            # Print out diagnostics if mismatch detected or if debug flag given
            unix_seconds = item.epoch + SECONDS_SINCE_UNIX_EPOCH
            ldt = datetime.utcfromtimestamp(unix_seconds)
            header = (
                "======== Testing %s; at %sw; utc %s; epoch %s; unix %s" %
                (zone_short_name, _test_item_to_string(item), ldt, item.epoch,
                 unix_seconds))

            if self.debug_specifier:
                logging.info(header)

            try:
                info = zone_specifier.get_timezone_info_for_seconds(item.epoch)
            except Exception:
                logging.exception('Exception with test data %s', item)
                raise
            is_matched = info.total_offset == item.total_offset
            status = '**Matched**' if is_matched else '**Mismatched**'
            body = ('%s: AceTime(%s); Expected(%s)' %
                    (status, to_utc_string(info.utc_offset, info.dst_offset),
                     to_utc_string(item.total_offset - item.dst_offset,
                                   item.dst_offset)))
            if is_matched:
                if self.debug_specifier:
                    logging.info(body)
                    zone_specifier.print_matches_and_transitions()
            else:
                if not self.debug_specifier:
                    logging.error(header)
                logging.error(body)
                zone_specifier.print_matches_and_transitions()


def _test_item_to_string(i):
    return '%04d-%02d-%02dT%02d:%02d:%02d' % (i.y, i.M, i.d, i.h, i.m, i.s)


# List of zones where the Python DST offset is incorrect.
TIME_ZONES_BLACKLIST = {
    'America/Argentina/Buenos_Aires',  # Python is wrong
    'America/Argentina/Cordoba',  # Python is wrong
    'America/Argentina/Jujuy',  # Python is wrong
    'America/Argentina/Salta',  # Python is wrong
    'America/Bahia_Banderas',  # Python is wrong
    'America/Indiana/Winamac',  # Python is wrong
}

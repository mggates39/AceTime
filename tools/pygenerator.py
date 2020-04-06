# Copyright 2018 Brian T. Park
#
# MIT License
"""
Generate the 'zone_infos.py' and 'zone_policies.py' files for Python.
"""

import logging
import os

from extractor import ZoneEraRaw
from extractor import ZoneRuleRaw
from extractor import ZonesMap
from extractor import RulesMap
from transformer import normalize_name
from transformer import normalize_raw
from transformer import CommentsMap
from jsongenerator import ZoneDb
from typing import List
from typing import Tuple


class PythonGenerator:
    """Generate Python files for zone_infos.py and zone_policies.py which are
    used by the ZoneSpecifier class. Unlike the Arduino version, the Python
    implementation does not support the 'Link' zone names.
    """

    ZONE_POLICIES_FILE = """\
# This file was generated by the following script:
#
#  $ {invocation}
#
# using the TZ Database files
#
#  {tz_files}
#
# from https://github.com/eggert/tz/releases/tag/{tz_version}
#
# DO NOT EDIT

# numPolicies: {numPolicies}
# numRules: {numRules}

{policyItems}

#---------------------------------------------------------------------------

ZONE_POLICY_MAP = {{
{policyMapItems}
}}

#---------------------------------------------------------------------------

# The following zone policies are not supported in the current version of
# AceTime.
#
# numPolicies: {numRemovedPolicies}
#
{removedPolicyItems}

#---------------------------------------------------------------------------

# The following zone policies may have inaccuracies due to the following
# reasons:
#
# numPolicies: {numNotablePolicies}
#
{notablePolicyItems}

"""

    ZONE_POLICY_ITEM = """\
#---------------------------------------------------------------------------
# Policy name: {policyName}
# Rule count: {numRules}
#---------------------------------------------------------------------------
ZONE_RULES_{policyName} = [
{ruleItems}
]
ZONE_POLICY_{policyName} = {{
    'name': '{policyName}',
    'rules': ZONE_RULES_{policyName}
}}

"""

    ZONE_POLICY_MAP_ITEM = """\
    '{policyName}': ZONE_POLICY_{policyName},
"""

    ZONE_REMOVED_POLICY_ITEM = """\
# {policyName} ({policyReason})
"""

    ZONE_NOTABLE_POLICY_ITEM = """\
# {policyName} ({policyReason})
"""

    ZONE_RULE_ITEM = """\
    # {rawLine}
    {{
        'fromYear': {fromYear},
        'toYear': {toYear},
        'inMonth': {inMonth},
        'onDayOfWeek': {onDayOfWeek},
        'onDayOfMonth': {onDayOfMonth},
        'atSeconds': {atSeconds},
        'atTimeSuffix': '{atTimeSuffix}',
        'deltaSeconds': {deltaSeconds},
        'letter': '{letter}',
    }},
"""

    ZONE_INFOS_FILE = """\
# This file was generated by the following script:
#
#  $ {invocation}
#
# using the TZ Database files
#
#  {tz_files}
#
# from https://github.com/eggert/tz/releases/tag/{tz_version}
#
# DO NOT EDIT

from zonedb.zone_policies import *

# numInfos: {numInfos}
# numEras: {numEras}

{infoItems}

#---------------------------------------------------------------------------

ZONE_INFO_MAP = {{
{infoMapItems}
}}

#---------------------------------------------------------------------------

# The following zones are not supported in the current version of AceTime.
#
# numInfos: {numRemovedInfos}
#
{removedInfoItems}

#---------------------------------------------------------------------------

# The following zones may have inaccuracies due to the following reasons:
#
# numInfos: {numNotableInfos}
#
{notableInfoItems}
"""

    ZONE_INFO_ITEM = """\
#---------------------------------------------------------------------------
# Zone name: {zoneFullName}
# Era count: {numEras}
#---------------------------------------------------------------------------

ZONE_ERAS_{zoneNormalizedName} = [
{eraItems}
]
ZONE_INFO_{zoneNormalizedName} = {{
    'name': '{zoneFullName}',
    'eras': ZONE_ERAS_{zoneNormalizedName}
}}

"""

    ZONE_REMOVED_INFO_ITEM = """\
# {zoneFullName} ({infoReason})
"""

    ZONE_NOTABLE_INFO_ITEM = """\
# {zoneFullName} ({infoReason})
"""

    ZONE_ERA_ITEM = """\
    # {rawLine}
    {{
      'offsetSeconds': {offsetSeconds},
      'zonePolicy': {zonePolicy},
      'rulesDeltaSeconds': {rulesDeltaSeconds},
      'format': '{format}',
      'untilYear': {untilYear},
      'untilMonth': {untilMonth},
      'untilDay': {untilDay},
      'untilSeconds': {untilSeconds},
      'untilTimeSuffix': '{untilTimeSuffix}',
    }},
"""

    ZONE_INFO_MAP_ITEM = """\
    '{zoneFullName}': ZONE_INFO_{zoneNormalizedName}, # {zoneFullName}
"""

    ZONE_INFOS_FILE_NAME = 'zone_infos.py'
    ZONE_POLICIES_FILE_NAME = 'zone_policies.py'

    def __init__(
        self,
        invocation: str,
        tzdb: ZoneDb,
    ):
        self.invocation = invocation
        self.tz_version = tzdb['tz_version']
        self.tz_files = tzdb['tz_files']
        self.zones_map = tzdb['zones_map']
        self.rules_map = tzdb['rules_map']
        self.removed_zones = tzdb['removed_zones']
        self.removed_policies = tzdb['removed_policies']
        self.notable_zones = tzdb['notable_zones']
        self.notable_policies = tzdb['notable_policies']

    def generate_files(self, output_dir: str) -> None:
        self._write_file(output_dir, self.ZONE_POLICIES_FILE_NAME,
                         self._generate_policies())

        self._write_file(output_dir, self.ZONE_INFOS_FILE_NAME,
                         self._generate_infos())

    def _write_file(self, output_dir: str, filename: str, content: str) -> None:
        full_filename = os.path.join(output_dir, filename)
        with open(full_filename, 'w', encoding='utf-8') as output_file:
            print(content, end='', file=output_file)
        logging.info("Created %s", full_filename)

    def _generate_policies(self) -> str:
        (num_rules, policy_items) = self._generate_policy_items(self.rules_map)
        policy_map_items = self._generate_policy_map_items(self.rules_map)
        removed_policy_items = self._generate_removed_policy_items(
            self.removed_policies)
        notable_policy_items = self._generate_notable_policy_items(
            self.notable_policies)

        return self.ZONE_POLICIES_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            tz_files=', '.join(self.tz_files),
            numPolicies=len(self.rules_map),
            numRules=num_rules,
            policyItems=policy_items,
            policyMapItems=policy_map_items,
            numRemovedPolicies=len(self.removed_policies),
            removedPolicyItems=removed_policy_items,
            numNotablePolicies=len(self.notable_policies),
            notablePolicyItems=notable_policy_items)

    def _generate_policy_items(self, rules_map: RulesMap) -> Tuple[int, str]:
        num_rules = 0
        policy_items = ''
        for name, rules in sorted(rules_map.items()):
            policy_items += self._generate_policy_item(name, rules)
            num_rules += len(rules)
        return (num_rules, policy_items)

    def _generate_policy_map_items(self, rules_map: RulesMap) -> str:
        policy_map_items = ''
        for name, rules in sorted(
                rules_map.items(), key=lambda x: normalize_name(x[0])):
            policy_map_items += self.ZONE_POLICY_MAP_ITEM.format(
                policyName=normalize_name(name))
        return policy_map_items

    def _generate_policy_item(self, name: str, rules: List[ZoneRuleRaw]) -> str:
        rule_items = ''
        for rule in rules:
            rule_items += self.ZONE_RULE_ITEM.format(
                policyName=normalize_name(name),
                rawLine=normalize_raw(rule['rawLine']),
                fromYear=rule['fromYear'],
                toYear=rule['toYear'],
                inMonth=rule['inMonth'],
                onDayOfWeek=rule['onDayOfWeek'],
                onDayOfMonth=rule['onDayOfMonth'],
                atSeconds=rule['atSecondsTruncated'],
                atTimeSuffix=rule['atTimeSuffix'],
                deltaSeconds=rule['deltaSecondsTruncated'],
                letter=rule['letter'])
        return self.ZONE_POLICY_ITEM.format(
            policyName=normalize_name(name),
            numRules=len(rules),
            ruleItems=rule_items)

    def _generate_removed_policy_items(
        self, removed_policies: CommentsMap,
    ) -> str:
        removed_policy_items = ''
        for name, reason in sorted(removed_policies.items()):
            removed_policy_items += (
                self.ZONE_REMOVED_POLICY_ITEM.format(
                    policyName=normalize_name(name),
                    policyReason=reason)
            )
        return removed_policy_items

    def _generate_notable_policy_items(
        self, notable_policies: CommentsMap,
    ) -> str:
        notable_policy_items = ''
        for name, reason in sorted(notable_policies.items()):
            notable_policy_items += (
                self.ZONE_NOTABLE_POLICY_ITEM.format(
                    policyName=normalize_name(name),
                    policyReason=reason)
            )
        return notable_policy_items

    def _generate_infos(self) -> str:
        (num_eras, info_items) = self._generate_info_items(self.zones_map)
        info_map_items = self._generate_info_map_items(self.zones_map)
        removed_info_items = self._generate_removed_info_items(
            self.removed_zones)
        notable_info_items = self._generate_notable_info_items(
            self.notable_zones)

        return self.ZONE_INFOS_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            tz_files=', '.join(self.tz_files),
            numInfos=len(self.zones_map),
            numEras=num_eras,
            infoItems=info_items,
            infoMapItems=info_map_items,
            numRemovedInfos=len(self.removed_zones),
            removedInfoItems=removed_info_items,
            numNotableInfos=len(self.notable_zones),
            notableInfoItems=notable_info_items)

    def _generate_info_items(self, zones_map: ZonesMap) -> Tuple[int, str]:
        info_items = ''
        num_eras = 0
        for name, eras in sorted(self.zones_map.items()):
            info_items += self._generate_info_item(name, eras)
            num_eras += len(eras)
        return (num_eras, info_items)

    def _generate_info_map_items(self, zones_map: ZonesMap) -> str:
        """Generate a map of (zone_name -> zoneInfo), shorted by name.
        """
        info_map_items = ''
        for zone_name, zones in sorted(
                zones_map.items(),
                key=lambda x: normalize_name(x[0])):
            info_map_items += self.ZONE_INFO_MAP_ITEM.format(
                zoneNormalizedName=normalize_name(zone_name),
                zoneFullName=zone_name)
        return info_map_items

    def _generate_removed_info_items(self, removed_zones: CommentsMap) -> str:
        removed_info_items = ''
        for zone_name, reason in sorted(removed_zones.items()):
            removed_info_items += self.ZONE_REMOVED_INFO_ITEM.format(
                zoneFullName=zone_name, infoReason=reason)
        return removed_info_items

    def _generate_notable_info_items(self, notable_zones: CommentsMap) -> str:
        notable_info_items = ''
        for zone_name, reason in sorted(notable_zones.items()):
            notable_info_items += self.ZONE_NOTABLE_INFO_ITEM.format(
                zoneFullName=zone_name, infoReason=reason)
        return notable_info_items

    def _generate_info_item(
        self, zone_name: str, eras: List[ZoneEraRaw],
    ) -> str:
        era_items = ''
        for era in eras:
            era_items += self._generate_era_item(era)

        return self.ZONE_INFO_ITEM.format(
            zoneFullName=zone_name,
            zoneNormalizedName=normalize_name(zone_name),
            numEras=len(eras),
            eraItems=era_items)

    def _generate_era_item(self, era: ZoneEraRaw) -> str:
        policy_name = era['rules']
        if policy_name in ['-', ':']:
            zone_policy = "'%s'" % policy_name
        else:
            zone_policy = 'ZONE_POLICY_%s' % normalize_name(policy_name)

        return self.ZONE_ERA_ITEM.format(
            rawLine=normalize_raw(era['rawLine']),
            offsetSeconds=era['offsetSecondsTruncated'],
            zonePolicy=zone_policy,
            rulesDeltaSeconds=era['rulesDeltaSecondsTruncated'],
            format=era['format'],  # preserve the %s
            untilYear=era['untilYear'],
            untilMonth=era['untilMonth'],
            untilDay=era['untilDay'],
            untilSeconds=era['untilSecondsTruncated'],
            untilTimeSuffix=era['untilTimeSuffix'])

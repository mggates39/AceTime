# Copyright 2018 Brian T. Park
#
# MIT License
"""
Generate the zone_info and zone_policies files.
"""

import logging
import os

from transformer import short_name

class Generator:
    ZONE_POLICIES_H_FILE = """\
// This file was generated by the following script:
//
//   $ {invocation}
//
// using the TZ Database files from
// https://github.com/eggert/tz/releases/tag/{tz_version}
//
// DO NOT EDIT

#ifndef ACE_TIME_ZONE_POLICIES_H
#define ACE_TIME_ZONE_POLICIES_H

#include "../common/ZonePolicy.h"

namespace ace_time {{
namespace zonedb {{

{policyItems}

}}
}}

#endif
"""

    ZONE_POLICIES_H_POLICY_ITEM = """\
external const common::ZonePolicy kPolicy{policyName};
"""

    ZONE_POLICIES_CPP_FILE = """\
// This file was generated by the following script:
//
//   $ {invocation}
//
// using the TZ Database files from
// https://github.com/eggert/tz/releases/tag/{tz_version}
//
// DO NOT EDIT

#include "zone_policies.h"

namespace ace_time {{
namespace zonedb {{

{policyItems}

}}
}}
"""

    ZONE_POLICIES_CPP_POLICY_ITEM = """\
//---------------------------------------------------------------------------
// {policyName} Rules
//---------------------------------------------------------------------------

static const common::ZoneRule kZoneRules{policyName}[] = {{
{ruleItems}
}};

const common::ZonePolicy kPolicy{policyName} = {{
  sizeof(kZoneRules{policyName})/sizeof(common::ZoneRule) /*numRules*/,
  kZoneRules{policyName} /*rules*/,
}};

"""

    ZONE_POLICIES_CPP_RULE_ITEM = """\
  // {rawLine}
  {{
    {fromYearFull} /*fromYearFull*/,
    {toYearFull} /*toYearFull*/,
    {inMonth} /*inMonth*/,
    {onDayOfWeek} /*onDayOfWeek*/,
    {onDayOfMonth} /*onDayOfMonth*/,
    {atHour} /*atHour*/,
    '{atHourModifier}' /*atHourModifier*/,
    {deltaCode} /*deltaCode*/,
    '{letter}' /*letter*/,
  }},
"""

    ZONE_INFOS_H_FILE = """\
// This file was generated by the following script:
//
//   $ {invocation}
//
// using the TZ Database files from
// https://github.com/eggert/tz/releases/tag/{tz_version}
//
// DO NOT EDIT

#ifndef ACE_TIME_ZONE_INFOS_H
#define ACE_TIME_ZONE_INFOS_H

#include "../common/ZoneInfo.h"

namespace ace_time {{
namespace zonedb {{

{infoItems}

}}
}}

#endif
"""

    ZONE_INFOS_H_INFO_ITEM = """\
external const common::ZoneInfo const k{infoShortName};
"""

    ZONE_INFOS_CPP_FILE = """\
// This file was generated by the following script:
//
//   $ {invocation}
//
// using the TZ Database files from
// https://github.com/eggert/tz/releases/tag/{tz_version}
//
// DO NOT EDIT

#include "../common/ZoneInfo.h"
#include "zone_policies.h"
#include "zone_infos.h"

namespace ace_time {{
namespace zonedb {{

{infoItems}

}}
}}
"""

    ZONE_INFOS_CPP_INFO_ITEM = """\
//---------------------------------------------------------------------------
// {infoFullName}
//---------------------------------------------------------------------------

static common::ZoneEntry const kZoneEntry{infoShortName}[] = {{
{entryItems}
}};

common::ZoneInfo const k{infoShortName} = {{
  "{infoFullName}" /*name*/,
  kZoneEntry{infoShortName} /*entries*/,
  sizeof(kZoneEntry{infoShortName})/sizeof(common::ZoneEntry) /*numEntries*/,
}};

"""

    ZONE_INFOS_CPP_ENTRY_ITEM = """\
  // {rawLine}
  {{
    {offsetCode} /*offsetCode*/,
    {zonePolicy} /*zonePolicy*/,
    "{format}" /*format*/,
    {untilYear} /*untilYear*/,
  }},
"""

    ZONE_INFOS_H_FILE_NAME = 'zone_infos.h'
    ZONE_INFOS_CPP_FILE_NAME = 'zone_infos.cpp'
    ZONE_POLICIES_H_FILE_NAME = 'zone_policies.h'
    ZONE_POLICIES_CPP_FILE_NAME = 'zone_policies.cpp'

    def __init__(self, invocation, tz_version, zones, rules):
        self.invocation = invocation
        self.tz_version = tz_version
        self.zones = zones
        self.rules = rules

    def print_generated_policies(self):
        print(self.generate_policies_h())
        print(self.generate_policies_cpp())

    def print_generated_infos(self):
        print(self.generate_infos_h())
        print(self.generate_infos_cpp())

    def generate_files(self, output_dir):
        self.write_file(output_dir,
            self.ZONE_POLICIES_H_FILE_NAME, self.generate_policies_h())
        self.write_file(output_dir,
            self.ZONE_POLICIES_CPP_FILE_NAME, self.generate_policies_cpp())

        self.write_file(output_dir,
            self.ZONE_INFOS_H_FILE_NAME, self.generate_infos_h())
        self.write_file(output_dir,
            self.ZONE_INFOS_CPP_FILE_NAME, self.generate_infos_cpp())

    def write_file(self, output_dir, filename, content):
        full_filename = os.path.join(output_dir, filename)
        with open(full_filename, 'w', encoding='utf-8') as output_file:
            print(content, end='', file=output_file)
        logging.info("Created %s", full_filename)

    def generate_policies_h(self):
        policy_items = ''
        for name, rules in sorted(self.rules.items()):
            policy_items += self.ZONE_POLICIES_H_POLICY_ITEM.format(
                policyName=name)

        return self.ZONE_POLICIES_H_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            policyItems=policy_items)

    def generate_policies_cpp(self):
        policy_items = ''
        for name, rules in sorted(self.rules.items()):
            policy_items += self.generate_policy_item(name, rules)

        return self.ZONE_POLICIES_CPP_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            policyItems=policy_items
        )

    def generate_policy_item(self, name, rules):
        rule_items = ''
        for rule in rules:
            atHour = rule['atMinute'] // 60
            rule_items += self.ZONE_POLICIES_CPP_RULE_ITEM.format(
                rawLine=rule['rawLine'],
                fromYearFull=rule['fromYear'],
                toYearFull=rule['toYear'],
                inMonth=rule['inMonth'],
                onDayOfWeek=rule['onDayOfWeek'],
                onDayOfMonth=rule['onDayOfMonth'],
                atHour=atHour,
                atHourModifier=rule['atHourModifier'],
                deltaCode=rule['deltaCode'],
                letter=rule['letter'])

        return self.ZONE_POLICIES_CPP_POLICY_ITEM.format(
            policyName=name,
            ruleItems=rule_items)
            
    def generate_infos_h(self):
        info_items = ''
        for name, zones in sorted(self.zones.items()):
            info_items += self.ZONE_INFOS_H_INFO_ITEM.format(
                infoShortName=short_name(name))

        return self.ZONE_INFOS_H_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            infoItems=info_items)

    def generate_infos_cpp(self):
        info_items = ''
        for name, zones in sorted(self.zones.items()):
            info_items += self.generate_entry_item(name, zones)

        return self.ZONE_INFOS_CPP_FILE.format(
            invocation=self.invocation,
            tz_version=self.tz_version,
            infoItems=info_items)

    def generate_entry_item(self, name, zones):
        entry_items = ''
        for zone in zones:
            rules = zone['rules']
            if rules == '-':
                zonePolicy = 'nullptr'
            else:
                zonePolicy = 'kPolicy%s' % rules

            until_year = zone['untilYear']
            if until_year == 9999:
                until_year = 255
            else:
                until_year -= 2000

            entry_items += self.ZONE_INFOS_CPP_ENTRY_ITEM.format(
                rawLine=zone['rawLine'],
                offsetCode=zone['offsetCode'],
                zonePolicy=zonePolicy,
                format=zone['format'],
                untilYear=until_year)

        return self.ZONE_INFOS_CPP_INFO_ITEM.format(
            infoFullName=name,
            infoShortName=short_name(name),
            entryItems=entry_items)


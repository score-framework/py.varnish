# Copyright © 2015 STRG.AT GmbH, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in the
# file named COPYING.LESSER.txt.
#
# The SCORE Framework and all its parts are distributed without any WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
# License.
#
# If you have not received a copy of the GNU Lesser General Public License see
# http://www.gnu.org/licenses/.
#
# The License-Agreement realised between you as Licensee and STRG.AT GmbH as
# Licenser including the issue of its valid conclusion and its pre- and
# post-contractual effects is governed by the laws of Austria. Any disputes
# concerning this License-Agreement including the issue of its valid conclusion
# and its pre- and post-contractual effects are exclusively decided by the
# competent court, in whose district STRG.AT GmbH has its registered seat, at
# the discretion of STRG.AT GmbH also the competent court, in whose district the
# Licensee has his registered seat, an establishment or assets.

import click
from score.cli import config
from score.varnish import ConfiguredVarnishModule
from score.init import parse_time_interval, parse_host_port, parse_list, \
    parse_bool, ConfigurationError, extract_conf


@click.group()
def main():
    pass


@main.command('purge')
@click.argument('paths', nargs=-1, default=None)
@click.option('-h', '--host', 'hosts', multiple=True, default=None,
              help='The varnish host.')
@click.option('-d', '--domain', 'domains', multiple=True, default=None,
              help='The domain to purge.')
@click.option('-t', '--timeout', 'timeout', default=None,
              help='The connect timeout for a purge request.')
@click.option('--hard', 'soft', flag_value=False, default=None,
              help='Whether to purge hard.')
@click.option('--soft', 'soft', flag_value=True, default=None,
              help='Whether to purge soft.')
@click.option('-y', '--yes', 'confirm', flag_value=False, default=True,
              help='Answer "yes" to all confirmations.')
def purge(hosts, domains, paths, soft, timeout, confirm):
    """
    CLI for sending purge requests to varnish hosts.
    """
    confdict = dict(config()[__package__])
    if not hosts:
        try:
            hosts = parse_list(confdict['hosts'])
        except KeyError:
            raise ConfigurationError('Missing configuration for key "hosts".')
    hosts = [parse_host_port(host) for host in hosts]
    if timeout is None:
        timeout = confdict['timeout']
    timeout = parse_time_interval(timeout)
    if soft is None:
        soft = confdict['soft']
    soft = parse_bool(soft)
    header_mapping = extract_conf(confdict, 'header.')
    if confirm:
        lines = (
            ('HOSTS: ', [':'.join(map(str, host)) for host in hosts]),
            ('DOMAINS: ', domains or ['.*']),
            ('PATHS: ', paths or ['.*'])
        )
        for line in lines:
            print(line[0] + ('\n' + ' '*len(line[0])).join(line[1]))
        click.confirm('Purge %s?' % ('soft' if soft else 'hard'), abort=True)
    varnish_conf = ConfiguredVarnishModule(hosts, soft, timeout, header_mapping)
    responses = varnish_conf.purge(domains=list(domains) or None,
                                   paths=list(paths) or None)
    for response in responses:
        print('Purged %s: %s %s %s' % (
            'soft' if response.request.soft else 'hard',
            ':'.join(map(str, response.request.host)),
            response.request.domain or '.*',
            response.request.path or '.*'
        ))

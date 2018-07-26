# Copyright © 2015-2018 STRG.AT GmbH, Vienna, Austria
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
import traceback


@click.group()
def main():
    pass


@main.command('purge')
@click.argument('paths', nargs=-1, default=None)
@click.option('-d', '--domain', 'domains', multiple=True, default=None,
              help='The domain to purge.')
@click.option('-t', '--timeout', 'timeout', default=None,
              help='The connect timeout for a purge request.')
@click.option('--type', 'type_', default=None)
@click.option('-y', '--yes', 'confirm', flag_value=False, default=True,
              help='Answer "yes" to all confirmations.')
@click.pass_context
def purge(click_ctx, domains, paths, type_, timeout, confirm):
    """
    CLI for sending purge requests to varnish servers.
    """
    varnish = click_ctx.obj['conf'].load('varnish')
    if confirm:
        lines = (
            ('SERVERS: ', list('%s:%s' % server for server in varnish.servers)),
            ('DOMAINS: ', domains or ['.*']),
            ('PATHS: ', paths or ['.*'])
        )
        for line in lines:
            print(line[0] + ('\n' + ' '*len(line[0])).join(line[1]))
        prompt = 'Purge?'
        if type_:
            prompt = 'Purge %s?' % (type_,)
        click.confirm(prompt, abort=True)
    requests = varnish.purge(domains=domains, paths=paths, type=type_,
                             raise_on_error=False)
    for request in requests:
        print('%r - ' % (request,), end='')
        if request.response and request.response.status != 200:
            print('ERROR')
            print('  %d - %s' % (request.response.status,
                                 request.response.reason))
        elif request.exception:
            print('ERROR')
            traceback.print_exception(
                type(request.exception),
                request.exception,
                request.exception.__traceback__)
        else:
            print('SUCCESS')

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

import threading
from http.client import HTTPConnection
from score.init import (
    ConfiguredModule, parse_time_interval, parse_list, parse_host_port,
    extract_conf)

defaults = {
    'timeout': '5s',
    'servers': [],
    'header.domain': 'X-Purge-Domain',
    'header.path': 'X-Purge-Path',
    'header.type': 'X-Purge-Type',
}


def init(confdict):
    """
    Initializes this module according to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`servers` :confdefault:`[]`
        A :func:`list <score.init.parse_list>` of Varnish hosts interpreted via
        :func:`score.init.parse_host_port`.

    :confkey:`timeout` :confdefault:`5s`
        The :func:`timeout <score.init.parse_time_interval>` for sending
        requests to a Varnish host passed to

    :confkey:`header.domain` :confdefault:`X-Purge-Domain`
        The header used for communicating the domain to purge.

    :confkey:`header.path` :confdefault:`X-Purge-Path`
        The header used for communicating the URL path to purge.

    :confkey:`header.type` :confdefault:`X-Purge-Type`
        The header that controls the :term:`purge type`.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    servers = [parse_host_port(host) for host in parse_list(conf['servers'])]
    timeout = parse_time_interval(conf['timeout'])
    header_mapping = extract_conf(conf, 'header.')
    return ConfiguredVarnishModule(servers, timeout, header_mapping)


class ConfiguredVarnishModule(ConfiguredModule):
    """
    This module's :class:`configuration object <score.init.ConfiguredModule>`.
    """

    def __init__(self, servers, timeout, header_mapping):
        import score.varnish
        super().__init__(score.varnish)
        self.servers = servers
        self.timeout = timeout
        self.header_mapping = header_mapping

    def purge(self, *, domains=[], domain=None, paths=[], path=None, type=None,
              raise_on_error=True):
        """
        Sends multiple :term:`purge requests <purge request>` to all configured
        Varnish servers with given keyword arguments for domains and paths.
        Each domain and path will result in a separate request to every
        configured Varnish_ host. All requests are sent asynchronously.

        The keyword argument *type* sends the :term:`type <purge type>` of purge
        request to perform.

        This method raises a :class:`PurgeError` containing a list of
        :class:`.PurgeError` causes if one of the requests fails for any reason.

        You can pass a *domain* and/or a *path*, ...

        .. code-block:: python

            # ...
            varnish_conf.purge(domain='montypython.com', path='^/parrot$')

        ... lists of *domains* and/or *paths* ...

        .. code-block:: python

            varnish_conf.purge(domains=['montypython.com', 'python.org'],
                               paths=['^/parrot$', '^/asteroids', '.*game$'])

        ... or nothing at all (purging everything):

        .. code-block:: python

            varnish_conf.purge()

        Note that *domains* and *domain* are mutually exclusive (as are *paths*
        and *path*).

        .. code-block:: python

            varnish_conf.purge(domain='python.org',
                               paths=['^/parrot$', '.*game$'],
                               type='hard')

        or none of them, which ist the most unspecific solution and
        will purge all servers and all paths on each Varnish_ host. Use with
        caution.

        .. code-block:: python

            varnish_conf.purge()
        """
        if domains and domain:
            raise ValueError('Both *domain* and *domains* given')
        if paths and path:
            raise ValueError('Both *path* and *paths* given')
        if not self.servers:
            # we could return even earlier than this, but even if there are no
            # servers configured, the checks of the keyword arguments should be
            # performed nonetheless.  otherwise we would start getting
            # unexpected errors as soon as varnish was enabled.
            return []
        # copy values to avoid tainting the function defaults
        domains = domains[:]
        paths = paths[:]
        if domain:
            domains.append(domain)
        if path:
            paths.append(path)
        requests = []
        for server in self.servers:
            for domain in domains or [None]:
                for path in paths or [None]:
                    request = PurgeRequest(self, server, domain, path, type)
                    request.start()
                    requests.append(request)
        for request in requests:
            request.join()
        if raise_on_error:
            exceptions = list(r.exception for r in requests if r.exception)
            if exceptions:
                raise PurgeError('One or more Exceptions occured.', exceptions)
        return requests


class PurgeRequest(threading.Thread):
    """
    A PurgeRequest handles a HTTP request with the method *PURGE* to a
    Varnish_ server.
    """

    def __init__(self, conf, server, domain, path, type):
        super().__init__()
        self.conf = conf
        self.server = server
        self.domain = domain
        self.path = path
        self.type = type
        self.exception = None
        self.response = None

    def __repr__(self):
        parts = ['server=%r']
        args = [self.__class__.__name__, self.server]
        if self.path is not None:
            parts.append('path=%r')
            args.append(self.path)
        if self.domain is not None:
            parts.append('domain=%r')
            args.append(self.domain)
        if self.type is not None:
            parts.append('type=%r')
            args.append(self.type)
        tpl = '%s(' + ', '.join(parts) + ')'
        return tpl % tuple(args)

    def run(self):
        try:
            self.send()
        except Exception as e:
            self.conf.log.exception(e)
            self.exception = e

    def send(self):
        """
        Sends the request to the provided :attr:`server`. Returns a
        :class:`PurgeResponse` or raises a :class:`PurgeError`.
        """
        self.conf.log.info(self)
        headers = dict()
        if self.domain:
            headers[self.conf.header_mapping['domain']] = self.domain
        if self.path:
            headers[self.conf.header_mapping['path']] = self.path
        if self.type:
            headers[self.conf.header_mapping['type']] = self.type
        connection = HTTPConnection(*self.server, timeout=self.conf.timeout)
        try:
            connection.request('GET', '/', headers=headers)
            response = connection.getresponse()
        finally:
            connection.close()
        self.response = response
        self.conf.log.info(response)
        if response.status is not 200:
            raise PurgeError(response.reason)


class PurgeError(Exception):
    """
    Thrown if a :term:`purge request` failed.
    """

    def __init__(self, msg, causes=None):
        """
        :param msg: The message.
        :param causes: The list of causes.
        """
        self.msg = msg
        self.causes = causes

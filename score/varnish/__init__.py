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

import logging
import multiprocessing
from http.client import HTTPConnection, HTTPException
from score.init import ConfiguredModule, parse_time_interval, parse_list, \
    parse_host_port, parse_bool, extract_conf

log = logging.getLogger(__package__)
defaults = {
    'timeout': '5s',
    'soft': 'true',
    'hosts': [],
    'header.domain': 'X-Purge-Domain',
    'header.path': 'X-Purge-Path',
    'header.soft': 'X-Purge-Soft',
}


def init(confdict):
    """
    Initializes this module according to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`hosts`
        A list of Varnish hosts passed to :func:`parse_host_port
        <score.init.parse_host_port>` and :func:`parse_list
        <score.init.parse_list>`.

    :confkey:`soft` :faint:`[default=true]`
        Whether to purge :term:`soft <soft purge>` or :term:`hard <hard purge>`.

    :confkey:`timeout` :faint:`[default=5s]`
        The timeout for sending requests to a Varnish host passed to
        :func:`parse_time_interval <score.init.parse_time_interval>`.

    :confkey:`header.domain` :faint:`[default=X-Purge-Domain]`
        The name of the header used for purging a domain.

    :confkey:`header.path` :faint:`[default=X-Purge-Path]`
        The name of the header used for purging a path.

    :confkey:`header.soft` :faint:`[default=X-Purge-Soft]`
        The name of the header used for triggering a :term:`soft purge`.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    hosts = [parse_host_port(host) for host in parse_list(conf['hosts'])]
    soft = parse_bool(conf['soft'])
    timeout = parse_time_interval(conf['timeout'])
    header_mapping = extract_conf(conf, 'header.')
    return ConfiguredVarnishModule(hosts, soft, timeout, header_mapping)


class ConfiguredVarnishModule(ConfiguredModule):
    """
    This module's :class:`configuration object <score.init.ConfiguredModule>`.
    """

    def __init__(self, hosts, soft, timeout, header_mapping):
        super().__init__(__package__)
        self.hosts = hosts
        self.soft = soft
        self.timeout = timeout
        self.header_mapping = header_mapping

    def purge(self, **kwargs):
        """
        Sends multiple :term:`purge requests <purge request>` to all configured
        Varnish hosts with given keyword arguments for domains and paths.
        Each domain and path will result in a separate request to every
        configured Varnish_ host. All requests are sent asynchronously.

        The keyword argument *soft* overrides the configured default for each
        :term:`purge request`. It describes whether the request should be a
        :term:`soft purge` or :term:`hard purge`.

        This method raises a :class:`PurgeError` containing a list of
        :class:`.PurgeError` causes if one of the requests fails for any reason.

        You could pass a *domain* and *path* ...

        .. code-block:: python

            # ...
            varnish_conf.purge(domain='montypython.com', path='^/parrot$')

        a list of *domains* and *paths* ...

        .. code-block:: python

            varnish_conf.purge(domains=['montypython.com', 'python.org'],
                               paths=['^/parrot$', '^/asteroids', '.*game$'])

        just the *soft* flag ...

        .. code-block:: python

            varnish_conf.purge(soft=False)

        a mixture of everything ...

        .. code-block:: python

            varnish_conf.purge(domains=['montypython.com'],
                               domain='python.org',
                               paths=['^/parrot$', '.*game$'],
                               path='^/asteroids',
                               soft=False)

        or none of them, which ist the most unspecific solution and
        will purge all hosts and all paths on each Varnish_ host. Use with
        caution.

        .. code-block:: python

            varnish_conf.purge()
        """
        domains = []
        paths = []
        soft = self.soft
        if 'domains' in kwargs:
            domains = kwargs['domains']
        if 'domain' in kwargs:
            if not isinstance(kwargs['domain'], str):
                raise TypeError('Keyword argument "domain" must be of type '
                                '%s, %s given.' %
                                (type(''), type(kwargs['domain'])))
            if kwargs['domain'] not in domains:
                domains.append(kwargs['domain'])
        if 'paths' in kwargs:
            paths = kwargs['paths']
        if 'path' in kwargs:
            if not isinstance(kwargs['path'], str):
                raise TypeError('Keyword argument "path" must be of type '
                                '%s, %s given.' %
                                (type(''), type(kwargs['path'])))
            if kwargs['path'] not in paths:
                paths.append(kwargs['path'])
        if 'soft' in kwargs and kwargs['soft'] is not None:
            soft = kwargs['soft']
        responses = []
        exceptions = []
        pool = multiprocessing.Pool()
        for host in self.hosts:
            for domain in domains or [None]:
                for path in paths or [None]:
                    purge_request = PurgeRequest(
                        host, soft, self.timeout, self.header_mapping,
                        domain=domain, path=path
                    )
                    pool.apply_async(
                        purge_request.send,
                        callback=lambda re: responses.append(re),
                        error_callback=lambda ex: exceptions.append(ex)
                    )

        pool.close()
        pool.join()
        if exceptions:
            raise PurgeError('One or more Exceptions occured.', exceptions)
        return responses


class PurgeRequest:
    """
    A PurgeRequest handles a HTTP request with the method *PURGE* to a
    Varnish_ host.
    """

    def __init__(self, host, soft, timeout, header_mapping, *,
                 domain=None, path=None):
        """
        :param host: The Varnish_ host to purge. A tuple
                     representing ``(host, port)``.
        :param soft: Whether the request should be a :term:`soft purge`
                     or :term:`hard purge`.
        :param timeout: The timeout in seconds.
        :param header_mapping: A dict for header mappings.
        :param domain: The regular expression for a domain to purge.
        :param path: The regular expression for a path to purge.
        """
        self.host = host
        self.soft = soft
        self.timeout = timeout
        self.header_mapping = header_mapping
        self.domain = domain
        self.path = path

    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self.__dict__)

    def send(self):
        """
        Sends the request to the :attr:`host`. Returns a
        :class:`PurgeResponse` or raises a :class:`PurgeError`.
        """
        log.info(self)
        headers = {
            self.header_mapping['domain']: self.domain or '.*',
            self.header_mapping['path']: self.path or '.*',
        }
        if self.soft:
            headers[self.header_mapping['soft']] = 'true'
        connection = HTTPConnection(*self.host, timeout=self.timeout)
        try:
            connection.request('PURGE', '/', headers=headers)
            response = connection.getresponse()
        except HTTPException as e:
            raise PurgeError('Connection to Varnish host failed: %s' % e)
        finally:
            connection.close()
        if response.status is not 200:
            raise PurgeError(response.reason)
        purge_respone = PurgeResponse(self, response)
        log.info(purge_respone)
        return purge_respone


class PurgeResponse:
    """
    A PurgeResponse generated by :meth:`.PurgeRequest.send`.
    """

    def __init__(self, request, response):
        """
        :param request: The :class:`PurgeRequest` this :class:`.PurgeResponse`
                        object was generated with.
        :param response: The :class:`http.client.HTTPResponse` object the
                         corresponding :class:`.PurgeRequest` has generated.
        """
        self.request = request
        self.response = response

    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self.__dict__)


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

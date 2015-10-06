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

"""
This package :ref:`integrates <framework_integration>` the module with
pyramid_.

.. _pyramid: http://docs.pylonsproject.org/projects/pyramid/en/latest/
"""

from score.init import (
    ConfigurationError, parse_time_interval, parse_dotted_path)
from pyramid.interfaces import IPredicateList
from pyramid.events import NewResponse


def init(confdict, configurator):
    """
    Apart from calling the :func:`base initializer <score.varnish.init>`, this
    function will also register a :term:`subscriber <pyramid:subscriber>`, which
    will set appropriate varnish headers for caching. The configuration of these
    headers need to be provided in a separate configuration value:

    :confkey:`conf`
        A :func:`dotted path <score.init.parse_dotted_path>` to a
        :class:`CachingConfiguration` instance.
    """
    import score.varnish
    conf = score.varnish.init(confdict)
    if 'conf' not in confdict:
        return conf
    caching = parse_dotted_path(confdict['conf'])
    if not isinstance(caching, CachingConfiguration):
        raise ConfigurationError(
            __package__, '"conf" must be an instance of CachingConfiguration')
    def set_header(event):
        duration = caching.lookup(event.request)
        if duration:
            header = ('Cache-Control', 'v-max-age=%d' % duration)
            event.response.headerlist.append(header)
    configurator.action(None, lambda: caching._finalize(configurator), order=10)
    configurator.add_subscriber_predicate('varnish_cacheable', Cacheable)
    configurator.add_subscriber(set_header, NewResponse, varnish_cacheable=True)
    return conf


class Cacheable:
    """
    A :ref:`subscriber predicate <pyramid:subscriber_predicates>` for events
    with request value that will test if the request could be cachde by varnish.
    It currently only ensures that the request method is "GET".
    """

    def __init__(self, value, config):
        self.inverted = not value

    def text(self):
        return 'varnish_cacheable = %s' % self.inverted

    phash = text

    def __call__(self, event):
        if not hasattr(event, 'request'):
            return
        cacheable = event.request.method == 'GET'
        if self.inverted:
            return not cacheable
        return cacheable


class CachingConfiguration:
    """
    A configuration of caching durations for various :term:`routes
    <pyramid:route>`. Instances of this class can be populated with consecutive
    calls to :meth:`.add` and must then be passed to the :func:`pyramid
    initializer <.init>`:

    .. code-block:: python

        from score.varnish.pyramid import CachingConfiguration, init

        caching = CachingConfiguration()
        caching.add('my_route', '10m')

        init({'conf': caching})
    """

    def __init__(self):
        self.configurations = []
        self.finalized = False

    def add(self, route, duration, **predicates):
        """
        Adds a caching duration for the route with given *name*. The *duration*
        must either be an integer (caching duration in seconds), or a string,
        which will be passed to :func:`score.init.parse_time_interval`.

        It is possible to add arbitrary :term:`view predicates <pyramid:view
        predicate>` to these rules:

        .. code-block:: python

            caching.add('my_route', '1h', xhr=False)
            caching.add('my_route', '10m', xhr=True)
        """
        if self.finalized:
            raise Exception('Cannot add further configurations after the '
                            'object was setup by the initializer')
        self.configurations.append({
            'name': route,
            'duration': parse_time_interval(duration),
            'predicates': predicates,
        })

    def _finalize(self, config):
        """
        This function will be called by the pyramid initializer and converts all
        predicate names to their respective callbacks.
        """
        predlist = config.registry.queryUtility(IPredicateList, name='view')
        for conf in self.configurations:
            if not conf['predicates']:
                continue
            _, predicates, _ = predlist.make(config, **conf['predicates'])
            conf['predicates'] = predicates
        self.finalized = True

    def lookup(self, request):
        """
        Returns number of seconds a *request* should be cached. Might be `None`
        if no caching was configured for given value.

        .. note::
            There is no need to call this function manually. If you have passed
            this object to a :func:`pyramid initializer <.init>`, score and
            pyramid will take care of everything.
        """
        if not self.finalized:
            raise Exception('Cannot perform lookup: '
                            'Configuration was not finalized yet')
        route = request.matched_route
        if not route:
            return
        for conf in self.configurations:
            if conf['name'] != route.name:
                continue
            context = getattr(request, 'context', None)
            if all(pred(context, request) for pred in conf['predicates']):
                return conf['duration']
        return None

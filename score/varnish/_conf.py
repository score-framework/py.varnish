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

from score.init import parse_time_interval
import functools


def add_route_caching(duration):
    """
    Adds caching to a :term:`route` by adding the `Cache-Control` header
    `s-maxage` to the response. The header is only added to responses of ``GET``
    requests. The *duration* may be anything acceptable by
    :func:`score.init.parse_time_interval`.

    See `Section 14.9.3 of RFC 2616`__ for the documentation of the ``s-maxage``
    value.

    __ https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9.3
    """
    duration = parse_time_interval(duration)

    def add_caching(route):
        callback = route.callback

        @functools.wraps(callback)
        def wrapper(ctx, *args, **kwargs):
            result = callback(ctx, *args, **kwargs)
            if ctx.http.request.method == 'GET':
                header = ('Cache-Control', 's-maxage=%d' % duration)
                ctx.http.response.headerlist.append(header)
            return result

        route.callback = wrapper
        return route

    return add_caching

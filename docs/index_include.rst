.. module:: score.varnish
.. role:: confkey
.. role:: confdefault

*************
score.varnish
*************

A module for defining caching durations for your :term:`routes <route>` as well
as sending `cache invalidation requests`_ to a running Varnish_ server. The
Varnish server must be configured to be able to interpret the commands sent by
this module correctly.

.. _cache invalidation requests: https://book.varnish-software.com/4.0/chapters/Cache_Invalidation.html
.. _Varnish: https://www.varnish-cache.org/

Quickstart
==========

You will first need to configure your varnish servers in your score
configuration file:

.. code-block:: ini

    [score.init]
    modules =
        score.varnish

    [varnish]
    servers = 127.0.0.1:80

You can now configure caching for your :mod:`score.http` :term:`routes
<route>`:

.. code-block:: python

    from score.varnish import cache

    @cache('5m')
    @route('home', '/')
    def home(ctx):
        return 'Hello World'

If you also configure your Varnish server to be able to accept HTTP requests
with the custom HTTP verb ``PURGE``, you can use this module to send such cache
invalidation requests. You can find a `short introduction to cache invalidation
in Varnish`__ in the varnish documentation:

.. code-block:: python

    # remove dead parrot
    score.varnish.purge(path='^/parrot$')


__ https://www.varnish-cache.org/docs/4.0/users-guide/purging.html

Configuration
=============

.. autofunction:: init

Details
=======

PURGE Headers
-------------

We have already mentioned, that the HTTP request will supply the custom verb
PURGE. The following is the list of default headers sent with the request to
control the operation:

``X-Purge-Domain``
    A regular expression for desired domains. It is meant to purge something
    like ``.*\.montypython.com`` which would affect ``montypython.com`` as well
    as ``www.montypython.com`` and all other subdomains.

``X-Purge-Path``
    A regular expression describing the paths to purge. The expression
    ``^/python$`` for example should solely purge one path.

``X-Purge-Type``
    This header controls the :term:`type <purge type>` of the purge to perform,
    if your server supports more than one.


Command-Line Interface
----------------------

Upon installation, this module registers a :mod:`score.cli` command that can be
used to invalidate all your Varnish_ hosts at once:

.. code-block:: console

    $ score varnish purge --domain .*montypython.com
      --domain python.org --hard --timeout 3s ^/parrot ^/pythonland
    HOSTS: localhost:6081
    DOMAINS: .*montypython.com
             python.org
    PATHS: ^/parrot
           ^/pythonland
    Purge hard? [y/N]: yes
    Purged hard: localhost:6081 python.org ^/parrot
    Purged hard: localhost:6081 .*montypython.com ^/pythonland
    Purged hard: localhost:6081 python.org ^/pythonland
    Purged hard: localhost:6081 .*montypython.com ^/parrot

.. code-block:: console

    $ score varnish purge --host localhost:6081 ^/pythons
    HOSTS: localhost:6081
    DOMAINS: .*
    PATHS: ^/pythons
    Purge soft? [y/N]: y
    Purged soft: localhost:6081 .* ^/pythons

.. code-block:: console

    $ score varnish purge
    HOSTS: localhost:6081
    DOMAINS: .*
    PATHS: .*
    Purge soft? [y/N]: yes
    Purged soft: localhost:6081 .* .*

If you want to bypass the confirmation dialog, just append the *yes* option:

.. code-block:: console

    $ score varnish purge --yes
    Purged soft: localhost:6081 .* .*

.. _varnish_configuration:

API
===

.. autofunction:: init

.. autoclass:: ConfiguredVarnishModule

    .. automethod:: purge

.. autofunction:: cache

.. autoclass:: PurgeError

.. _Varnish: https://www.varnish-cache.org/

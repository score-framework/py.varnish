.. module:: score.varnish
.. role:: faint
.. role:: confkey

*************
score.varnish
*************

Introduction
============

This module handles :term:`purge requests <purge request>` to a Varnish_ host.
To get an idea of what Varnish_ is and what it is meant to be just dive into
the `Varnish documentation`_. We are using HTTP headers to tell a Varnish_
configuration what to purge as described in the documentation of purging_.
The :term:`VCL` has to deal with configurable headers we use in our module:

.. _Varnish: https://www.varnish-cache.org/

Headers
-------

domain :faint:`[X-Purge-Domain]`
    A regular expression for desired domains. It is meant to purge something
    like ``.*montypython.com`` which would affect ``montypython.com`` as well
    as ``www.montypython.com`` (and of course all other subdomains).

path :faint:`[X-Purge-Path]`
    A regular expression for desired paths. The expression ``^/pythons$`` for
    example should solely purge one path, namely ``/pythons``.

soft :faint:`[X-Purge-Soft]`
    This header is sent within a :term:`soft purge`.

.. _Varnish documentation: https://www.varnish-cache.org/docs/4.0/
.. _purging: https://www.varnish-cache.org/docs/4.0/users-guide/purging.html

Command-Line Interface
======================

Upon installation, this module registers a :mod:`score.cli` command that can be
used to send :term:`purge requests <purge request>` to multiple Varnish_ hosts.
Use the configuration keys in our :ref:`module configuration
<varnish_configuration>` to set up your command-line environment as described
in the :ref:`score.cli configuration management <cli_configuration_management>`.
The configuration keys with default values will be automatically configured in
your environment.

The configuration key for *hosts* is mandatory if you do not want to pass the
*host* option in every command-line call. Some other optional options like
*timeout* or *soft* will fall back to the configuration values of your
command-line environment. It is recommended to check your environment before
you start purging. A working configuration looks like this:

.. code-block:: console

    $ score config list score.varnish
    timeout = 5s
    soft = true
    hosts = localhost:6081
    header.domain = X-Purge-Domain
    header.path = X-Purge-Path
    header.soft = X-Purge-Soft

Here is a full example of all command-line arguments and options. You could
pass multiple *hosts*, multiple *domains* and multiple *paths*.

.. code-block:: console

    $ score varnish purge --host localhost:6081 --domain .*montypython.com
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

This example uses the configured hosts in your environment. We assume that we
configured *hosts* to *localhost:6081*.

.. code-block:: console

    $ score varnish purge
    HOSTS: localhost:6081
    DOMAINS: .*
    PATHS: .*
    Purge soft? [y/N]: yes
    Purged soft: localhost:6081 .* .*

If you want to bypass the confirmation dialog, just append *yes* as option.

.. code-block:: console

    $ score varnish purge --yes
    Purged soft: localhost:6081 .* .*

.. _Varnish: https://www.varnish-cache.org/

.. _varnish_configuration:

Configuration
=============

.. autofunction:: init

.. autoclass:: ConfiguredVarnishModule

    .. automethod:: purge

.. autoclass:: .PurgeError


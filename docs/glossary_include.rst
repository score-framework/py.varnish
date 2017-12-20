.. _varnish_glossary:

.. glossary::

    purge request
        An HTTP request to a Varnish_ server with the HTTP verb ``PURGE`` and
        the intent to invalidate its cache for certain resources. This approach
        allows you to cache objects for a long time, if you invalidate the
        cache each time they are modified.

    purge type
        There numerous `cache invalidation strategies in the Varnish server`__.
        If you have configured your Varnish_ server to do so, you may specify
        the type of purge to perform in your :term:`purge requests <purge
        request>`.

        __ https://book.varnish-software.com/4.0/chapters/Cache_Invalidation.html

.. _Varnish: https://www.varnish-cache.org/
.. _soft purge: https://www.varnish-cache.org/vmod/soft-purge

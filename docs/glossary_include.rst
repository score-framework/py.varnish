.. _Varnish: https://www.varnish-cache.org/
.. _soft purge: https://www.varnish-cache.org/vmod/soft-purge

.. _varnish_glossary:

.. glossary::

    purge request
        A special HTTP request with the method *PURGE* to a Varnish_ host.

    soft purge
        A special :term:`purge request` telling the Varnish_ backend to use the
        `soft purge`_ feature.

    hard purge
        A :term:`purge request` not using the feature of a :term:`soft purge`.

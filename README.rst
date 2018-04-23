.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

===================
collective.es.index
===================

ElasticSearch Indexer for Plone content

Features
--------

- Indexes full content in ElasticSearch on a field base
- uses serializers of ``plone.restapi`` to get the JSON for indexing
- configuration of ElasticSearch via ``zope.conf`` (buildout)
- flexible drop-in replacement proxy-index for the catalog (optional)
- default profile installs SearchableText drop-in (optional)


Installation
------------

This addon needs ElasticSearch 6.2 with `ingest-attachment plugin <https://www.elastic.co/guide/en/elasticsearch/plugins/6.2/ingest-attachment.html>`_ installed.

Install collective.es.index by adding it to your buildout::

    [buildout]

    ...

    eggs =
        collective.es.index

also there, configure the connection to ElasticSearch::

    [instance]

    ...

    zope-conf-additional =
         %import collective.es.index
         <elasticsearch>
         query 127.0.0.1:9200
         ingest 127.0.0.1:9200
         </elasticsearch>

and then running ``bin/buildout``.

To install the default drop-in proxy-index for ``SearchableText``,
go to the Site-Setup Add-Ons section and install ``ElasticSearch SearchableText Proxy Index``.

New content will be indexed in ElasticSearch.

To index existing content, a full ``Clear and Rebuild`` is needed (via ZMI/``portal_catalog``/Tab ``Advanced``).


Source Code
-----------

The sources are in a GIT DVCS with its main branches at `github <http://github.com/collective/collective.es.index>`_.
There you can report issue too.

We'd be happy to see many forks and pull-requests to make this addon even better.

Maintainers are `Jens Klein <mailto:jk@kleinundpartner.at>`_, `Peter Holzer <mailto:peter.holzer@agitator.com>`_ and the BlueDynamics Alliance developer team.
We appreciate any contribution and if a release is needed to be done on pypi, please just contact one of us.
We also offer commercial support if any training, coaching, integration or adaptions are needed.


Contributions
-------------

Initial implementation was made possible by `Evangelisch-reformierte Landeskirche des Kantons Zürich <http://zhref.ch/>`_.

Idea and testing: Peter Holzer

Concept & code by Jens W. Klein

Authors:

- no others so far


License
-------

The project is licensed under the GPLv2.

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

Using in Plone 4
----------------

This product can be used in Plone 4. but it requires the `collective.indexing`
product. Just add this product to your Plone 4 buildout::

    [buildout]

    ...

    eggs =
        collective.indexing

ES Python dependencies
----------------------

Current version of this package requires `elasticsearch_dsl`.
It is necessary to add the 'elasticsearch-dsl' egg to the buildout eggs.
Alternatively, it can be added to the eggs in the celery part.
Run the buildout again to get that dependency on existing installations.

ES configuration on zope.conf
-----------------------------

The elasticsearch directive supports the following keys:

`max_blobsize`
  Max length of files to index, in bytes.
  If a file is larger than this size, it will not be indexed, and this will be logged.
  Default is zero, which means index everything.

`request_timeout`
  The default connection timeout is 10 seconds.
  Using this key it can be set to any number of seconds.

`use_celery`
  If `true`, indexing will be done in async celery tasks.
  This requires that celery is correctly configured.

`indexed_chars`
  Maximum number of characters to extract from attachments.
  Default is `100000`.
  Use `-1` for infinite.

`search_fields`
  The search fields and their weights for searching, separated by spaces.

Example::

  zope-conf-additional =
      %import collective.es.index
      <elasticsearch>
      query 127.0.0.1:92000
      ingest 127.0.0.1:92000
      request_timeout 20
      max_blobsize 10000000 # 10 MB
      indexed_chars 200000
      use_celery true
      search_fields title^1.2 description^1.1 subjects^2 extracted_text
      </elasticsearch>

It is necessary to add this configuration to the buildout and rerun it
whenever a change is made to these parameters.

Celery configuration
--------------------

NOTE: The configuration here uses `collective.celery`, so it has changed.

The collective.celery package requires adding the celery and collective.celery eggs to the mian buildout section eggs.
Example::

  eggs =
      celery
      Plone
      elasticsearch
      elasticsearch-dsl
      collective.es.index
      collective.celery

We still use the celery-broker part, for clarity.
The celery part is still required, but is simpler::

  [celery-broker]
  host = 127.0.0.1
  port = 6379

  [celery]
  recipe = zc.recipe.egg
  environment-vars = ${buildout:environment-vars}
  eggs =
      ${buildout:eggs}
      flower
  scripts = pcelery flower

The celery part depends on having some variables added to the main
environment-vars section::

  environment-vars =
      CELERY_BROKER_URL redis://${celery-broker:host}:${celery-broker:port}
      CELERY_RESULT_BACKEND redis://${celery-broker:host}:${celery-broker:port}
      CELERY_TASKS collective.es.index.tasks

Removing b64 attribute
----------------------

To get the b64 attribute removal working on an existing elasticsearch install,
it's necessary to clear the old ingest pipeline,
so that collective.es.index can install the new one.
To do this, you can use a Python prompt, like this::

  >>> from elasticsearch import Elasticsearch
  >>> es = Elasticsearch()
  >>> es.ingest.delete_pipeline('attachment_ingest_plone_plone')

Highlight support
-----------------

For every search result, a list of highlights from extracted text is
saved as a dictionary in the current request annotations. The
dictionary is keyed by object UID.

To get the annotations from Python code::

  from collective.es.index.esproxyindex import HIGHLIGHT_KEY
  from zope.annotation.interfaces import IAnnotations
  annotations = IAnnotations(REQUEST)
  highlights = annotations[HIGHLIGHT_KEY]
  obj_highlights = highlights[OBJ_UID]
  highlight_text = '<br/>'.join(obj_highlights)

Highlights are just lists of HTML text fragments with the query term
enclosed in `<em>` tags.

Faceted search
--------------

In addition to the elastic search index,
this package includes support for faceted search,
as implemented in the elasticsearch_dsl library.
There is a `@@faceted-search` view, which will allow you to filter search results using facets.

Note that collective.es.index used a mapping that was incompatible with faceted search,
wo it's necessary to completely remove the previous index from elastic search and reindex it again.

The quickest way to remove the index is from the command line::

  >>> from elasticsearch import Elasticsearch
  >>> es = Elasticsearch()
  >>> es.indices.delete('plone_plone')

Once this is done, the full catalog must be reindexed from the ZMI.

By default, review_state, subjects, and modified fields are used as facets.
The elastic search zope configuration supports changing them and adding custom facets.
For regular keyword fields, just use the name of the field.
For date fields, add an interval (month, week, day, hour).
For integer fields, an integer interval is allowed::

  zope-conf-additional =
      %import collective.es.index
      <elasticsearch>
      query 127.0.0.1:92000
      facets department created,month subjects
      </elasticsearch>

The facets key expects one or more facets separated by spaces.
In this example there is a custom facet (department),
a date facet using monthly intervals,
and a regular plone facet.
Do not leave any spaces between the field and the interval for date and integer facets,
or they will not be interpreted correctly.

Although elasticsearch_dsl supports month, week, day, and hour intervals,
in practice, month is the best for plone, since the others result in a large number of options.

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

Concept & initial code by Jens W. Klein

Authors:

- Enfold Systems


License
-------

The project is licensed under the GPLv2.

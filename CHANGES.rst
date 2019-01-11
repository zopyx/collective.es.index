Changelog
=========

1.0a2 (unreleased)
------------------

- Move to elasticsearch_dsl package for query generation

- Add celery support (requires latest collective.celery) tested with celery>=4.2.0

- Add new directives: max_blobsize, request_timeout, use_celery, indexed_chars

- No longer keeps the b64 encoded blob in ES index

- Add highlight support on search results

- basic plone 4 compatibility

- refactor code to avoid sending obj data in redis payload

- add stopgap solution for missing rid problem


1.0a1 (git tag)
---------------

- Initial release.
  [jensens]

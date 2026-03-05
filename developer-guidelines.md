## Developer Guidelines

This document provides guidelines for developers to effectively and safely make changes to our codebases.

Our overall system is tested by integration tests located in the `api-tests` repository. When implementing any changes, this repo should be updated first to reflect the new expected behavior.

After the integration tests are updated (and failing), the other repos can be updated to implement the desired behavior.

While updating each repo, the local tests in each repo should also be updated. Use the same branch name across all repos that are updated; that way, they can all be tested together reliably in the integration tests.

Ensure that the local tests are passing in each repo before moving on.

To run the integration tests, you need to additionally clone the `service-infra` repo in /repos/ as well. The `api-tests` references this repo. Do that before running the integration tests.

In addition, check the docker-compose file in service-infra to make sure that you have all of the necessary repos cloned for reference in the full integration tests. You do not need to run `docker compose up` in the infra repo because the integration tests will do that during setup.

Once all changes are complete, run the integration tests and then iterate to fix any errors or oversights.

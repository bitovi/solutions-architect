## Developer Guidelines

This document provides guidelines for developers to effectively and safely make changes to our codebases.

Our overall system is tested by integration tests located in the `api-tests` repository. When implementing any changes, this repo should be updated first to reflect the new expected behavior. This repo can be referenced to understand how the entire system is connected together (see the docker compose file).

The integration tests should be updated first (and failing). Other repos can be updated afterward to implement the desired behavior.

While updating each repo, the local tests in each repo should also be updated. Use the same branch name across all repos that are updated; that way, they can all be tested together reliably in the integration tests.

Ensure that the local tests are passing in each repo before moving on.

The integration tests have a Github Action workflow to check out all branches of the same name (using default/main as the fallback for any repo that doesn't have that branch) and run the tests against those branches together. So, once you update all repos, the PR in the api-tests repo can verify the implementation contained in the new branches.

Iterate and refine as necessary until all tests pass.

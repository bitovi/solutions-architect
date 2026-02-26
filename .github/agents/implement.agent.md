---
name: Implement Feature
description: Implement a feature across one or more repositories based on the operations files created by the Plan Feature agent.
---
Your task is to implement a feature or change based on the specifications provided. The /operations/ folder contains the implementation/change plans that you need to follow. Each plan file corresponds to a specific repository and contains the details of the changes required in that repository.

developer-guidelines.md in the root needs to be considered to understand the overall workflow and principles for making changes across the system. Follow that guide to understand how work is done.

Clone all necessary repositories into the /repos/ folder and create a new branch for your work. The branch name should be the same across all repos you update to keep the work organized and testable together.

For this exercise, you do not need to make any commits or open PRs. Just update the code and/or documentation in the repos according to the plans and leave it for the user to review.

For each major step in the development workflow, use subagents to isolate context and then iterate as necessary until the final tests pass.

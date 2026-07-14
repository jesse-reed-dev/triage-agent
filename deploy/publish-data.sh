#!/usr/bin/env bash
# Publishes data/data.json to the local `data` branch — the branch GitHub
# Pages' dashboard reads. Runs as the second ExecStart of triage-agent.service,
# so it only executes when the pipeline delivered successfully.
#
# Uses git plumbing (hash-object → mktree → commit-tree → update-ref) instead
# of checkout/add/commit so it NEVER touches the working directory: whatever
# branch is checked out, whatever uncommitted work is in flight, this only
# creates objects and moves the `data` branch pointer. The first run creates
# the branch as an orphan automatically (a commit with no parent).
#
# Pushes via the `data-publish` remote — an SSH host alias backed by a
# write-scoped deploy key (see README), so the live dashboard updates
# without any human action. No remote configured = commit-only, push
# manually. A failed push is a warning, not a failure: the commit is safe
# locally and the next run's push carries it.

set -euo pipefail
cd "$(dirname "$0")/.."

push_data_branch() {
    if ! git remote get-url data-publish >/dev/null 2>&1; then
        echo "publish-data: no data-publish remote — push the data branch manually to update the dashboard."
    elif git push -q data-publish data:data; then
        echo "publish-data: pushed — the live dashboard is current."
    else
        echo "publish-data: WARNING — push failed; will retry on the next run. Dashboard stays at its last pushed state."
    fi
}

if [ ! -f data/data.json ]; then
    echo "publish-data: no data/data.json yet — nothing to publish."
    exit 0
fi

# Write the file into git's object store; get its content hash.
blob=$(git hash-object -w data/data.json)

# Build a tree (a directory snapshot) holding just that one file.
tree=$(printf '100644 blob %s\tdata.json' "$blob" | git mktree)

# Find the current tip of the data branch, if the branch exists yet.
parent=$(git rev-parse -q --verify refs/heads/data || true)

# No new issues means an identical tree — skip the empty commit, but still
# push in case an earlier commit never made it out.
if [ -n "$parent" ] && [ "$(git rev-parse "$parent^{tree}")" = "$tree" ]; then
    echo "publish-data: data.json unchanged — no new commit."
    push_data_branch
    exit 0
fi

# Commit the tree on top of the previous publish (or as the orphan root),
# then move the branch pointer to it.
commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "Publish triage data $(date +%F)")
git update-ref refs/heads/data "$commit"
echo "publish-data: data branch is now $commit"
push_data_branch

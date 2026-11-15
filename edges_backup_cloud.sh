#!/bin/bash
# 15 Nov (lane 2, coordinator 15:00 item 6): daily encrypted backup of the cloud record's state (work/output) to the branch
# "edges-backup" of this repo. Encrypted to edges_backup_pub.pem: only the private key, which sits on Ansh's Mac (secrets/, never in
# git, never typed by anyone), can open it, so the public branch shows nothing readable. Once a day; keeps the last 30.
# Restore (on the Mac): scratch/edge/edges_restore.sh <file.enc>
set -e
D=$(date -u +%Y-%m-%d); W=work/output
git fetch -q origin edges-backup 2>/dev/null && git ls-tree --name-only origin/edges-backup | grep -q "state-$D.enc" && { echo "edges backup: already done today"; exit 0; }
T=$(mktemp -d); tar czf $T/state.tgz -C work output/markets/live output/markets/odds/oa 2>/dev/null || tar czf $T/state.tgz -C work output
openssl rand -out $T/k 32
openssl enc -aes-256-cbc -pbkdf2 -salt -in $T/state.tgz -out $T/state-$D.enc -pass file:$T/k
openssl pkeyutl -encrypt -pubin -inkey edges_backup_pub.pem -in $T/k -out $T/state-$D.key
rm -f $T/k $T/state.tgz
B=$(mktemp -d); git worktree add -q --detach $B 2>/dev/null
cd $B
if git rev-parse -q --verify origin/edges-backup >/dev/null; then git checkout -q -B edges-backup origin/edges-backup; else git checkout -q --orphan edges-backup; git rm -rq . 2>/dev/null || true; fi
cp $T/state-$D.enc $T/state-$D.key .
ls state-*.enc 2>/dev/null | sort | head -n -30 | while read f; do git rm -q "$f" "${f%.enc}.key" 2>/dev/null || true; done
git add state-$D.enc state-$D.key
git -c user.name=edges-bot -c user.email=edges-bot@users.noreply.github.com commit -q -m "edges state backup $D (encrypted)"
for i in 1 2 3; do git push -q origin edges-backup && break || { git fetch -q origin edges-backup; git rebase -q origin/edges-backup; sleep 5; }; done
echo "edges backup: state-$D.enc pushed to edges-backup ($(du -k state-$D.enc | cut -f1) KB)"

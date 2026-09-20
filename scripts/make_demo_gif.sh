#!/usr/bin/env bash
set -euo pipefail

output="${1:-docs/assets/vectorledger-demo.gif}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

make_frame() {
  local number="$1"
  local command="$2"
  local body="$3"
  convert -size 1200x675 xc:'#07111f' \
    -fill '#12233b' -draw 'roundrectangle 35,30 1165,645 24,24' \
    -fill '#263c59' -draw 'rectangle 35,30 1165,78' \
    -fill '#ff6b6b' -draw 'circle 65,54 72,54' \
    -fill '#ffd166' -draw 'circle 91,54 98,54' \
    -fill '#5de2a5' -draw 'circle 117,54 124,54' \
    -font DejaVu-Sans-Mono -pointsize 24 -fill '#8ba6c8' \
    -annotate +155+62 'VectorLedger demo' \
    -pointsize 27 -fill '#57d7ff' -annotate +70+135 "$ $command" \
    -pointsize 25 -fill '#e6edf7' -interline-spacing 14 -annotate +70+200 "$body" \
    "$work_dir/frame-$number.png"
}

make_frame 1 'docker compose up -d' $'Starting postgres ... done\nStarting qdrant  ... done\nStarting redis    ... done\nStarting vectorledger ... done'
make_frame 2 'docker compose --profile demo run --rm demo' $'Seeded salary-policy.pdf\n\nPostgreSQL: 1 chunk\nQdrant:    1 unregistered vector\nRedis:     1 cached answer'
make_frame 3 'vectorledger delete salary-policy --tenant acme' $'Tombstone version 2 accepted\n\nDiscovering records by tenant_id + document_id ...\nDeleting derived copies ...\nRunning independent verification scan ...'
make_frame 4 'vectorledger verify salary-policy --tenant acme' $'POSTGRES   CLEAN   deleted=1   remaining=0\nQDRANT     CLEAN   deleted=1   remaining=0\nREDIS      CLEAN   deleted=1   remaining=0'
make_frame 5 'receipt status' $'VERIFIED DELETED\n\nAll configured stores are clean.\nSigned receipt persisted for audit.'

convert -delay 90 "$work_dir/frame-1.png" \
  -delay 110 "$work_dir/frame-2.png" \
  -delay 130 "$work_dir/frame-3.png" \
  -delay 150 "$work_dir/frame-4.png" \
  -delay 220 "$work_dir/frame-5.png" \
  -loop 0 -layers Optimize "$output"

echo "Wrote $output"

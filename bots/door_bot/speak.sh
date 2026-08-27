#!/bin/bash

text="$1"

curl -s -G -X POST "http://127.0.0.1:50021/audio_query?speaker=3" \
  --data-urlencode "text=$text" \
| curl -s -H "Content-Type: application/json" -X POST -d @- \
  "http://127.0.0.1:50021/synthesis?speaker=3" \
  > /tmp/voice.wav

aplay /tmp/voice.wav

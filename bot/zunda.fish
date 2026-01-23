function zunda
    set -l text ""

    if test (count $argv) -gt 0
        set text (string join " " $argv)
    else
        read -z text
    end

    test -z "$text"; and return

    curl -s -G -X POST "127.0.0.1:50021/audio_query?speaker=3" \
        --data-urlencode "text=$text" \
    | curl -s -H "Content-Type: application/json" -X POST -d @- \
        "127.0.0.1:50021/synthesis?speaker=3" \
    | paplay
end


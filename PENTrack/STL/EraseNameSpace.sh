for h in */ *; do
    cd "$h"
    for d in *\ *; do mv "$d" "${d// /}"; done
    cd ..
done

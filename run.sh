trap 'kill $(jobs -p)' EXIT
python3 rpcserver.py localhost 5000 &
wait
#!/bin/sh
# 1 request every 2 s to the legacy orders app, so its eBPF traces keep flowing.
while :; do curl -s -o /dev/null http://127.0.0.1:8200/; sleep 2; done

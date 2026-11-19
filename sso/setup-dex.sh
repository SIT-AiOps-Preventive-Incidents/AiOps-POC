#!/bin/sh
# Make sso/dex.yaml from dex.example.yaml: a random password per demo account, a random client secret, bcrypt
# hashes (made with htpasswd in a throwaway container). Prints the accounts once and keeps them in
# sso/demo-accounts.txt (mode 600). Neither file is committed.
set -eu
cd "$(dirname "$0")"
PUBLIC_URL=${PUBLIC_URL:-http://cp26pt1.sit.kmutt.ac.th:8080}
ISSUER=${SSO_ISSUER:-http://cp26pt1.sit.kmutt.ac.th:5556/dex}
rnd() { head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 16; }
bcrypt() { docker run --rm httpd:2.4-alpine htpasswd -bnBC 10 "" "$1" | tr -d ':\n'; }
SECRET=$(rnd)
cp dex.example.yaml dex.yaml.tmp
sed -i "s|__ISSUER__|$ISSUER|; s|__PUBLIC_URL__|$PUBLIC_URL|; s|__CLIENT_SECRET__|$SECRET|" dex.yaml.tmp
umask 077
: > demo-accounts.txt
for who in admin manager developer viewer; do
  pw=$(rnd)
  h=$(bcrypt "$pw")
  sed -i "s|__HASH_${who}__|$h|" dex.yaml.tmp
  echo "$who@radarops.demo  $pw" >> demo-accounts.txt
done
mv dex.yaml.tmp dex.yaml
chmod 644 dex.yaml   # the dex container reads it as its own user
echo "issuer         $ISSUER"
echo "client id      radarops"
echo "client secret  $SECRET"
echo "demo accounts (also in sso/demo-accounts.txt):"
cat demo-accounts.txt

#!/usr/bin/env bash
set -u
for URL in \
  'https://artifactory.ext.net.nokia.com/artifactory/api/npm/npmjs/' \
  'https://artifactory-espoo1.int.net.nokia.com/artifactory/api/npm/npmjs/' \
  'https://artifactory-espoo1.int.net.nokia.com/artifactory/api/npm/npm-public/' \
  'https://artifactory-espoo1.int.net.nokia.com/artifactory/api/npm/npm-virtual/'
do
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 8 "${URL}vite")
  echo "$URL -> $code"
done

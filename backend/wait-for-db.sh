#!/bin/sh

set -e

host="$1"
shift

until mysqladmin ping -h "$host" --silent; do
  echo "Waiting for MariaDB at $host..."
  sleep 2
done

exec "$@" 
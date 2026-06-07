#!/bin/sh
set -e

# Replace environment variables in built files
if [ -n "$VITE_API_BASE_URL" ]; then
    find /usr/share/nginx/html -name "*.js" -exec sed -i "s|__VITE_API_BASE_URL__|$VITE_API_BASE_URL|g" {} \;
fi

if [ -n "$VITE_APP_VERSION" ]; then
    find /usr/share/nginx/html -name "*.js" -exec sed -i "s|__VITE_APP_VERSION__|$VITE_APP_VERSION|g" {} \;
fi

# Execute the main command
exec "$@"